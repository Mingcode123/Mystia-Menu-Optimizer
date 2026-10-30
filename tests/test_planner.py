"""Rule examples and differential checks against a concrete-ingredient oracle.

The oracle deliberately does not use the planner's rule helpers, tag grouping,
capacity solver, or ingredient-count pruning. It exhaustively tries concrete
ingredient multisets on small inputs.
"""

from collections import Counter
from itertools import combinations, combinations_with_replacement
import random
import unittest

from mystia_planner.models import Dataset, Dish, Guest, Ingredient, Settings
from mystia_planner.planner import best_by_cookware, best_dish_candidate, plan_dataset
from mystia_planner.rules import effective_guest, final_tags, price_tag


def ingredient(name, tags=(), quantity=20):
    return Ingredient(name, frozenset(tags), quantity)


def dish(name="dish", tags=("a", "b"), required=("base",), cookware="pot", price=30, forbidden=(), owned=True):
    return Dish(name, frozenset(tags), cookware, price, tuple(required), tuple(forbidden), owned)


def exhaustive_dish(recipe, guest, ingredients, settings):
    if not recipe.owned or not guest.preferred_tags:
        return None
    allowed = []
    for name, item in sorted(ingredients.items()):
        if name == "铃仙":
            continue
        if any(entry == name if entry in ingredients else entry in item.tags for entry in recipe.forbidden_entries):
            continue
        allowed.append(name)
    best = None
    for length in range(6 - len(recipe.required_ingredients)):
        for extra in combinations_with_replacement(allowed, length):
            tags = set(recipe.tags)
            tags.add(recipe.cookware)
            if 0 < recipe.sell_price < 20:
                tags.add("实惠")
            if recipe.sell_price > 60:
                tags.add("昂贵")
            for name in extra:
                tags.update(ingredients[name].tags)
            if extra and len(recipe.required_ingredients) + len(extra) == 5:
                tags.add("大份")
            for high, low in (("肉", "素"), ("饱腹", "下酒"), ("重油", "清淡"), ("大份", "小巧")):
                if high in tags:
                    tags.discard(low)
            if tags & settings.trend_like:
                tags.add("流行·喜爱")
            if tags & settings.trend_hate:
                tags.add("流行·厌恶")
            if tags & guest.disliked_tags:
                continue
            covered = set(guest.preferred_tags) & tags
            score = len(covered) - len(tags & guest.disliked_tags)
            if score < settings.min_score:
                continue
            counts = Counter(recipe.required_ingredients + extra)
            margin = min(ingredients[name].daily_quantity - settings.orders_per_day * count for name, count in counts.items())
            key = (-min(len(covered), 3), len(recipe.required_ingredients) + len(extra), -margin, -recipe.sell_price, recipe.name, extra)
            if best is None or key < best[0]:
                best = (key, extra, frozenset(tags), margin)
    return best


