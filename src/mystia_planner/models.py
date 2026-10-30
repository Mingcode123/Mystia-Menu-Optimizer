"""Domain objects shared by the parser, rules, and planner."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Ingredient:
    name: str
    tags: frozenset[str]
    daily_quantity: float


@dataclass(frozen=True)
class Dish:
    name: str
    tags: frozenset[str]
    cookware: str
    sell_price: float
    required_ingredients: tuple[str, ...]
    forbidden_entries: tuple[str, ...] = ()
    owned: bool = True


@dataclass(frozen=True)
class Guest:
    name: str
    preferred_tags: tuple[str, ...]
    disliked_tags: frozenset[str] = frozenset()
    budget: str = ""


@dataclass(frozen=True)
class Dataset:
    ingredients: dict[str, Ingredient]
    dishes: tuple[Dish, ...]
    guests: tuple[Guest, ...]
    metadata: dict = field(default_factory=dict)


@dataclass(frozen=True)
class Settings:
    min_score: int = 3
    orders_per_day: int = 5
    trend_like: frozenset[str] = frozenset()
    trend_hate: frozenset[str] = frozenset()
    cookware_count: int | None = None
    exclude_cookware: frozenset[str] = frozenset()

    def __post_init__(self) -> None:
        if isinstance(self.min_score, bool) or not isinstance(self.min_score, int) or self.min_score < 1:
            raise ValueError("min_score must be a positive integer")
        if isinstance(self.orders_per_day, bool) or not isinstance(self.orders_per_day, int) or self.orders_per_day < 1:
            raise ValueError("orders_per_day must be a positive integer")
        if self.cookware_count is not None and (
            isinstance(self.cookware_count, bool)
            or not isinstance(self.cookware_count, int)
            or self.cookware_count < 1
        ):
            raise ValueError("cookware_count must be a positive integer")


@dataclass(frozen=True)
class Candidate:
    dish: Dish
    added_ingredients: tuple[str, ...]
    final_tags: frozenset[str]
    covered_tags: tuple[str, ...]
    score: int
    total_ingredients: int
    supply_margin: float
    ingredient_counts: tuple[tuple[str, int], ...]

    @property
    def coverage(self) -> int:
        return min(len(self.covered_tags), 3)

    @property
    def preference_key(self) -> tuple:
        """Smaller is better; final fields make equal objectives deterministic."""
        return (
            -self.coverage,
            self.total_ingredients,
            -self.supply_margin,
            -self.dish.sell_price,
            self.dish.name,
            self.added_ingredients,
        )
