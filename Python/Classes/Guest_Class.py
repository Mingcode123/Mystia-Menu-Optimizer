# -*- coding: utf-8 -*-
"""
Guest_Class.py
- 解析“普客/稀客”sheet 的一行数据（pandas.Series）
- 支持表头模糊匹配（忽略大小写/空格/全角空格）
- 字段名同步到新表头：
  Budget / Preferred Tags / Disliked Tags / Spawn Areas / Beverage Tags / Level / Name / Icon / type
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable

import Food_Class  # 复用 pick/to_list/to_float/to_int/to_bool_like 等工具


@dataclass
class Guest:
    name: str = ""
    icon: str = ""
    Type: str = ""   # 保持旧字段名 Type，兼容旧逻辑；值常见：rare / normal / 稀客 / 普客
    budget: float = 0.0
    preferred_tags: list[str] = field(default_factory=list)
    disliked_tags: list[str] = field(default_factory=list)
    spawn_areas: list[str] = field(default_factory=list)
    beverage_tags: list[str] = field(default_factory=list)
    level: int = 0

    def __init__(self, row: Any):
        nmap = Food_Class.row_norm_map(row)
        self.name = str(Food_Class.pick(row, ["Name", "名称", "name"], "", _nmap=nmap) or "").strip()
        self.icon = str(Food_Class.pick(row, ["Icon", "图标", "icon"], "", _nmap=nmap) or "").strip()

        type_raw = Food_Class.pick(row, ["type", "Type", "类型"], "", _nmap=nmap) or ""
        t = str(type_raw).strip()
        # 兼容各种写法
        tl = t.lower()
        if tl in {"rare", "r"} or t == "稀客":
            self.Type = "rare"
        elif tl in {"normal", "n"} or t == "普客":
            self.Type = "normal"
        else:
            self.Type = t  # 原样保留

        self.budget = Food_Class.to_float(Food_Class.pick(row, ["Budget", "预算", "money"], 0, _nmap=nmap), 0.0)

        self.preferred_tags = Food_Class.to_list(Food_Class.pick(
            row, ["Preferred Tags", "喜爱", "favList"], "", _nmap=nmap
        ))
        self.disliked_tags = Food_Class.to_list(Food_Class.pick(
            row, ["Disliked Tags", "厌恶", "dissList"], "", _nmap=nmap
        ))
        self.spawn_areas = Food_Class.to_list(Food_Class.pick(
            row, ["Spawn Areas", "出没地区", "distanceList"], "", _nmap=nmap
        ))
        self.beverage_tags = Food_Class.to_list(Food_Class.pick(
            row, ["Beverage Tags", "酒水tag", "drinkList"], "", _nmap=nmap
        ))
        self.level = Food_Class.to_int(Food_Class.pick(row, ["Level", "等级", "lv"], 0, _nmap=nmap), 0)

    # -----------------------------
    #  Methods used by existing logic
    # -----------------------------
    def checkbyfav(self, tag_list: Iterable[str]) -> int:
        """返回 喜爱tag 与 tag_list 的重叠数。"""
        return len(set(self.preferred_tags).intersection(tag_list))

    def checkbydiss(self, diss_list: Iterable[str]):
        """
        稀客才有“厌恶”判定：
        - 若命中厌恶，返回负数（-命中数）
        - 若未命中，返回 True
        其他类型返回 False
        """
        if self.Type != "rare":
            return False
        hit = len(set(self.disliked_tags).intersection(diss_list))
        return -hit if hit > 0 else True

    def checkbydistanceList(self, place: str) -> bool:
        """旧方法名：距离/出没地区判定。"""
        return place in self.spawn_areas

    def checkbydrink(self, drink_obj) -> int:
        """返回 酒水tag 与 drink.tags 的重叠数。"""
        drink_tags = getattr(drink_obj, "tags", None) or getattr(drink_obj, "props", []) or []
        return len(set(self.beverage_tags).intersection(drink_tags))

    # 新方法名（更语义化）
    def in_spawn_area(self, place: str) -> bool:
        return self.checkbydistanceList(place)

    # ---- compatibility aliases (旧字段名) ----
    @property
    def favList(self):  # noqa
        return self.preferred_tags

    @property
    def dissList(self):  # noqa
        return self.disliked_tags

    @property
    def distanceList(self):  # noqa
        return self.spawn_areas

    @property
    def drinkList(self):  # noqa
        return self.beverage_tags

    @property
    def money(self):  # noqa
        return self.budget