class RuleExamples(unittest.TestCase):
    def test_repeated_additions_are_needed_to_reach_large_serving(self):
        ingredients = {"base": ingredient("base", quantity=6), "filler": ingredient("filler", quantity=20)}
        guest = Guest("guest", ("a", "b", "大份"))
        candidate = best_dish_candidate(dish(), guest, ingredients, Settings())
        self.assertEqual(candidate.added_ingredients, ("filler",) * 4)
        self.assertEqual(candidate.total_ingredients, 5)
        self.assertEqual(candidate.score, 3)

    def test_base_ingredient_tags_are_not_implicitly_added(self):
        ingredients = {"base": ingredient("base", ("secret",))}
        guest = Guest("guest", ("secret",))
        candidate = best_dish_candidate(dish(tags=()), guest, ingredients, Settings(min_score=1))
        self.assertEqual(candidate.added_ingredients, ("base",))
        self.assertEqual(candidate.total_ingredients, 2)
        forbidden = dish(tags=(), forbidden=("base",))
        self.assertIsNone(best_dish_candidate(forbidden, guest, ingredients, Settings(min_score=1)))

    def test_covering_precedes_trend_detection(self):
        recipe = dish(tags=("素", "下酒", "清淡", "小巧"))
        settings = Settings(trend_like=frozenset({"素"}), trend_hate=frozenset({"肉"}))
        tags = final_tags(recipe, ("肉", "饱腹", "重油"), 4, settings)
        self.assertTrue({"肉", "饱腹", "重油", "大份", "流行·厌恶"} <= tags)
        self.assertTrue({"素", "下酒", "清淡", "小巧", "流行·喜爱"}.isdisjoint(tags))

    def test_five_base_ingredients_alone_do_not_create_large_serving(self):
        recipe = dish(required=("base",) * 5)
        self.assertNotIn("大份", final_tags(recipe, (), 0, Settings()))

    def test_forbidden_name_and_forbidden_tag_apply_only_to_additions(self):
        ingredients = {"base": ingredient("base"), "A": ingredient("A", ("c", "animal")), "B": ingredient("B", ("c",))}
        guest = Guest("guest", ("a", "b", "c"))
        named = best_dish_candidate(dish(forbidden=("A",)), guest, ingredients, Settings())
        tagged = best_dish_candidate(dish(forbidden=("animal",)), guest, ingredients, Settings())
        self.assertEqual(named.added_ingredients, ("B",))
        self.assertEqual(tagged.added_ingredients, ("B",))
        base_forbidden = best_dish_candidate(dish(tags=("a", "b", "c"), forbidden=("base",)), guest, ingredients, Settings())
        self.assertEqual(base_forbidden.added_ingredients, ())

    def test_price_thresholds(self):
        self.assertEqual([price_tag(p) for p in (0, 19, 20, 60, 61)], [None, "实惠", None, None, "昂贵"])

    def test_threshold_and_dislikes_are_hard_constraints(self):
        ingredients = {"base": ingredient("base")}
        self.assertIsNone(best_dish_candidate(dish(), Guest("g", ("a", "b", "c")), ingredients, Settings()))
        self.assertIsNone(best_dish_candidate(dish(tags=("a", "b", "c", "bad")), Guest("g", ("a", "b", "c"), frozenset({"bad"})), ingredients, Settings()))

    def test_coverage_cap_prefers_fewer_ingredients_over_fourth_tag(self):
        ingredients = {"base": ingredient("base", quantity=100)}
        guest = Guest("g", ("a", "b", "c", "d"))
        recipes = (dish("three", ("a", "b", "c")), dish("four", ("a", "b", "c", "d"), ("base", "base"), price=50))
        result = best_by_cookware(guest, recipes, ingredients, Settings())
        self.assertEqual(result["pot"].dish.name, "three")

    def test_equivalence_allocation_includes_base_consumption(self):
        ingredients = {"A": ingredient("A", ("c",), 10), "B": ingredient("B", ("c",), 9)}
        candidate = best_dish_candidate(dish(required=("A",)), Guest("g", ("a", "b", "c")), ingredients, Settings())
        self.assertEqual(candidate.added_ingredients, ("B",))
        self.assertEqual(candidate.supply_margin, 4)

    def test_neutral_fillers_are_not_limited_to_first_three(self):
        ingredients = {"base": ingredient("base", quantity=50)}
        for name in ("A", "B", "C"):
            ingredients[name] = ingredient(name, (f"neutral-{name}",), 0)
        ingredients["Z"] = ingredient("Z", ("neutral-Z",), 50)
        candidate = best_dish_candidate(dish(), Guest("g", ("a", "b", "大份")), ingredients, Settings())
        self.assertNotIn("A", candidate.added_ingredients)
        self.assertNotIn("B", candidate.added_ingredients)
        self.assertNotIn("C", candidate.added_ingredients)
        self.assertIn("Z", candidate.added_ingredients)

    def test_inactive_trends_are_removed_from_guest_preferences(self):
        guest = Guest("g", ("a", "流行·喜爱"), frozenset({"流行·厌恶"}))
        actual = effective_guest(guest, Settings())
        self.assertEqual(actual.preferred_tags, ("a",))
        self.assertEqual(actual.disliked_tags, frozenset())

    def test_deterministic_price_then_name_then_addition_ties(self):
        ingredients = {"base": ingredient("base", quantity=30), "A": ingredient("A", ("c",), 20), "B": ingredient("B", ("c",), 20)}
        recipes = (dish("z", price=40), dish("b", price=50), dish("a", price=50))
        result = best_by_cookware(Guest("g", ("a", "b", "c")), recipes, ingredients, Settings())
        self.assertEqual(result["pot"].dish.name, "a")
        self.assertEqual(result["pot"].added_ingredients, ("A",))


