"""Validated JSON row dictionaries in; portable JSON and CSV reports out."""

from __future__ import annotations

import csv
import json
import math
import re
from pathlib import Path

from .models import Dataset, Dish, Guest, Ingredient
from .rules import MAX_INGREDIENTS

DATA_FORMAT = "mystia-planner-data/v1"
_SPLIT = re.compile(r"[,，;；、\n\r\t|/]+")


def text(value: object) -> str:
    return "" if value is None else str(value).strip()


def names(value: object) -> tuple[str, ...]:
    """Keep repetitions: a recipe may consume the same ingredient twice."""
    if isinstance(value, (list, tuple)):
        return tuple(text(item) for item in value if text(item))
    return tuple(part.strip() for part in _SPLIT.split(text(value)) if part.strip())


def _key(value: object) -> str:
    return "".join(text(value).split()).casefold()


def pick(row: dict, *aliases: str, default=None):
    normalized = {_key(key): value for key, value in row.items()}
    for alias in aliases:
        value = normalized.get(_key(alias))
        if value is not None and text(value) != "":
            return value
    return default


def _number(value: object, field: str) -> float:
    try:
        if isinstance(value, bool):
            raise ValueError
        result = float(value)
    except (TypeError, ValueError):
        raise ValueError(f"{field}: expected a finite non-negative number, got {value!r}") from None
    if not math.isfinite(result) or result < 0:
        raise ValueError(f"{field}: expected a finite non-negative number, got {value!r}")
    return result


def _owned(value: object, field: str) -> bool:
    if value is None or text(value) == "":
        return False
    normalized = text(value).casefold()
    if normalized in {"1", "1.0", "true", "yes", "y", "是", "有", "√", "owned"}:
        return True
    if normalized in {"0", "0.0", "false", "no", "n", "否", "无", "×"}:
        return False
    raise ValueError(f"{field}: unrecognized Owned value {value!r}")


def _rows(sheets: dict, name: str) -> list[dict]:
    rows = sheets.get(name)
    if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
        raise ValueError(f"sheets.{name}: expected a list of row dictionaries")
    return [row for row in rows if any(value is not None and text(value) != "" for value in row.values())]


