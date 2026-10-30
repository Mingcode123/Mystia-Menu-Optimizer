"""Single-plan and cookware selection from the final nCookware prototype.

The priority is capped coverage, ingredient count, then supply margin. Supply
is evaluated per guest; this is not a joint inventory model for an entire day.

Publication cleanup changes: identical-tag additions are allocated with base
consumption included, and all neutral fillers remain eligible. Historical
multi-plan solvers and their inactive advanced-ingredient filters are omitted.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from itertools import combinations, combinations_with_replacement

from .models import Candidate, Dataset, Dish, Guest, Ingredient, Settings
from .rules import (
    COVER_RULES,
    COVERAGE_CAP,
    MAX_INGREDIENTS,
    allowed_addons,
    cookware_key,
    effective_guest,
    final_tags,
    price_tag,
    score_tags,
)

# Retain the original nCookware treatment of guests with no feasible plan.
NO_PLAN_INGREDIENT_PENALTY = 10**9
NO_PLAN_MARGIN_PENALTY = 10**18


def _allocate_equivalent(
    base_counts: Counter,
    group_demands: tuple[tuple[tuple[str, ...], int], ...],
    ingredients: dict[str, Ingredient],
    orders_per_day: int,
) -> tuple[tuple[str, ...], float]:
    """Maximize minimum remaining supply for fixed identical-tag group counts.

    Each ingredient belongs to one tag group. At a proposed margin, the base
    recipe must fit and each group must have enough aggregate extra capacity.
    The optimum occurs at q_i - K*(base_i + extra_i), with extra_i <= 5.
    Binary search checks those discrete values. At the common optimal margin,
    lexicographically smallest additions are recovered by a capacity fill.
    This includes base consumption, unlike the old maximum-raw-TDQ replacement.
    """
    base_margins = [ingredients[name].daily_quantity - orders_per_day * count for name, count in base_counts.items()]
    if not group_demands:
        return (), min(base_margins)

    thresholds = set(base_margins)
    for members, demand in group_demands:
        for name in members:
            for extra in range(1, demand + 1):
                thresholds.add(ingredients[name].daily_quantity - orders_per_day * (base_counts[name] + extra))
    thresholds = sorted(thresholds)

    def capacity(name: str, demand: int, margin: float) -> int:
        # A five-slot recipe lets us avoid floor/epsilon errors entirely.
        for extra in range(demand, 0, -1):
            remaining = ingredients[name].daily_quantity - orders_per_day * (base_counts[name] + extra)
            if remaining >= margin:
                return extra
        return 0

    def feasible(margin: float) -> bool:
        if any(value < margin for value in base_margins):
            return False
        return all(sum(capacity(name, demand, margin) for name in members) >= demand for members, demand in group_demands)

    lo, hi = 0, len(thresholds) - 1
    best_margin = thresholds[0]
    while lo <= hi:
        mid = (lo + hi) // 2
        if feasible(thresholds[mid]):
            best_margin = thresholds[mid]
            lo = mid + 1
        else:
            hi = mid - 1

    additions = []
    for members, demand in group_demands:
        left = demand
        for name in members:
            take = min(left, capacity(name, demand, best_margin))
            additions.extend([name] * take)
            left -= take
            if not left:
                break
        if left:
            raise AssertionError("Equivalent ingredient allocation failed at a feasible margin")
    additions = tuple(sorted(additions))
    counts = base_counts + Counter(additions)
    actual_margin = min(ingredients[name].daily_quantity - orders_per_day * count for name, count in counts.items())
    return additions, actual_margin


def best_dish_candidate(
    dish: Dish,
    guest: Guest,
    ingredients: dict[str, Ingredient],
    settings: Settings,
    incumbent: Candidate | None = None,
) -> Candidate | None:
    """Enumerate tag-group multisets, including repeated additions and fillers.

    Search reductions reject unremovable disliked tags and impossible score
    upper bounds. Once coverage reaches its cap, a longer ingredient list
    cannot improve the lexicographic objective. There is no top-N candidate cap.
    """
    if not dish.owned or not guest.preferred_tags:
        return None
    base_count = len(dish.required_ingredients)
    if not 1 <= base_count <= MAX_INGREDIENTS:
        raise ValueError(f"Recipe {dish.name!r} must have 1–{MAX_INGREDIENTS} base ingredients")
    if any(name not in ingredients for name in dish.required_ingredients):
        raise ValueError(f"Recipe {dish.name!r} contains an unknown base ingredient")
    max_total = MAX_INGREDIENTS
    if incumbent is not None and incumbent.coverage == COVERAGE_CAP:
        max_total = min(max_total, incumbent.total_ingredients)
    if base_count > max_total:
        return None

    coverable = {weak for _, weak in COVER_RULES}
    irrevocable_dislikes = guest.disliked_tags - coverable
    raw_dish_tags = set(dish.tags) | {dish.cookware}
    if price_tag(dish.sell_price):
        raw_dish_tags.add(price_tag(dish.sell_price))
    if raw_dish_tags.intersection(irrevocable_dislikes):
        return None

    by_signature = defaultdict(list)
    for name in allowed_addons(dish, ingredients):
        tags = ingredients[name].tags
        if not tags.intersection(irrevocable_dislikes):
            by_signature[tuple(sorted(tags))].append(name)
    groups = tuple((frozenset(tags), tuple(sorted(members))) for tags, members in sorted(by_signature.items()))

    # Optimistic upper bound ignores all tag removals and all dislikes.
    possible_tags = set(raw_dish_tags)
    for tags, _ in groups:
        possible_tags.update(tags)
    if groups and base_count < MAX_INGREDIENTS:
        possible_tags.add("大份")
    if possible_tags.intersection(settings.trend_like):
        possible_tags.add("流行·喜爱")
    if possible_tags.intersection(settings.trend_hate):
        possible_tags.add("流行·厌恶")
    if len(possible_tags.intersection(guest.preferred_tags)) < settings.min_score:
        return None

    base_counts = Counter(dish.required_ingredients)
    best = None
    for extra_count in range(max_total - base_count + 1):
        for indexes in combinations_with_replacement(range(len(groups)), extra_count):
            addon_tags = set()
            multiplicities = Counter(indexes)
            for index in multiplicities:
                addon_tags.update(groups[index][0])
            tags = final_tags(dish, addon_tags, extra_count, settings)
            if tags.intersection(guest.disliked_tags):
                continue
            score = score_tags(tags, guest)
            if score < settings.min_score:
                continue
            covered = tuple(tag for tag in guest.preferred_tags if tag in tags)
            demands = tuple((groups[index][1], count) for index, count in sorted(multiplicities.items()))
            additions, margin = _allocate_equivalent(base_counts, demands, ingredients, settings.orders_per_day)
            counts = base_counts + Counter(additions)
            candidate = Candidate(
                dish=dish,
                added_ingredients=additions,
                final_tags=tags,
                covered_tags=covered,
                score=score,
                total_ingredients=base_count + extra_count,
                supply_margin=margin,
                ingredient_counts=tuple(sorted(counts.items())),
            )
            if best is None or candidate.preference_key < best.preference_key:
                best = candidate
        # Complete the entire layer before stopping, so supply and ties count.
        if best is not None and best.coverage == COVERAGE_CAP:
            break
    return best


def best_by_cookware(
    guest: Guest,
    dishes: tuple[Dish, ...],
    ingredients: dict[str, Ingredient],
    settings: Settings,
) -> dict[str, Candidate]:
    best = {}
    excluded = {cookware_key(name) for name in settings.exclude_cookware}
    # Smaller base recipes provide useful ingredient-count bounds first.
    for dish in sorted(dishes, key=lambda item: (len(item.required_ingredients), item.name)):
        key = cookware_key(dish.cookware)
        if not dish.owned or key in excluded:
            continue
        candidate = best_dish_candidate(dish, guest, ingredients, settings, best.get(key))
        if candidate is not None and (key not in best or candidate.preference_key < best[key].preference_key):
            best[key] = candidate
    return best


def _plan_dict(candidate: Candidate, ingredients: dict[str, Ingredient], settings: Settings) -> dict:
    return {
        "dish": candidate.dish.name,
        "cookware": candidate.dish.cookware,
        "sell_price": candidate.dish.sell_price,
        "base_ingredients": list(candidate.dish.required_ingredients),
        "added_ingredients": list(candidate.added_ingredients),
        "final_tags": sorted(candidate.final_tags),
        "covered_tags": list(candidate.covered_tags),
        "score": candidate.score,
        "coverage_capped": candidate.coverage,
        "total_ingredients": candidate.total_ingredients,
        "supply_margin": candidate.supply_margin,
        "ingredient_counts": dict(candidate.ingredient_counts),
        "remaining_supply": {
            name: ingredients[name].daily_quantity - settings.orders_per_day * count
            for name, count in candidate.ingredient_counts
        },
    }


def plan_dataset(dataset: Dataset, settings: Settings, guest_names: tuple[str, ...] | None = None) -> dict:
    wanted = set(guest_names or ())
    unknown = wanted - {guest.name for guest in dataset.guests}
    if unknown:
        raise ValueError(f"Unknown guest name(s): {', '.join(sorted(unknown))}")
    guests = tuple(effective_guest(guest, settings) for guest in dataset.guests if not wanted or guest.name in wanted)
    if not guests:
        raise ValueError("No guests selected")
    cookware_names = {}
    for dish in sorted(dataset.dishes, key=lambda item: (item.cookware, item.name)):
        if dish.owned and dish.cookware:
            cookware_names.setdefault(cookware_key(dish.cookware), dish.cookware)
    excluded = {cookware_key(name) for name in settings.exclude_cookware}
    unknown_excluded = excluded - cookware_names.keys()
    if unknown_excluded:
        raise ValueError(f"Unknown or unavailable cookware exclusion(s): {', '.join(sorted(unknown_excluded))}")
    cookware_names = {key: value for key, value in cookware_names.items() if key not in excluded}
    cookware_keys = tuple(sorted(cookware_names))
    n = len(cookware_keys) if settings.cookware_count is None else settings.cookware_count
    if n > len(cookware_keys):
        raise ValueError(f"cookware_count={n} exceeds the {len(cookware_keys)} available cookware types")

    per_guest = {guest.name: best_by_cookware(guest, dataset.dishes, dataset.ingredients, settings) for guest in guests}
    best_combo = None
    best_key = None
    best_chosen = {}
    best_metrics = None
    for combo in combinations(cookware_keys, n):
        chosen = {}
        for guest in guests:
            candidates = [per_guest[guest.name][key] for key in combo if key in per_guest[guest.name]]
            if candidates:
                chosen[guest.name] = min(candidates, key=lambda item: item.preference_key)
        missing = len(guests) - len(chosen)
        coverage = sum(item.coverage for item in chosen.values())
        total = sum(item.total_ingredients for item in chosen.values())
        margin = sum(item.supply_margin for item in chosen.values())
        penalized_total = total + missing * NO_PLAN_INGREDIENT_PENALTY
        penalized_margin = margin - missing * NO_PLAN_MARGIN_PENALTY
        key = (-coverage, penalized_total, -penalized_margin, combo)
        if best_key is None or key < best_key:
            best_key, best_combo, best_chosen = key, combo, chosen
            best_metrics = {
                "guest_count": len(guests),
                "planned_count": len(chosen),
                "unplanned_count": missing,
                "coverage_sum": coverage,
                "total_ingredients_sum": total,
                "supply_margin_sum": margin,
                "comparison_total_with_missing_penalty": penalized_total,
                "comparison_margin_with_missing_penalty": penalized_margin,
            }
    results = []
    for guest in guests:
        candidate = best_chosen.get(guest.name)
        results.append({
            "guest": guest.name,
            "budget_display_only": guest.budget,
            "preferred_tags": list(guest.preferred_tags),
            "disliked_tags": sorted(guest.disliked_tags),
            "status": "planned" if candidate else "no_feasible_plan",
            "plan": _plan_dict(candidate, dataset.ingredients, settings) if candidate else None,
        })
    return {
        "format": "mystia-planner-result/v1",
        "source_metadata": dataset.metadata,
        "settings": {
            "min_score": settings.min_score,
            "orders_per_day": settings.orders_per_day,
            "coverage_cap": COVERAGE_CAP,
            "trend_like": sorted(settings.trend_like),
            "trend_hate": sorted(settings.trend_hate),
            "cookware_count": n,
            "exclude_cookware": sorted(settings.exclude_cookware),
        },
        "selected_cookware": [cookware_names[key] for key in (best_combo or ())],
        "summary": best_metrics,
        "model_scope": {
            "budget_is_constraint": False,
            "negative_supply_margin_allowed": True,
            "inventory_shared_across_guests": False,
            "ingredient_cost_unit": "count, not purchase price",
            "missing_plan_ingredient_penalty": NO_PLAN_INGREDIENT_PENALTY,
            "missing_plan_margin_penalty": NO_PLAN_MARGIN_PENALTY,
        },
        "guests": results,
    }