class CookwareExamples(unittest.TestCase):
    def setUp(self):
        self.ingredients = {"base": ingredient("base", quantity=50)}
        self.guests = (Guest("one", ("a", "b", "c")), Guest("two", ("x", "y", "z")))
        self.recipes = (
            dish("pot-one", ("a", "b", "c"), cookware="pot"),
            dish("pan-one", ("a", "b", "c"), cookware="pan"),
            dish("pan-two", ("x", "y", "z"), cookware="pan"),
        )
        self.data = Dataset(self.ingredients, self.recipes, self.guests)

    def test_global_cookware_count_and_exclusion(self):
        report = plan_dataset(self.data, Settings(cookware_count=1))
        self.assertEqual(report["selected_cookware"], ["pan"])
        self.assertEqual(report["summary"]["planned_count"], 2)
        restricted = plan_dataset(self.data, Settings(cookware_count=1, exclude_cookware=frozenset({"pan"})))
        self.assertEqual(restricted["selected_cookware"], ["pot"])
        self.assertEqual(restricted["guests"][1]["status"], "no_feasible_plan")
        self.assertIsNone(restricted["guests"][1]["plan"])
        self.assertEqual(restricted["summary"]["total_ingredients_sum"], 1)
        self.assertEqual(restricted["summary"]["comparison_total_with_missing_penalty"], 1_000_000_001)

    def test_no_plan_does_not_disappear(self):
        report = plan_dataset(self.data, Settings(min_score=6))
        self.assertEqual(report["summary"]["unplanned_count"], 2)
        self.assertEqual(len(report["guests"]), 2)
        self.assertTrue(all(row["plan"] is None for row in report["guests"]))

    def test_negative_margin_is_reported_and_is_not_a_stock_constraint(self):
        data = Dataset({"base": ingredient("base", quantity=0)}, self.recipes, self.guests)
        report = plan_dataset(data, Settings(cookware_count=1))
        self.assertEqual(report["summary"]["planned_count"], 2)
        self.assertEqual(report["guests"][0]["plan"]["supply_margin"], -5)

    def test_invalid_settings_names_and_cookware_fail_explicitly(self):
        for kwargs in ({"min_score": 0}, {"orders_per_day": 0}, {"cookware_count": 0}):
            with self.assertRaises(ValueError):
                Settings(**kwargs)
        with self.assertRaises(ValueError):
            plan_dataset(self.data, Settings(cookware_count=3))
        with self.assertRaises(ValueError):
            plan_dataset(self.data, Settings(), ("missing",))
        with self.assertRaises(ValueError):
            plan_dataset(self.data, Settings(exclude_cookware=frozenset({"typo"})))

    def test_guest_filter_and_dish_order_are_deterministic(self):
        one = plan_dataset(self.data, Settings(cookware_count=1), ("two",))
        self.assertEqual([row["guest"] for row in one["guests"]], ["two"])
        reverse = Dataset(self.ingredients, tuple(reversed(self.recipes)), self.guests)
        self.assertEqual(plan_dataset(self.data, Settings()), plan_dataset(reverse, Settings()))


