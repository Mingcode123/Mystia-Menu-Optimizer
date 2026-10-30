"""Rules retained from the final historical nCookware prototype.

Base recipe ingredients consume supply but do not add their tags to a dish.
Forbidden entries restrict additions, and repeated additions are allowed.
"""

from __future__ import annotations

from dataclasses import replace
from typing import Iterable

from .models import Dish, Guest, Ingredient, Settings

COVER_RULES = (("肉", "素"), ("饱腹", "下酒"), ("重油", "清淡"), ("大份", "小巧"))
MAX_INGREDIENTS = 5
COVERAGE_CAP = 3
# This non-food entry was explicitly excluded in the historical prototype.
EXCLUDED_ADDONS = frozenset({"铃仙"})


def cookware_key(value: str) -> str:
    return "".join(value.split()).casefold()


def price_tag(sell_price: float) -> str | None:
    if 0 < sell_price < 20:
        return "实惠"
    if sell_price > 60:
        return "昂贵"
    return None


def effective_guest(guest: Guest, settings: Settings) -> Guest:
    """No trend anchor means that trend is inactive, as in the legacy CLI."""
    inactive = set()
    if not settings.trend_like:
        inactive.add("流行·喜爱")
    if not settings.trend_hate:
        inactive.add("流行·厌恶")
    return replace(
        guest,
        preferred_tags=tuple(t for t in guest.preferred_tags if t not in inactive),
        disliked_tags=guest.disliked_tags - inactive,
    )


def allowed_addons(dish: Dish, ingredients: dict[str, Ingredient]) -> tuple[str, ...]:
    forbidden_names = set(dish.forbidden_entries) & ingredients.keys()
    forbidden_tags = set(dish.forbidden_entries) - ingredients.keys()
    return tuple(sorted(
        name for name, ingredient in ingredients.items()
        if name not in EXCLUDED_ADDONS
        and name not in forbidden_names
        and not ingredient.tags.intersection(forbidden_tags)
    ))


def final_tags(
    dish: Dish,
    addon_tags: Iterable[str],
    addon_count: int,
    settings: Settings,
) -> frozenset[str]:
    tags = set(dish.tags)
    if dish.cookware:
        tags.add(dish.cookware)
    price = price_tag(dish.sell_price)
    if price:
        tags.add(price)
    tags.update(addon_tags)
    if addon_count > 0 and len(dish.required_ingredients) + addon_count == MAX_INGREDIENTS:
        tags.add("大份")
    for stronger, weaker in COVER_RULES:
        if stronger in tags:
            tags.discard(weaker)
    # Trend triggers are evaluated after all covering rules.
    if tags.intersection(settings.trend_like):
        tags.add("流行·喜爱")
    if tags.intersection(settings.trend_hate):
        tags.add("流行·厌恶")
    return frozenset(tags)


def score_tags(tags: frozenset[str], guest: Guest) -> int:
    return len(tags.intersection(guest.preferred_tags)) - len(tags.intersection(guest.disliked_tags))
