# -*- coding: utf-8 -*-
"""
Food_Class.py
- 支持 Excel 表头“模糊匹配”（忽略大小写、首尾空格、全角空格、多空格）
- 字段名已同步到你的新表头：
  Budget / Preferred Tags / Disliked Tags / Spawn Areas / Beverage Tags / Tags
  Required Ingredients / Forbidden Ingredients / Owned / Buy Price / Sell Price / cookware / Level
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence, Optional, Iterable


# -----------------------------
#  Header / cell utils (fuzzy)
# -----------------------------
def norm_key(k: Any) -> str:
    """归一化表头：忽略大小写、首尾空格、全角空格、多空格。"""
    s = "" if k is None else str(k)
    s = s.replace("\u3000", " ")
    s = s.strip().lower()
    s = re.sub(r"\s+", " ", s)
    return s


def is_empty_cell(x: Any) -> bool:
    """None/NaN/空串 都当空。"""
    if x is None:
        return True
    try:
        # pandas/numpy 的 NaN
        if x != x:
            return True
    except Exception:
        pass
    s = str(x).strip()
    return (s == "" or s.lower() == "nan")


def row_norm_map(row: Any) -> dict[str, Any]:
    """
    把一行（dict/pandas.Series/类似 mapping）变成：
    {norm_key(col_name): value}
    """
    if hasattr(row, "items"):
        items = row.items()
    elif isinstance(row, Mapping):
        items = row.items()
    else:
        # fallback：当作对象属性
        items = ((k, getattr(row, k)) for k in dir(row))
    m: dict[str, Any] = {}
    for k, v in items:
        m[norm_key(k)] = v
    return m


def pick(row: Any, keys: Sequence[str], default: Any = None, *, _nmap: Optional[dict[str, Any]] = None) -> Any:
    """
    从 row 中按 keys 取值，支持模糊表头匹配。
    - keys 里写 "Name" 也能匹配到 "NAME"/" name "/全角空格等
    - 会跳过 None/NaN/空串
    """
    # 先尝试精确 key（最快）
    if hasattr(row, "get"):
        for k in keys:
            try:
                v = row.get(k)
                if not is_empty_cell(v):
                    return v
            except Exception:
                pass

    nmap = _nmap if _nmap is not None else row_norm_map(row)
    for k in keys:
        nk = norm_key(k)
        if nk in nmap and not is_empty_cell(nmap[nk]):
            return nmap[nk]
    return default


def find_df_col(df, keys: Sequence[str]) -> Optional[str]:
    """
    在 DataFrame 的 columns 里模糊匹配列名，返回实际列名（原样），找不到返回 None。
    """
    if df is None or getattr(df, "empty", True):
        return None
    col_map = {norm_key(c): c for c in df.columns}
    for k in keys:
        nk = norm_key(k)
        if nk in col_map:
            return col_map[nk]
    return None


# -----------------------------
#  Value parsing
# -----------------------------
_SPLIT_RE = re.compile(r"[、，,;；/|\n\r]+")

def to_list(x: Any) -> list[str]:
    """把单元格解析成 list[str]；支持多种分隔符；空 -> []。"""
    if is_empty_cell(x):
        return []
    s = str(x).strip()
    if not s:
        return []
    parts = [p.strip() for p in _SPLIT_RE.split(s) if p.strip()]
    return parts


def to_float(x: Any, default: float = 0.0) -> float:
    if is_empty_cell(x):
        return float(default)
    try:
        return float(str(x).strip())
    except Exception:
        return float(default)


def to_int(x: Any, default: int = 0) -> int:
    if is_empty_cell(x):
        return int(default)
    try:
        return int(float(str(x).strip()))
    except Exception:
        return int(default)


def to_bool_like(x: Any, default: bool = False) -> bool:
    if is_empty_cell(x):
        return default
    s = str(x).strip().lower()
    if s in {"1", "true", "yes", "y", "是", "有", "√", "owned"}:
        return True
    if s in {"0", "false", "no", "n", "否", "无", "×"}:
        return False
    # 数字兜底
    try:
        return float(s) != 0.0
    except Exception:
        return True


# -----------------------------
#  Domain classes
# -----------------------------
@dataclass
class Ingredient:
    name: str = ""
    icon: str = ""
    tags: list[str] = field(default_factory=list)
    buy_price: float = 0.0
    sell_price: float = 0.0
    level: int = 0
    is_owned: bool = False

    def __init__(self, row: Any):
        nmap = row_norm_map(row)
        self.name = str(pick(row, ["Name", "名称", "name"], "", _nmap=nmap) or "").strip()
        self.icon = str(pick(row, ["Icon", "图标", "icon"], "", _nmap=nmap) or "").strip()
        self.tags = to_list(pick(row, ["Tags", "标签", "tag", "tags"], "", _nmap=nmap))
        self.buy_price = to_float(pick(row, ["Buy Price", "进货价", "成本"], 0, _nmap=nmap), 0.0)
        self.sell_price = to_float(pick(row, ["Sell Price", "售价", "sell price", "price"], 0, _nmap=nmap), 0.0)
        self.level = to_int(pick(row, ["Level", "等级", "lv"], 0, _nmap=nmap), 0)
        self.is_owned = to_bool_like(pick(row, ["Owned", "持有", "拥有", "available"], 0, _nmap=nmap), False)

    # ---- compatibility aliases (尽量不在新代码里用，但保留避免老脚本炸) ----
    @property
    def lv(self):  # noqa
        return self.level

    @property
    def merchant(self):  # noqa
        return self.buy_price

    @property
    def price(self):  # noqa
        return self.sell_price

    @property
    def props(self):  # noqa
        return self.tags


@dataclass
class Drink:
    name: str = ""
    icon: str = ""
    tags: list[str] = field(default_factory=list)
    buy_price: float = 0.0
    sell_price: float = 0.0
    level: int = 0
    is_owned: bool = False
    profit: float = 0.0

    def __init__(self, row: Any):
        nmap = row_norm_map(row)
        self.name = str(pick(row, ["Name", "名称", "name"], "", _nmap=nmap) or "").strip()
        self.icon = str(pick(row, ["Icon", "图标", "icon"], "", _nmap=nmap) or "").strip()
        self.tags = to_list(pick(row, ["Tags", "标签", "tag", "tags"], "", _nmap=nmap))
        self.buy_price = to_float(pick(row, ["Buy Price", "进货价", "成本"], 0, _nmap=nmap), 0.0)
        self.sell_price = to_float(pick(row, ["Sell Price", "售价", "sell price", "price"], 0, _nmap=nmap), 0.0)
        self.level = to_int(pick(row, ["Level", "等级", "lv"], 0, _nmap=nmap), 0)
        self.is_owned = to_bool_like(pick(row, ["Owned", "持有", "拥有", "available"], 0, _nmap=nmap), False)
        self.profit = self.sell_price - self.buy_price

    @property
    def merchant(self):  # noqa
        return self.buy_price

    @property
    def price(self):  # noqa
        return self.sell_price

    @property
    def props(self):  # noqa
        return self.tags


@dataclass
class Food:
    name: str = ""
    icon: str = ""
    cookware: str = ""
    tags: list[str] = field(default_factory=list)
    required_ingredients: list[str] = field(default_factory=list)
    forbidden_ingredients: Optional[list[str]] = None  # None 表示“没有冲突限制”
    buy_price: float = 0.0
    sell_price: float = 0.0
    level: int = 0
    is_owned: bool = False

    # 运行时计算
    use_class: list[Ingredient] = field(default_factory=list)
    cost: float = 0.0
    cost_actual: float = 0.0
    profit: float = 0.0
    profit_actual: float = 0.0

    def __init__(self, row: Any):
        nmap = row_norm_map(row)

        self.use_class = []
        self.cost = 0.0
        self.cost_actual = 0.0
        self.profit = 0.0
        self.profit_actual = 0.0

        self.name = str(pick(row, ["Name", "名称", "name"], "", _nmap=nmap) or "").strip()
        self.icon = str(pick(row, ["Icon", "图标", "icon"], "", _nmap=nmap) or "").strip()
        self.cookware = str(pick(row, ["cookware", "Cookware", "厨具", "烹饪方式", "cook"], "", _nmap=nmap) or "").strip()

        self.sell_price = to_float(pick(row, ["Sell Price", "售价", "sell price", "price"], 0, _nmap=nmap), 0.0)
        self.buy_price = to_float(pick(row, ["Buy Price", "进货价", "成本", "merchant"], 0, _nmap=nmap), 0.0)

        self.tags = to_list(pick(row, ["Tags", "标签", "tag", "tags", "props"], "", _nmap=nmap))
        self.required_ingredients = to_list(pick(row, ["Required Ingredients", "材料", "食材", "基础食材", "useList"], "", _nmap=nmap))

        inv_raw = pick(row, ["Forbidden Ingredients", "禁忌", "不相容", "冲突", "invalidList"], None, _nmap=nmap)
        if is_empty_cell(inv_raw):
            self.forbidden_ingredients = None
        else:
            self.forbidden_ingredients = to_list(inv_raw)

        self.level = to_int(pick(row, ["Level", "等级", "lv"], 0, _nmap=nmap), 0)
        self.is_owned = to_bool_like(pick(row, ["Owned", "持有", "拥有", "available"], 0, _nmap=nmap), False)

    def after_init(self, ingredient_dict: Mapping[str, Ingredient]):
        """
        根据 required_ingredients 计算：cost / cost_actual / profit / profit_actual
        - cost: 食材 sell_price 累加
        - cost_actual: 食材 buy_price 累加
        """
        if not self.required_ingredients:
            return
        if "任意" in self.required_ingredients:
            return

        for name in self.required_ingredients:
            ing = ingredient_dict.get(name)
            if ing is not None:
                self.use_class.append(ing)

        self.cost = sum(float(getattr(ing, "sell_price", 0.0) or 0.0) for ing in self.use_class)
        self.cost_actual = sum(float(getattr(ing, "buy_price", 0.0) or 0.0) for ing in self.use_class)

        self.profit = self.sell_price - self.cost
        self.profit_actual = self.sell_price - self.cost_actual

    # -----------------------------
    #  Tag checks (used by 推荐逻辑)
    # -----------------------------
    def count_tag_overlap(self, tags: Iterable[str]) -> int:
        return len(set(self.tags).intersection(tags))

    def has_any_tag(self, tags: Iterable[str]) -> bool:
        return self.count_tag_overlap(tags) > 0

    # ---- compatibility aliases ----
    @property
    def cook(self):  # noqa
        return self.cookware

    @property
    def price(self):  # noqa
        return self.sell_price

    @property
    def merchant(self):  # noqa
        return self.buy_price

    @property
    def props(self):  # noqa
        return self.tags

    @property
    def useList(self):  # noqa
        return self.required_ingredients

    @property
    def invalidList(self):  # noqa
        return self.forbidden_ingredients

    # 老脚本里用到的名字：checkbyprops
    def checkbyprops(self, tag_list):  # noqa
        return self.count_tag_overlap(tag_list)