class ExhaustiveDifferentialTests(unittest.TestCase):
    def test_equivalent_group_multiple_copies_and_repeated_base(self):
        ingredients = {
            "A": ingredient("A", ("neutral",), 20),
            "B": ingredient("B", ("neutral",), 15),
        }
        recipe = dish(required=("A", "A"))
        guest = Guest("g", ("a", "b", "大份"))
        settings = Settings()
        candidate = best_dish_candidate(recipe, guest, ingredients, settings)
        expected = exhaustive_dish(recipe, guest, ingredients, settings)
        self.assertEqual(candidate.preference_key, expected[0])
        self.assertEqual(candidate.added_ingredients, ("A", "B", "B"))
        self.assertEqual(candidate.supply_margin, 5)

    def test_group_allocation_cross_group_bottleneck_and_lexical_tie(self):
        # x and y groups need separate additions. A fixed low-supply base
        # ingredient sets the bottleneck, so local group maxima alone are not
        # enough to recover the global lexicographically smallest tied solution.
        ingredients = {
            "base": ingredient("base", (), 7),
            "A": ingredient("A", ("x",), 8),
            "B": ingredient("B", ("x",), 30),
            "C": ingredient("C", ("y",), 8),
            "D": ingredient("D", ("y",), 30),
        }
        recipe = dish(tags=("a",))
        guest = Guest("g", ("a", "x", "y"))
        settings = Settings()
        candidate = best_dish_candidate(recipe, guest, ingredients, settings)
        expected = exhaustive_dish(recipe, guest, ingredients, settings)
        self.assertEqual(candidate.preference_key, expected[0])
        self.assertEqual(candidate.added_ingredients, ("A", "C"))
        self.assertEqual(candidate.supply_margin, 2)

    def test_random_small_instances_match_concrete_multiset_enumeration(self):
        rng = random.Random(271828)
        tag_universe = ("a", "b", "c", "肉", "素", "大份", "小巧")
        feasible_cases = 0
        for case in range(90):
            ingredients = {}
            for index in range(rng.randint(3, 6)):
                name = f"i{index}"
                tags = tuple(rng.sample(tag_universe, rng.randint(0, 2)))
                if index == 1:
                    tags = tuple(ingredients["i0"].tags)  # force an equivalent group
                ingredients[name] = ingredient(name, tags, rng.choice([0, 5, 9, 10, 10.5, 20]))
            all_names = tuple(ingredients)
            recipe = dish(
                tags=rng.sample(tag_universe, rng.randint(0, 3)),
                required=tuple(rng.choice(all_names) for _ in range(rng.randint(1, 3))),
                price=rng.choice([0, 19, 20, 60, 61]),
                forbidden=(rng.choice(all_names + tag_universe),) if rng.random() < 0.35 else (),
            )
            preferred = tuple(rng.sample(tag_universe + ("实惠", "昂贵", "流行·喜爱", "流行·厌恶"), rng.randint(2, 5)))
            guest = Guest("g", preferred, frozenset(rng.sample(tag_universe, rng.randint(0, 2))))
            settings = Settings(
                min_score=rng.randint(1, 3),
                orders_per_day=rng.randint(1, 5),
                trend_like=frozenset({"素"}) if rng.random() < 0.5 else frozenset(),
                trend_hate=frozenset({"肉"}) if rng.random() < 0.5 else frozenset(),
            )
            guest = effective_guest(guest, settings)
            actual = best_dish_candidate(recipe, guest, ingredients, settings)
            expected = exhaustive_dish(recipe, guest, ingredients, settings)
            with self.subTest(case=case):
                if expected is None:
                    self.assertIsNone(actual)
                else:
                    feasible_cases += 1
                    self.assertIsNotNone(actual)
                    self.assertEqual(actual.preference_key, expected[0])
                    self.assertEqual(actual.final_tags, expected[2])
        self.assertGreaterEqual(feasible_cases, 10, "The random oracle must exercise feasible solutions as well as rejection")

    def test_cookware_selection_matches_uncompressed_exhaustive_oracle(self):
        ingredients = {
            "A": ingredient("A", ("c",), 10),
            "B": ingredient("B", ("c",), 9),
            "X": ingredient("X", ("x",), 20),
            "Y": ingredient("Y", ("y",), 15),
        }
        recipes = (
            dish("r1", ("a", "b"), ("A",), "pot"),
            dish("r2", ("a", "x"), ("X",), "pan"),
            dish("r3", ("b", "y"), ("B",), "grill"),
        )
        guests = (Guest("one", ("a", "b", "c")), Guest("two", ("a", "x", "y")))
        data = Dataset(ingredients, recipes, guests)
        settings = Settings(cookware_count=2)
        best = None
        for combo in combinations(sorted({r.cookware for r in recipes}), 2):
            selected = []
            for guest in guests:
                options = [exhaustive_dish(recipe, guest, ingredients, settings) for recipe in recipes if recipe.cookware in combo]
                options = [option for option in options if option is not None]
                if options:
                    selected.append(min(options, key=lambda option: option[0]))
            missing = len(guests) - len(selected)
            key = (
                sum(option[0][0] for option in selected),
                sum(option[0][1] for option in selected) + missing * 10**9,
                sum(option[0][2] for option in selected) + missing * 10**18,
                combo,
            )
            if best is None or key < best:
                best = key
        report = plan_dataset(data, settings)
        self.assertEqual(tuple(report["selected_cookware"]), best[3])


if __name__ == "__main__":
    unittest.main()