def dataset_from_dict(payload: dict) -> Dataset:
    if not isinstance(payload, dict) or payload.get("format") != DATA_FORMAT:
        raise ValueError(f"Input format must be {DATA_FORMAT!r}")
    sheets = payload.get("sheets")
    if not isinstance(sheets, dict):
        raise ValueError("sheets must be an object")
    metadata = payload.get("metadata", {})
    if not isinstance(metadata, dict):
        raise ValueError("metadata must be an object")

    quantities = {}
    for row in _rows(sheets, "食材merchant_data"):
        name = text(pick(row, "Name", "名称", "食材", "Ingredient"))
        if not name:
            raise ValueError("食材merchant_data: a non-empty row is missing Name")
        if name in quantities:
            raise ValueError(f"食材merchant_data: duplicate Name {name!r}")
        quantities[name] = _number(
            pick(row, "Total Daily Quantity", "TDQ", "每日数量", "每日供给"),
            f"食材merchant_data[{name}].Total Daily Quantity",
        )

    ingredients = {}
    for row in _rows(sheets, "食材"):
        name = text(pick(row, "Name", "名称", "食材", "Ingredient"))
        if not name:
            raise ValueError("食材: a non-empty row is missing Name")
        if name in ingredients:
            raise ValueError(f"食材: duplicate Name {name!r}")
        if name not in quantities:
            raise ValueError(f"食材[{name}]: missing named supply entry in 食材merchant_data")
        ingredients[name] = Ingredient(
            name, frozenset(names(pick(row, "Tags", "标签", "tag"))), quantities[name]
        )
    if not ingredients:
        raise ValueError("食材 must contain at least one ingredient")

    dishes = []
    seen = set()
    dish_rows = _rows(sheets, "料理")
    owned_aliases = ("Owned", "是否持有", "已持有", "available", "持有", "拥有")
    has_owned_column = any(_key(key) in {_key(alias) for alias in owned_aliases} for row in dish_rows for key in row)
    for row in dish_rows:
        name = text(pick(row, "Name", "名称", "料理", "Dish"))
        if not name or name in seen:
            raise ValueError(f"料理: missing or duplicate Name {name!r}")
        seen.add(name)
        owned = _owned(pick(row, *owned_aliases), f"料理[{name}]") if has_owned_column else True
        required = names(pick(row, "Required Ingredients", "必需食材", "useList", "材料", "基础食材"))
        cookware = text(pick(row, "Cookware", "厨具", "Cook", "Cookware Tag"))
        if owned:
            if not 1 <= len(required) <= MAX_INGREDIENTS:
                raise ValueError(f"料理[{name}]: an owned recipe must use 1–{MAX_INGREDIENTS} base ingredients")
            missing = sorted(set(required) - ingredients.keys())
            if missing:
                raise ValueError(f"料理[{name}]: unknown base ingredient(s): {', '.join(missing)}")
            if not cookware:
                raise ValueError(f"料理[{name}]: an owned recipe needs Cookware")
        dishes.append(Dish(
            name=name,
            tags=frozenset(names(pick(row, "Tags", "标签", "tag"))),
            cookware=cookware,
            sell_price=_number(pick(row, "Sell Price", "售价", "Price", "卖价", default=0), f"料理[{name}].Sell Price"),
            required_ingredients=required,
            forbidden_entries=names(pick(row, "Forbidden Ingredients", "禁止食材", "invalidList", "Forbidden")),
            owned=owned,
        ))

    guests = []
    seen = set()
    for row in _rows(sheets, "稀客"):
        name = text(pick(row, "Name", "名称", "稀客", "Guest", "客人", "稀客名", "姓名"))
        preferred = names(pick(row, "Preferred Tags", "喜爱", "favList", "喜欢标签", "偏好", "喜好"))
        disliked = names(pick(row, "Disliked Tags", "厌恶", "dissList", "讨厌标签", "讨厌", "不喜欢"))
        budget = text(pick(row, "Budget", "预算", "money"))
        # Preserve the original workbook's merged-cell continuation convention.
        if not name:
            if not guests:
                raise ValueError("稀客: a continuation row appears before any named guest")
            prior = guests[-1]
            guests[-1] = Guest(
                prior.name,
                tuple(dict.fromkeys(prior.preferred_tags + preferred)),
                prior.disliked_tags | frozenset(disliked),
                prior.budget or budget,
            )
            continue
        if name in seen:
            raise ValueError(f"稀客: duplicate Name {name!r}")
        seen.add(name)
        guests.append(Guest(name, tuple(dict.fromkeys(preferred)), frozenset(disliked), budget))
    if not guests:
        raise ValueError("稀客 must contain at least one named guest")
    return Dataset(ingredients, tuple(dishes), tuple(guests), dict(metadata))


def load_dataset(path: str | Path) -> Dataset:
    def reject_constant(value: str):
        raise ValueError(f"Invalid JSON numeric constant: {value}")
    with Path(path).open(encoding="utf-8-sig") as handle:
        payload = json.load(handle, parse_constant=reject_constant)
    return dataset_from_dict(payload)


def write_json_report(report: dict, path: str | Path) -> None:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def write_csv_report(report: dict, path: str | Path) -> None:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    columns = ["guest", "status", "dish", "cookware", "sell_price", "base_ingredients", "added_ingredients", "final_tags", "covered_tags", "score", "coverage_capped", "total_ingredients", "supply_margin"]
    with destination.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        for result in report["guests"]:
            row = {"guest": result["guest"], "status": result["status"]}
            plan = result.get("plan")
            if plan:
                for field in columns[2:]:
                    value = plan.get(field, "")
                    row[field] = "、".join(value) if isinstance(value, list) else value
            # CSV is intended to be opened in spreadsheet software as plain data.
            for key, value in row.items():
                if isinstance(value, str) and value.startswith(("=", "+", "-", "@")):
                    row[key] = "'" + value
            writer.writerow(row)
