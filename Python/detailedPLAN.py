#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Izakaya guest plan generator (TDQ-aware).

Reads:   ../东方夜雀食堂.xlsx   (relative to this .py file)
Writes:  ../稀客料理表*.xlsx (auto-named)

Per guest, the objective is:

Stage 1 (Ecost-minimal per tag):
  For each preferred tag t, consider all dish+add-on plans that:
    - use only owned dishes
    - satisfy score >= min_score (score computed against ALL preferred/disliked tags)
    - have no disliked tags in the FINAL tag set (after cover rules + trend tagging)
    - respect dish-level forbidden rules
    - apply add-on subset filter + advanced-ingredient plan filter (both do NOT consider score)
    - apply add-on equivalent-ingredient dedup (equivalence = identical ingredient tag set)
  Keep ALL plans with minimal total ingredient count for that tag.

Stage 2 (maximize inf_tdq among Stage 1 options):
  Choose one plan for each preferred tag, maximizing
    inf_tdq = min_{ingredient used} ( q_i - (K/m) * total_used_i )
  where:
    q_i = ingredient's real TDQ (from merchant table),
    K   = expected orders per day (default 5),
    m   = number of preferred tags for the guest,
    total_used_i = sum over tags of ingredient i count in the chosen plan for that tag
                   (counts include BOTH base and added ingredients).

Implementation:
  Stage 2 is solved by discrete-lambda binary search with DFS feasibility.

Notes for output Excel (per user's latest spec):
  - Preferred Tags rendered as multiline in one cell.
  - Merge guest block (Name/Budget/Preferred Tags).
  - Merge by Dish (Dish..Base Ingredients), even if Added differs.
  - Merge by Dish+Added (Added Ingredients + Tags).
"""

from __future__ import annotations

import argparse
import os
import re
import time
import math
import unicodedata
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Set, Tuple

import openpyxl
from openpyxl.styles import Alignment, Font
from openpyxl.utils import get_column_letter

# Progress update frequency when scanning dishes in Stage 1
PROGRESS_EVERY = 10



# -----------------------------
# Fixed switches (per your requirement)
# -----------------------------
MIN_SCORE_DEFAULT = 3
ORDERS_PER_DAY_DEFAULT = 5

EQ_ING_DEDUP = True                 # only for ADD-ONS
SUBSET_FILTER = True               # add-on subset filter (方案级)
SUBSET_SCORE_FILTER = False        # “不考虑得分”
ING_UPGRADE_FILTER = True          # advanced-ingredient plan filter (方案级)
ING_UPGRADE_SCORE_FILTER = False   # “不考虑得分”

PREFERRED_EQ_REPS = ["猪肉","鳟鱼","三文鱼","河豚","极上金枪鱼","海苔","豆腐","桃子","白果"]
HARD_EXCLUDE_ADDON = {"铃仙"}


# -----------------------------
# Helpers: parsing / normalization
# -----------------------------
_SPLIT_RE = re.compile(r"[,，;；、\n\r\t|/]+")

def _s(v) -> str:
    if v is None:
        return ""
    if isinstance(v, str):
        return v.strip()
    return str(v).strip()

def split_list(v) -> List[str]:
    txt = _s(v)
    if not txt:
        return []
    return [p.strip() for p in _SPLIT_RE.split(txt) if p.strip()]

def norm_key(s: str) -> str:
    s = _s(s).lower()
    s = s.replace(" ", "").replace("\u3000", "")
    return s

def as_int(v, default=0) -> int:
    try:
        if v is None or v == "":
            return default
        if isinstance(v, (int, float)):
            return int(v)
        return int(float(str(v)))
    except Exception:
        return default

def as_float(v, default=0.0) -> float:
    try:
        if v is None or v == "":
            return default
        if isinstance(v, (int, float)):
            return float(v)
        return float(str(v))
    except Exception:
        return default

def price_tag(price: float) -> Optional[str]:
    if price <= 0:
        return None
    if price < 20:
        return "实惠"
    if price > 60:
        return "昂贵"
    return None

def apply_cover_overrides(tagset: Set[str]) -> Set[str]:
    ts = set(tagset)
    rules = [("肉", "素"), ("饱腹", "下酒"), ("重油", "清淡"), ("大份", "小巧")]
    for stronger, weaker in rules:
        if stronger in ts and weaker in ts:
            ts.discard(weaker)
    return ts


# -----------------------------
# Data models
# -----------------------------
@dataclass(frozen=True)
class Ingredient:
    name: str
    tags: Tuple[str, ...]  # unique, sorted

@dataclass
class Dish:
    name: str
    tags: Tuple[str, ...]
    cookware: str
    sell_price: float
    required_ingredients: List[str]
    forbidden_entries: List[str]  # may be ingredient names OR tags
    owned: bool

@dataclass
class Guest:
    name: str
    budget: str
    preferred_tags: List[str]
    disliked_tags: List[str]

@dataclass
class Candidate:
    dish: Dish
    base_names: Tuple[str, ...]
    added_names: Tuple[str, ...]            # (possibly eq-dedup rep names)
    added_names_final: Tuple[str, ...]      # after TDQ-max replacement within eq groups
    tagset: Tuple[str, ...]                 # final tags (after cover + trend)
    score: int
    total_ing: int                          # base + added
    orig_key: str                           # multiset key over added_names
    norm_key: str                           # orig_key after baseRep mapping
    advanced: bool                           # any add-on uses advanced ingredient
    added_counts: Counter
    total_counts: Counter

    @property
    def added_str(self) -> str:
        return "、".join(self.added_names_final)

    @property
    def base_str(self) -> str:
        return "、".join(self.base_names)

    @property
    def tags_str(self) -> str:
        return "、".join(self.tagset)


# -----------------------------
# Excel reading
# -----------------------------
def sheet_rows_as_dicts(ws) -> List[Dict[str, object]]:
    rows = list(ws.iter_rows(values_only=True))
    if not rows:
        return []
    headers = [(_s(h) if h is not None else "") for h in rows[0]]
    out = []
    for r in rows[1:]:
        if all((c is None or _s(c) == "") for c in r):
            continue
        out.append({headers[i]: r[i] if i < len(r) else None for i in range(len(headers))})
    return out

def pick_col(row: Dict[str, object], *candidates: str, default=""):
    # direct hit
    for k in candidates:
        if k in row and row[k] is not None and _s(row[k]) != "":
            return row[k]
    # normalized hit
    nk_to_key = {norm_key(k): k for k in row.keys()}
    for k in candidates:
        nk = norm_key(k)
        if nk in nk_to_key:
            v = row[nk_to_key[nk]]
            if v is not None and _s(v) != "":
                return v
    return default

def parse_ingredients(wb) -> Dict[str, Ingredient]:
    ws = wb["食材"]
    rows = sheet_rows_as_dicts(ws)
    ing: Dict[str, Ingredient] = {}
    for r in rows:
        name = _s(pick_col(r, "Name", "名称", "食材", "Ingredient"))
        if not name:
            continue
        tags = split_list(pick_col(r, "Tags", "标签", "tag", "tags"))
        ing[name] = Ingredient(name=name, tags=tuple(sorted(set(tags))))
    return ing

def parse_dishes(wb) -> List[Dish]:
    ws = wb["料理"]
    rows = sheet_rows_as_dicts(ws)
    # If the sheet does not contain an Owned/available column, default to treating all dishes as owned.
    nk_headers = {norm_key(k) for k in rows[0].keys()} if rows else set()
    has_owned_col = any(norm_key(k) in nk_headers for k in ["Owned", "是否持有", "已持有", "available"])
    if not has_owned_col:
        print("⚠️ 料理表未找到 Owned 列（或全部为空），将默认把所有料理视为 Owned=1（用于避免全员无方案）。")
    out: List[Dish] = []
    for r in rows:
        name = _s(pick_col(r, "Name", "名称", "料理", "Dish"))
        if not name:
            continue
        tags = split_list(pick_col(r, "Tags", "标签", "tag", "tags"))
        cookware = _s(pick_col(r, "Cookware", "厨具", "Cook", "Cookware Tag"))
        sell_price = as_float(pick_col(r, "Sell Price", "售价", "Price", "卖价"), default=0.0)
        req = split_list(pick_col(r, "Required Ingredients", "必需食材", "useList"))
        forb = split_list(pick_col(r, "Forbidden Ingredients", "禁止食材", "invalidList", "Forbidden"))
        if has_owned_col:
            owned_val = pick_col(r, "Owned", "是否持有", "已持有", "available", default="")
            owned = (as_int(owned_val, 0) == 1)
        else:
            owned = True
        out.append(Dish(
            name=name,
            tags=tuple(sorted(set(tags))),
            cookware=cookware,
            sell_price=sell_price,
            required_ingredients=req,
            forbidden_entries=forb,
            owned=owned,
        ))
    return out

def parse_guests(wb) -> List[Guest]:
    """Parse '稀客' sheet.

    Robustness:
      - Supports slightly different header names (Name/名称/稀客/Guest/客人/稀客名/姓名).
      - If the sheet uses merged cells / continuation rows where Name is blank,
        we treat the row as continuing the previous guest and extend tags.
    """
    ws = wb["稀客"]
    rows = sheet_rows_as_dicts(ws)
    out: List[Guest] = []

    for idx, r in enumerate(rows, 1):
        name = _s(pick_col(r, "Name", "名称", "稀客", "Guest", "客人", "稀客名", "姓名"))
        budget = _s(pick_col(r, "Budget", "预算", "money"))
        pref = split_list(pick_col(r, "Preferred Tags", "喜爱", "favList", "喜欢标签", "偏好", "喜好"))
        diss = split_list(pick_col(r, "Disliked Tags", "厌恶", "dissList", "讨厌标签", "讨厌", "不喜欢"))

        # Continuation row: name empty but has content -> merge into previous guest
        if not name:
            has_payload = bool(budget or pref or diss)
            if has_payload and out:
                g = out[-1]
                if budget and not g.budget:
                    g.budget = budget
                if pref:
                    g.preferred_tags.extend(pref)
                if diss:
                    g.disliked_tags.extend(diss)
            continue

        out.append(Guest(name=name, budget=budget, preferred_tags=pref, disliked_tags=diss))

    return out
def parse_tdq_raw(wb) -> Dict[str, float]:
    ws = wb["食材merchant_data"]
    rows = sheet_rows_as_dicts(ws)
    tdq: Dict[str, float] = {}
    for r in rows:
        name = _s(pick_col(r, "Name", "名称", "食材", "Ingredient"))
        if not name:
            continue
        q = pick_col(r, "Total Daily Quantity", "TDQ", "每日数量", "每日供给")
        tdq[name] = as_float(q, default=0.0)
    return tdq


# -----------------------------
# Equivalent ingredient signatures (by identical tag sets)
# -----------------------------
def build_sig_key(tags: Tuple[str, ...]) -> str:
    if not tags:
        return "__EMPTY__"
    return "|".join(tags)

def build_ing_sig_maps(ingredients: Dict[str, Ingredient], tdq_raw: Dict[str, float]) -> Tuple[Dict[str, str], Dict[str, List[str]]]:
    ing_sig: Dict[str, str] = {}
    sig_members: Dict[str, List[str]] = defaultdict(list)

    for name, ing in ingredients.items():
        sig = build_sig_key(ing.tags)
        if sig == "__EMPTY__":
            sig = f"__EMPTY__:{name}"
        ing_sig[name] = sig
        sig_members[sig].append(name)

    pref_rank = {n: i for i, n in enumerate(PREFERRED_EQ_REPS)}
    def member_sort_key(n: str):
        return (-tdq_raw.get(n, 0.0), pref_rank.get(n, 10**9), n)

    for sig, arr in sig_members.items():
        arr.sort(key=member_sort_key)

    return ing_sig, sig_members

def dedup_allowed_by_sig(allowed: List[str], ing_sig: Dict[str, str]) -> List[str]:
    pref_rank = {n: i for i, n in enumerate(PREFERRED_EQ_REPS)}
    best_by_sig: Dict[str, str] = {}
    for name in allowed:
        sig = ing_sig.get(name, f"__EMPTY__:{name}")
        if sig not in best_by_sig:
            best_by_sig[sig] = name
            continue
        cur = best_by_sig[sig]
        a = (pref_rank.get(name, 10**9), name)
        b = (pref_rank.get(cur, 10**9), cur)
        if a < b:
            best_by_sig[sig] = name

    sig_seen: Set[str] = set()
    out: List[str] = []
    for name in allowed:
        sig = ing_sig.get(name, f"__EMPTY__:{name}")
        if sig in sig_seen:
            continue
        rep = best_by_sig[sig]
        if name == rep:
            out.append(name)
            sig_seen.add(sig)

    if len(out) != len(best_by_sig):
        for sig, rep in best_by_sig.items():
            if sig not in sig_seen:
                out.append(rep)
                sig_seen.add(sig)

    return out


# -----------------------------
# Advanced ingredient mapping (baseRep)
# -----------------------------
def build_base_rep(allowed_ing_names: List[str], ingredients: Dict[str, Ingredient]) -> Dict[str, str]:
    tagset = {n: set(ingredients[n].tags) for n in allowed_ing_names if n in ingredients}
    names_sorted = sorted(allowed_ing_names, key=lambda n: (len(tagset.get(n, set())), n))

    base_rep: Dict[str, str] = {n: n for n in allowed_ing_names}
    for x in allowed_ing_names:
        ts_x = tagset.get(x, None)
        if ts_x is None:
            continue
        best = x
        best_sz = len(ts_x)
        for y in names_sorted:
            if y == x:
                continue
            ts_y = tagset.get(y, None)
            if ts_y is None:
                continue
            if len(ts_y) >= best_sz:
                break
            if ts_y < ts_x:
                best = y
                best_sz = len(ts_y)
        base_rep[x] = best
    return base_rep

def multiset_key(items: Sequence[str]) -> str:
    if not items:
        return ""
    c = Counter(items)
    return "|".join(f"{k}*{c[k]}" for k in sorted(c.keys()))

def norm_key_by_base_rep(items: Sequence[str], base_rep: Dict[str, str]) -> Tuple[str, bool]:
    if not items:
        return ("", False)
    mapped = [base_rep.get(x, x) for x in items]
    adv = any(base_rep.get(x, x) != x for x in items)
    return (multiset_key(mapped), adv)


# -----------------------------
# Candidate enumeration (per dish, per guest) + pruning
# -----------------------------
def compute_score(tagset: Set[str], fav: Set[str], diss: Set[str]) -> int:
    return sum((1 if t in fav else -1 if t in diss else 0) for t in tagset)

def add_trend_tags(tagset: Set[str], trend_like_anchors: Set[str], trend_hate_anchors: Set[str]) -> Set[str]:
    ts = set(tagset)
    if trend_like_anchors and (ts & trend_like_anchors):
        ts.add("流行·喜爱")
    if trend_hate_anchors and (ts & trend_hate_anchors):
        ts.add("流行·厌恶")
    return ts

def _forbidden_split(dish: Dish, ingredients: Dict[str, Ingredient]) -> Tuple[Set[str], Set[str]]:
    forb_names: Set[str] = set()
    forb_tags: Set[str] = set()
    all_ing_names = set(ingredients.keys())
    for x in dish.forbidden_entries:
        x = _s(x)
        if not x:
            continue
        if x in all_ing_names:
            forb_names.add(x)
        else:
            forb_tags.add(x)
    return forb_names, forb_tags

def build_dish_pool_for_guest(
    guest: Guest,
    dish: Dish,
    ingredients: Dict[str, Ingredient],
    tdq_raw: Dict[str, float],
    ing_sig: Dict[str, str],
    sig_members_sorted: Dict[str, List[str]],
    min_score: int,
    trend_like_anchors: Set[str],
    trend_hate_anchors: Set[str],
) -> List[Candidate]:
    fav = set(guest.preferred_tags)
    diss = set(guest.disliked_tags)

    base_names = tuple([n for n in dish.required_ingredients if n])
    base_count = len(base_names)
    max_extra = max(0, 5 - base_count)

    all_ing_names = [n for n in ingredients.keys() if n not in HARD_EXCLUDE_ADDON]
    forb_names, forb_tags = _forbidden_split(dish, ingredients)

    allowed = []
    for n in all_ing_names:
        if n in forb_names:
            continue
        if forb_tags:
            if set(ingredients[n].tags) & forb_tags:
                continue
        allowed.append(n)

    allowed_all = allowed

    # Speed: keep only add-ons that can actually affect feasibility/score for this guest.
    # If an ingredient's tags never intersect the guest's scoring/trigger tags, using it can never help reach min_score
    # (and would only increase total ingredients), so we safely drop it from enumeration.
    trigger_tags: Set[str] = set(fav)
    if "流行·喜爱" in fav:
        trigger_tags |= set(trend_like_anchors)
    if "流行·厌恶" in fav:
        trigger_tags |= set(trend_hate_anchors)

    # Cover rules: if a guest dislikes a weaker tag, we may need its stronger tag to "cover" it.
    cover_rules = [("肉", "素"), ("饱腹", "下酒"), ("重油", "清淡"), ("大份", "小巧")]
    for strong, weak in cover_rules:
        if weak in diss and strong not in diss:
            trigger_tags.add(strong)

    allowed_useful: List[str] = []
    if trigger_tags:
        for n in allowed:
            if set(ingredients[n].tags) & trigger_tags:
                allowed_useful.append(n)

    if allowed_useful:
        allowed = allowed_useful

        # If the guest likes 大份, sometimes we still need a "neutral filler" add-on (to reach total=5)
        # even when no scoring/trigger add-on is feasible. Keep a few safe fillers to preserve correctness.
        if "大份" in fav and base_count < 5 and max_extra > 0:
            fillers: List[str] = []
            for n in allowed_all:
                if n in allowed:
                    continue
                if set(ingredients[n].tags) & diss:
                    continue
                if set(ingredients[n].tags) & trigger_tags:
                    continue  # keep fillers neutral
                fillers.append(n)
                if len(fillers) >= 3:
                    break
            allowed.extend(fillers)

    else:
        # No add-on can influence score/feasibility.
        # Only keep a few "safe fillers" if the guest likes 大份 (needs any add-on to reach total=5).
        allowed = []
        if "大份" in fav and base_count < 5 and max_extra > 0:
            for n in allowed_all:
                if not (set(ingredients[n].tags) & diss):
                    allowed.append(n)
                if len(allowed) >= 3:
                    break

    if EQ_ING_DEDUP:
        allowed = dedup_allowed_by_sig(allowed, ing_sig)

    base_rep = build_base_rep(allowed, ingredients)

    pt = price_tag(dish.sell_price)
    dish_tag_base = set(dish.tags)
    if dish.cookware:
        dish_tag_base.add(dish.cookware)
    if pt:
        dish_tag_base.add(pt)


    # Tag rule (match INDEX.html): total tags = dish's own tags + cookware tag + price tag + add-on ingredient tags.
    # IMPORTANT: Base required ingredients' tags are NOT merged into tagset.
    base_tagset = set(dish_tag_base)

    # Safe optimistic upper bound for pruning:
    # only count +fav (ignore -diss), and allow one-time bonus tags (大份 / trend tags).
    base_fav = sum(1 for t in base_tagset if t in fav)

    potential_dafen = 1 if ("大份" in fav and base_count < 5 and max_extra > 0) else 0

    can_trigger_trend_like = bool(trend_like_anchors) and (
        bool(base_tagset & trend_like_anchors) or any((set(ingredients[n].tags) & trend_like_anchors) for n in allowed)
    )
    can_trigger_trend_hate = bool(trend_hate_anchors) and (
        bool(base_tagset & trend_hate_anchors) or any((set(ingredients[n].tags) & trend_hate_anchors) for n in allowed)
    )
    potential_trend_like = 1 if ("流行·喜爱" in fav and can_trigger_trend_like) else 0
    potential_trend_hate = 1 if ("流行·厌恶" in fav and can_trigger_trend_hate) else 0

    base_fav_upper = base_fav + potential_dafen + potential_trend_like + potential_trend_hate


    delta_pos: List[int] = []
    for n in allowed:
        its = set(ingredients[n].tags)
        delta = sum(1 for t in its if t in fav)
        delta_pos.append(max(0, delta))

    suffix_max: List[int] = [0] * (len(allowed) + 1)
    for i in range(len(allowed) - 1, -1, -1):
        suffix_max[i] = max(suffix_max[i + 1], delta_pos[i])

    if base_fav_upper + max_extra * suffix_max[0] < min_score:
        return []

    allowed_set = set(allowed)
    best_allowed_by_sig: Dict[str, str] = {}
    for n in allowed:
        sig = ing_sig.get(n, f"__EMPTY__:{n}")
        for cand_name in sig_members_sorted.get(sig, [n]):
            if cand_name in forb_names:
                continue
            best_allowed_by_sig[sig] = cand_name
            break
        if sig not in best_allowed_by_sig:
            best_allowed_by_sig[sig] = n

    pool: List[Candidate] = []
    chosen_idx: List[int] = []

    def dfs(start_i: int, k_left: int, pos_upper: int):
        # IMPORTANT: pruning must depend on what we've already chosen.
        # pos_upper is an *upper bound* on the number of +fav tags we can still achieve
        # (we purposely ignore -diss here, so pruning stays safe).
        if pos_upper + k_left * suffix_max[start_i] < min_score:
            return
        if k_left == 0:
            added = tuple(allowed[i] for i in chosen_idx)

            raw_ts = set(dish_tag_base)
            for an in added:
                raw_ts.update(ingredients[an].tags)

            # forbiddenIngredients only restricts "extra add-ons";
            # we've already filtered allowed add-ons by forbidden entries (names/tags) above.

            total_ing = base_count + len(added)
            ts = set(raw_ts)
            if total_ing == 5 and len(added) > 0:
                ts.add("大份")

            ts = apply_cover_overrides(ts)
            ts = add_trend_tags(ts, trend_like_anchors, trend_hate_anchors)

            if diss and (ts & diss):
                return

            sc = compute_score(ts, fav, diss)
            if sc < min_score:
                return

            orig = multiset_key(added)
            norm, adv = norm_key_by_base_rep(added, base_rep)

            added_final_list = []
            for an in added:
                sig = ing_sig.get(an, f"__EMPTY__:{an}")
                added_final_list.append(best_allowed_by_sig.get(sig, an))
            added_final = tuple(added_final_list)

            added_counts = Counter(added_final)
            total_counts = Counter(base_names)
            total_counts.update(added_final)

            pool.append(Candidate(
                dish=dish,
                base_names=base_names,
                added_names=added,
                added_names_final=added_final,
                tagset=tuple(sorted(ts)),
                score=sc,
                total_ing=total_ing,
                orig_key=orig,
                norm_key=norm,
                advanced=adv,
                added_counts=added_counts,
                total_counts=total_counts,
            ))
            return

        for i in range(start_i, len(allowed)):
            chosen_idx.append(i)
            dfs(i, k_left - 1, pos_upper + delta_pos[i])
            chosen_idx.pop()

    for k in range(0, max_extra + 1):
        chosen_idx.clear()
        dfs(0, k, base_fav_upper)

    uniq: Dict[Tuple[str, str], Candidate] = {}
    for c in pool:
        key = (c.dish.name, c.orig_key)
        if key not in uniq:
            uniq[key] = c
        else:
            cur = uniq[key]
            if (c.score, -len(c.added_names_final), c.added_str) > (cur.score, -len(cur.added_names_final), cur.added_str):
                uniq[key] = c
    return list(uniq.values())


# -----------------------------
# Post filters (per required tag)
# -----------------------------
def apply_ing_upgrade_filter(cands: List[Candidate], score_filter: bool) -> List[Candidate]:
    if not cands:
        return []
    by_norm: Dict[str, List[Candidate]] = defaultdict(list)
    for c in cands:
        by_norm[c.norm_key].append(c)

    out: List[Candidate] = []
    for nk, arr in by_norm.items():
        if len(arr) == 1:
            out.extend(arr)
            continue
        has_base = any((not c.advanced) for c in arr)
        for c in arr:
            if not c.advanced:
                out.append(c)
            else:
                if score_filter:
                    if any((not b.advanced and b.score >= c.score) for b in arr):
                        continue
                    out.append(c)
                else:
                    if has_base:
                        continue
                    out.append(c)
    return out

def _is_proper_sub_multiset(a: Counter, b: Counter) -> bool:
    strict = False
    for k, av in a.items():
        bv = b.get(k, 0)
        if av > bv:
            return False
        if av < bv:
            strict = True
    if not strict:
        for k, bv in b.items():
            if k not in a and bv > 0:
                return True
    return strict

def apply_subset_filter(cands: List[Candidate], score_filter: bool) -> List[Candidate]:
    """加料子集过滤（对同一道菜、同一 requiredTag 子候选集生效）

    语义（与 INDEX.html 对齐）：
    - 对 added multiset（基于“加料代表名”，未做 TDQ 替换）做多重集子集判定；
    - 若存在已保留方案 S，使得 added(S) 是 added(C) 的真子集：
        - 若 score_filter=False：直接认为 C 被支配，删除 C；
        - 若 score_filter=True ：仅当 score(S) >= score(C) 时删除 C。
    实现：O(M * 2^k)（k<=5 的加料位数），避免 O(M^2)。
    """
    if not cands:
        return []

    def _rep_counts_key(added_names: Tuple[str, ...]) -> Tuple[Dict[str, int], str, int]:
        # counts + canonical key + totalAdded
        cnt: Dict[str, int] = {}
        total = 0
        for nm in added_names:
            if not nm:
                continue
            cnt[nm] = cnt.get(nm, 0) + 1
            total += 1
        key = multiset_key(added_names)
        return cnt, key, total

    arr: List[Tuple[Candidate, Dict[str, int], str, int]] = []
    for c in cands:
        cnt, key, total = _rep_counts_key(c.added_names)
        arr.append((c, cnt, key, total))

    # totalAdded 升序，score 降序（考虑得分时），再按 key 稳定排序
    if score_filter:
        arr.sort(key=lambda x: (x[3], -x[0].score, x[2]))
    else:
        arr.sort(key=lambda x: (x[3], x[2]))

    best_score_by_key: Dict[str, int] = {}

    def _is_dominated_by_subset(counts: Dict[str, int], full_key: str, score: int) -> bool:
        # Generate all subset keys (multi-set) and check in best_score_by_key.
        items = sorted([(k, v) for k, v in counts.items() if v > 0], key=lambda kv: kv[0])

        dominated = False

        def rec(i: int, parts: List[str]):
            nonlocal dominated
            if dominated:
                return
            if i == len(items):
                key = "|".join(parts)
                if key == full_key:
                    return
                if key in best_score_by_key:
                    if (not score_filter) or (best_score_by_key[key] >= score):
                        dominated = True
                return
            name, cnt = items[i]
            # 0..cnt
            for k in range(0, cnt + 1):
                if dominated:
                    return
                if k == 0:
                    rec(i + 1, parts)
                else:
                    parts.append(f"{name}*{k}")
                    rec(i + 1, parts)
                    parts.pop()

        rec(0, [])
        return dominated

    kept: List[Candidate] = []
    for c, cnt, key, total in arr:
        if _is_dominated_by_subset(cnt, key, c.score):
            continue
        prev = best_score_by_key.get(key)
        if prev is None or c.score > prev:
            best_score_by_key[key] = c.score
        kept.append(c)

    return kept

def remaining_vec(selection: Dict[str, Candidate], tdq_raw: Dict[str, float], orders_per_day: int) -> List[float]:
    tags = list(selection.keys())
    m = max(1, len(tags))
    step = orders_per_day / m

    cons = Counter()
    for t in tags:
        cons.update(selection[t].total_counts)

    vec = []
    for ing, cnt in cons.items():
        qi = tdq_raw.get(ing, 0.0)
        vec.append(qi - step * cnt)
    vec.sort()
    return vec

def solve_max_inf_tdq(
    tags: List[str],
    options: Dict[str, List[Candidate]],
    tdq_raw: Dict[str, float],
    orders_per_day: int,
) -> Optional[Dict[str, Candidate]]:
    """
    Stage 2: maximize inf_tdq among Stage 1 options.

    Objective:
      inf_tdq = min_{ingredient used} ( q_i - (K/m) * total_used_i )
    where K=orders_per_day, m=#tags.

    We solve max-lambda with monotone feasibility:
      feasible(lambda) iff exists a selection (one option per tag) such that
      for every used ingredient i:
        total_used_i <= floor((q_i - lambda) / step)
    where step = K/m.

    Then for best lambda, we choose the selection that maximizes the full
    remaining vector (sorted ascending).  This implementation is optimized
    for speed but preserves the exact same objective + tie-breaking behavior.
    """
    from functools import lru_cache
    import sys

    if not tags:
        return {}
    for t in tags:
        if not options.get(t):
            return None

    m = len(tags)
    K = orders_per_day
    step = K / m

    # ---- Reduce branching: de-dup options per tag by total_counts multiset key ----
    # Use a tuple key (faster than building strings); tie-break identical to previous.
    def counts_key(cnt: Counter) -> Tuple[Tuple[str, int], ...]:
        return tuple(sorted(cnt.items()))

    reduced: Dict[str, List[Candidate]] = {}
    for t in tags:
        best_by_cnt: Dict[Tuple[Tuple[str, int], ...], Candidate] = {}
        for c in options[t]:
            k = counts_key(c.total_counts)
            prev = best_by_cnt.get(k)
            if prev is None:
                best_by_cnt[k] = c
            else:
                # prefer higher score, then fewer ingredients, then higher price as a stable tie-break
                if (c.score, -c.total_ing, c.dish.sell_price) > (prev.score, -prev.total_ing, prev.dish.sell_price):
                    best_by_cnt[k] = c
        reduced[t] = list(best_by_cnt.values())
        if not reduced[t]:
            return None
    options = reduced

    # Choose an order that reduces branching (same as before).
    tags_ordered = sorted(tags, key=lambda t: (len(options[t]), t))

    # Ingredients that can possibly appear in any selection
    used_ings: Set[str] = set()
    for t in tags_ordered:
        for c in options[t]:
            used_ings.update(c.total_counts.keys())

    # Map ingredient -> small int id (deterministic) for faster DP keys/merges.
    ing_list = sorted(used_ings)
    ing_to_id: Dict[str, int] = {name: i for i, name in enumerate(ing_list)}
    qi_arr: List[float] = [float(tdq_raw.get(name, 0.0)) for name in ing_list]
    n_ing = len(ing_list)

    # Max possible total count per ingredient across all tags (since each tag plan uses <=5 ingredients).
    max_u = 5 * m

    # Precompute remainder table to avoid repeated float arithmetic at DP leaves.
    # rem[i][u] = qi_i - step*u
    rem_table: List[List[float]] = []
    for qi in qi_arr:
        rem_table.append([qi - step * u for u in range(max_u + 1)])

    # Cache each candidate's ingredient-counts as a *flat* tuple: (id0,c0,id1,c1,...), sorted by id.
    _cand_items_flat_cache: Dict[int, Tuple[int, ...]] = {}
    for t in tags_ordered:
        for c in options[t]:
            pairs = [(ing_to_id[ing], int(cnt)) for ing, cnt in c.total_counts.items() if cnt]
            pairs.sort()
            flat: List[int] = []
            for iid, cnt in pairs:
                flat.append(iid)
                flat.append(cnt)
            _cand_items_flat_cache[id(c)] = tuple(flat)

    # ---- Discretize lambda candidates: q_i - step*u, u in [0..max_u] ----
    lambdas: List[float] = []
    for qi in qi_arr:
        for u in range(0, max_u + 1):
            lambdas.append(qi - step * u)
    lambdas.append(float("-inf"))
    lambdas = sorted(set(round(x, 10) for x in lambdas))

    # UI helper (overwrite same line)
    def _ui(msg: str) -> None:
        sys.stdout.write("\r" + msg)
        sys.stdout.flush()

    inv_step = 1.0 / step

    def build_caps_arr(lam: float) -> Optional[List[int]]:
        """caps[id] = floor((qi - lam)/step), or None when lam==-inf."""
        if lam == float("-inf"):
            return None
        caps = [0] * n_ing
        # Use the same tiny epsilon as previous implementation.
        for i, qi in enumerate(qi_arr):
            caps[i] = int(math.floor((qi - lam) * inv_step + 1e-12))
        return caps

    def _merge_add_flat(
        cons_key: Tuple[int, ...],
        items: Tuple[int, ...],
        caps: Optional[List[int]],
    ) -> Optional[Tuple[int, ...]]:
        """Merge two sorted flat tuples (id,count) pairs, summing counts. Return None if exceeds caps."""
        use_caps = caps is not None
        i = 0
        j = 0
        n1 = len(cons_key)
        n2 = len(items)
        out: List[int] = []

        while i < n1 and j < n2:
            id1 = cons_key[i]
            c1 = cons_key[i + 1]
            id2 = items[j]
            c2 = items[j + 1]
            if id1 == id2:
                nv = c1 + c2
                if use_caps and caps[id1] < nv:
                    return None
                out.append(id1)
                out.append(nv)
                i += 2
                j += 2
            elif id1 < id2:
                out.append(id1)
                out.append(c1)
                i += 2
            else:
                if use_caps and caps[id2] < c2:
                    return None
                out.append(id2)
                out.append(c2)
                j += 2

        while i < n1:
            out.append(cons_key[i])
            out.append(cons_key[i + 1])
            i += 2
        while j < n2:
            id2 = items[j]
            c2 = items[j + 1]
            if use_caps and caps[id2] < c2:
                return None
            out.append(id2)
            out.append(c2)
            j += 2

        return tuple(out)

    def filter_cands_by_lam(lam: float, caps: Optional[List[int]]) -> Dict[str, List[Candidate]]:
        """Filter out candidates that individually exceed caps (same behavior as before)."""
        if lam == float("-inf"):
            return {t: options[t] for t in tags_ordered}
        assert caps is not None
        out: Dict[str, List[Candidate]] = {}
        for t in tags_ordered:
            lst: List[Candidate] = []
            for c in options[t]:
                it = _cand_items_flat_cache[id(c)]
                ok = True
                for k in range(0, len(it), 2):
                    if caps[it[k]] < it[k + 1]:
                        ok = False
                        break
                if ok:
                    lst.append(c)
            out[t] = lst
        return out

    def feasible(lam: float) -> bool:
        caps = build_caps_arr(lam)
        opts = filter_cands_by_lam(lam, caps)

        for t in tags_ordered:
            if not opts[t]:
                return False

        # Same tag ordering rule as previous version.
        ord_tags = sorted(tags_ordered, key=lambda t: (len(opts[t]), t))
        m2 = len(ord_tags)

        memo: Dict[Tuple[int, Tuple[int, ...]], bool] = {}

        def rec(idx: int, cons_key: Tuple[int, ...]) -> bool:
            key = (idx, cons_key)
            hit = memo.get(key)
            if hit is not None:
                return hit
            if idx == m2:
                memo[key] = True
                return True

            t = ord_tags[idx]
            for cand in opts[t]:
                items = _cand_items_flat_cache[id(cand)]
                nk = _merge_add_flat(cons_key, items, caps)
                if nk is None:
                    continue
                if rec(idx + 1, nk):
                    memo[key] = True
                    return True

            memo[key] = False
            return False

        return rec(0, ())

    # ---- Binary search for best lambda ----
    lo, hi = 0, len(lambdas) - 1
    best_idx = 0
    # rough upper bound on iterations for UI
    max_iters = max(1, int(math.ceil(math.log2(len(lambdas) + 1))))
    it = 0
    while lo <= hi:
        it += 1
        mid = (lo + hi) // 2
        lam = lambdas[mid]
        ok = feasible(lam)
        _ui(f"      Stage 2: λ-search {it}/{max_iters} | test λ={lam:.6g} | {'OK' if ok else 'NO'}      ")
        if ok:
            best_idx = mid
            lo = mid + 1
        else:
            hi = mid - 1
    sys.stdout.write("\n")

    best_lam = lambdas[best_idx]
    caps_best = build_caps_arr(best_lam)
    opts_best = filter_cands_by_lam(best_lam, caps_best)

    # Same ord_tags and same option sorting as before (tie-break preserved).
    ord_tags = sorted(tags_ordered, key=lambda t: (len(opts_best[t]), t))
    m2 = len(ord_tags)

    def option_sort_key(c: Candidate):
        mins = float("inf")
        for ing, cnt in c.total_counts.items():
            qi = float(tdq_raw.get(ing, 0.0))
            mins = min(mins, qi - step * cnt)
        return (-mins, c.total_ing, -c.dish.sell_price, c.dish.name, c.added_str)

    opts_sorted: Dict[str, List[Candidate]] = {t: sorted(opts_best[t], key=option_sort_key) for t in ord_tags}

    # Precompute items list aligned with opts_sorted order
    cand_items_by_tag: Dict[str, List[Tuple[int, ...]]] = {}
    for t in ord_tags:
        items_list: List[Tuple[int, ...]] = []
        for c in opts_sorted[t]:
            items_list.append(_cand_items_flat_cache[id(c)])
        cand_items_by_tag[t] = items_list

    def vec_from_key(cons_key: Tuple[int, ...]) -> Tuple[float, ...]:
        vec: List[float] = []
        for k in range(0, len(cons_key), 2):
            iid = cons_key[k]
            cnt = cons_key[k + 1]
            if 0 <= cnt <= max_u:
                vec.append(rem_table[iid][cnt])
            else:
                vec.append(qi_arr[iid] - step * cnt)
        vec.sort()
        return tuple(vec)

    last_ui = time.time()

    # Cache only the best vector (choices reconstructed afterwards) to reduce memory footprint.
    @lru_cache(maxsize=None)
    def best_vec_from(idx: int, cons_key: Tuple[int, ...]) -> Optional[Tuple[float, ...]]:
        nonlocal last_ui
        now = time.time()
        if now - last_ui >= 0.5:
            try:
                ci = best_vec_from.cache_info()
                _ui(f"      Stage 2: selecting best combo | states {ci.misses:,} | cache {ci.currsize:,}      ")
            except Exception:
                _ui("      Stage 2: selecting best combo      ")
            last_ui = now

        if idx == m2:
            return vec_from_key(cons_key)

        t = ord_tags[idx]
        items_list = cand_items_by_tag[t]
        best_vec: Optional[Tuple[float, ...]] = None

        for i in range(len(items_list)):
            nk = _merge_add_flat(cons_key, items_list[i], caps_best)
            if nk is None:
                continue
            v_suf = best_vec_from(idx + 1, nk)
            if v_suf is None:
                continue
            if best_vec is None or v_suf > best_vec:
                best_vec = v_suf

        return best_vec

    root_best = best_vec_from(0, tuple())
    sys.stdout.write("\n")
    if root_best is None:
        return None

    # Reconstruct choices with the same deterministic "first best wins" tie-break.
    choice: List[int] = []
    cons: Tuple[int, ...] = tuple()
    for idx in range(m2):
        t = ord_tags[idx]
        items_list = cand_items_by_tag[t]
        target = best_vec_from(idx, cons)
        if target is None:
            return None
        picked = None
        for i in range(len(items_list)):
            nk = _merge_add_flat(cons, items_list[i], caps_best)
            if nk is None:
                continue
            v_suf = best_vec_from(idx + 1, nk)
            if v_suf is None:
                continue
            if v_suf == target:
                picked = i
                cons = nk
                break
        if picked is None:
            return None
        choice.append(picked)

    sel: Dict[str, Candidate] = {}
    for idx, t in enumerate(ord_tags):
        sel[t] = opts_sorted[t][choice[idx]]
    return sel


# -----------------------------
# Per-guest planning
# -----------------------------
def plan_for_guest(
    guest: Guest,
    dishes: List[Dish],
    ingredients: Dict[str, Ingredient],
    tdq_raw: Dict[str, float],
    ing_sig: Dict[str, str],
    sig_members_sorted: Dict[str, List[str]],
    min_score: int,
    orders_per_day: int,
    trend_like_anchors: Set[str],
    trend_hate_anchors: Set[str],
    verbose: bool = False,
    guest_idx: int = 0,
    guest_total: int = 0,
) -> Tuple[Dict[str, Candidate], Dict[str, List[Candidate]]]:
    tags = [t for t in guest.preferred_tags if _s(t)]
    tags = list(dict.fromkeys(tags))
    if not tags:
        return {}, {}

    if verbose:
        prefix = f"[{guest_idx}/{guest_total}] " if guest_total else ""
        print(f"{prefix}{guest.name}: {len(tags)} preferred tags -> Stage 1 (Ecost-min) scanning dishes...")
        t0 = time.time()

        best_cost: Dict[str, int] = {t: 10**9 for t in tags}
    options: Dict[str, List[Candidate]] = {t: [] for t in tags}
    tags_set = set(tags)

    # Stage 1 is defined as: for each preferred tag t, run the per-dish pool,
    # then apply (ingUpgrade/subset) filters within the sub-pool that contains t,
    # and keep only the minimal total_ing candidates.
    dishes_owned = [d for d in dishes if d.owned]
    total_owned = len(dishes_owned)

    for di, dish in enumerate(dishes_owned, 1):
        if verbose and (di % PROGRESS_EVERY == 0 or di == total_owned):
            print(f"    ... scanned {di}/{total_owned} owned dishes")
        pool = build_dish_pool_for_guest(
            guest=guest,
            dish=dish,
            ingredients=ingredients,
            tdq_raw=tdq_raw,
            ing_sig=ing_sig,
            sig_members_sorted=sig_members_sorted,
            min_score=min_score,
            trend_like_anchors=trend_like_anchors,
            trend_hate_anchors=trend_hate_anchors,
        )
        if not pool:
            continue

        # bucket candidates by which preferred tags they hit (single pass; avoid m scans of pool)
        buckets: Dict[str, List[Candidate]] = defaultdict(list)
        for c in pool:
            for tt in c.tagset:
                if tt in tags_set:
                    buckets[tt].append(c)

        for t, sub in buckets.items():
            if not sub:
                continue
            if ING_UPGRADE_FILTER:
                sub = apply_ing_upgrade_filter(sub, score_filter=ING_UPGRADE_SCORE_FILTER)
            if SUBSET_FILTER:
                sub = apply_subset_filter(sub, score_filter=SUBSET_SCORE_FILTER)
            if not sub:
                continue

            min_total = min(c.total_ing for c in sub)
            if min_total < best_cost[t]:
                best_cost[t] = min_total
                options[t] = [c for c in sub if c.total_ing == min_total]
            elif min_total == best_cost[t]:
                options[t].extend([c for c in sub if c.total_ing == min_total])

    # De-dup options per tag by (dish, added_final multiset)
    for t in tags:
        uniq = {}
        for c in options[t]:
            key = (c.dish.name, multiset_key(c.added_names_final))
            if key not in uniq:
                uniq[key] = c
            else:
                cur = uniq[key]
                if (c.score, c.added_str) > (cur.score, cur.added_str):
                    uniq[key] = c
        options[t] = list(uniq.values())

    feasible_tags = [t for t in tags if options.get(t)]
    if verbose:
        counts = [len(options[t]) for t in feasible_tags]
        if counts:
            print(f"    Stage 1 done: feasible {len(feasible_tags)}/{len(tags)} tags, options range {min(counts)}-{max(counts)}, total options {sum(counts)}")
        else:
            print(f"    Stage 1 done: no feasible tags (all empty options)")

    best_sel = solve_max_inf_tdq(feasible_tags, options, tdq_raw, orders_per_day) or {}
    if verbose:
        if best_sel:
            m2 = max(1, len(feasible_tags))
            step2 = orders_per_day / m2
            cons2 = Counter()
            for tt, cc in best_sel.items():
                cons2.update(cc.total_counts)
            inf_tdq = float("inf")
            for ing, cnt in cons2.items():
                qi = tdq_raw.get(ing, 0.0)
                inf_tdq = min(inf_tdq, qi - step2 * cnt)
            inf_tdq = inf_tdq if inf_tdq != float("inf") else float("-inf")
            print(f"    Stage 2 done: selected {len(best_sel)}/{len(feasible_tags)} tags, inf_tdq≈{inf_tdq:.4g}")
        else:
            print("    Stage 2 done: no feasible combination across tags")
        dt = time.time() - t0
        print(f"    Done in {dt:.2f}s")


    final_map: Dict[str, Candidate] = {}
    for t in tags:
        if t in best_sel:
            final_map[t] = best_sel[t]
    return final_map, options


# -----------------------------
# Excel output (merge rules per your spec)
# -----------------------------
HEADERS = [
    "Name",
    "Budget",
    "Preferred Tags",
    "Tag",
    "Dish",
    "Cookware",
    "Sell Price",
    "Base Ingredients",
    "Added Ingredients",
    "Tags",
]

def _text_display_width(s: str) -> int:
    """Rough display width (wide CJK chars count as 2)."""
    if s is None:
        return 0
    s = str(s)
    w = 0
    for ch in s:
        if ch == "\n":
            continue
        ea = unicodedata.east_asian_width(ch)
        w += 2 if ea in ("W", "F") else 1
    return w


def autosize_columns(ws, max_width: int = 55, min_width: int = 10, base_row_height: int = 15, max_row_height: int = 120):
    """Best-effort autosize: set column widths + row heights, and center+wrap all cells."""
    col_widths: Dict[int, int] = {}

    # Column widths (based on longest visual line)
    for col in range(1, ws.max_column + 1):
        letter = get_column_letter(col)
        best = 0
        for row in range(1, ws.max_row + 1):
            v = ws.cell(row=row, column=col).value
            if v is None:
                continue
            s = str(v)
            # respect explicit newlines
            best = max(best, max((_text_display_width(line) for line in s.splitlines()), default=0))
        width = min(max(min_width, best + 2), max_width)
        ws.column_dimensions[letter].width = width
        col_widths[col] = width

    # Center + wrap all cells (merged cells: only top-left matters, but harmless)
    align = Alignment(horizontal="center", vertical="center", wrap_text=True)
    for r in range(1, ws.max_row + 1):
        for c in range(1, ws.max_column + 1):
            ws.cell(row=r, column=c).alignment = align

    # Row heights (estimate wrapped lines by width)
    for r in range(1, ws.max_row + 1):
        needed = 1
        for c in range(1, ws.max_column + 1):
            v = ws.cell(row=r, column=c).value
            if v is None:
                continue
            s = str(v)
            width = max(1, col_widths.get(c, max_width) - 2)
            lines = 0
            for line in (s.splitlines() if s else [""]):
                w = _text_display_width(line)
                lines += max(1, math.ceil(w / width))
            needed = max(needed, lines)
        ws.row_dimensions[r].height = min(max_row_height, base_row_height * needed)

def write_output(
    out_path: Path,
    guests: List[Guest],
    dishes: List[Dish],
    ingredients: Dict[str, Ingredient],
    tdq_raw: Dict[str, float],
    ing_sig: Dict[str, str],
    sig_members_sorted: Dict[str, List[str]],
    min_score: int,
    orders_per_day: int,
    trend_like_anchors: Set[str],
    trend_hate_anchors: Set[str],
    verbose: bool = True,
):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Plans"

    bold = Font(bold=True)
    for j, h in enumerate(HEADERS, 1):
        cell = ws.cell(row=1, column=j, value=h)
        cell.font = bold
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

    ws.freeze_panes = "A2"

    row = 2
    wrap_cols = {3, 8, 9, 10}

    if verbose:
        print(f"\n=== Generating Plans for {len(guests)} guests ===")

    for gi, guest in enumerate(guests, 1):
        selection, _ = plan_for_guest(
            guest=guest,
            dishes=dishes,
            ingredients=ingredients,
            tdq_raw=tdq_raw,
            ing_sig=ing_sig,
            sig_members_sorted=sig_members_sorted,
            min_score=min_score,
            orders_per_day=orders_per_day,
            trend_like_anchors=trend_like_anchors,
            trend_hate_anchors=trend_hate_anchors,
            verbose=verbose,
            guest_idx=gi,
            guest_total=len(guests),
        )

        pref_tags = list(dict.fromkeys([t for t in guest.preferred_tags if _s(t)]))
        pref_tags_multiline = "、".join(pref_tags)

        items = [(t, selection.get(t)) for t in pref_tags]

        by_dish: Dict[str, List[Tuple[str, Candidate]]] = defaultdict(list)
        missing: List[str] = []
        for t, c in items:
            if c is None:
                missing.append(t)
            else:
                by_dish[c.dish.name].append((t, c))

        # Ensure tags covered by the same dish are adjacent: output grouped by dish then by variant(Added).
        dish_order = sorted(by_dish.keys(), key=lambda dn: (dn,))  # stable dish grouping

        start_row_guest = row

        for dn in dish_order:
            pairs = by_dish[dn]
            by_variant: Dict[str, List[Tuple[str, Candidate]]] = defaultdict(list)
            for t, c in pairs:
                vk = multiset_key(c.added_names_final)  # Added-variant key
                by_variant[vk].append((t, c))

            variants_sorted = sorted(by_variant.items(), key=lambda kv: (len(kv[0].split("|")) if kv[0] else 0, kv[0]))

            for vk, tcs in variants_sorted:
                # keep tag order as in Preferred Tags list
                tcs.sort(key=lambda tc: pref_tags.index(tc[0]))
                for t, c in tcs:
                    ws.cell(row=row, column=1, value=guest.name)
                    ws.cell(row=row, column=2, value=guest.budget)
                    ws.cell(row=row, column=3, value=pref_tags_multiline)
                    ws.cell(row=row, column=4, value=t)

                    ws.cell(row=row, column=5, value=c.dish.name)
                    ws.cell(row=row, column=6, value=c.dish.cookware)
                    ws.cell(row=row, column=7, value=c.dish.sell_price)
                    ws.cell(row=row, column=8, value=c.base_str)
                    ws.cell(row=row, column=9, value=c.added_str)
                    ws.cell(row=row, column=10, value=c.tags_str)

                    for col in wrap_cols:
                        ws.cell(row=row, column=col).alignment = Alignment(wrap_text=True, vertical="top")
                    row += 1

        # If any tag has no feasible plan, still output a row to make it visible.
        for t in missing:
            ws.cell(row=row, column=1, value=guest.name)
            ws.cell(row=row, column=2, value=guest.budget)
            ws.cell(row=row, column=3, value=pref_tags_multiline)
            ws.cell(row=row, column=4, value=t)
            for col in range(5, 11):
                ws.cell(row=row, column=col, value="")
            for col in wrap_cols:
                ws.cell(row=row, column=col).alignment = Alignment(wrap_text=True, vertical="top")
            row += 1

        end_row_guest = row - 1

        # Merge guest block (Name/Budget/Preferred Tags)
        if end_row_guest >= start_row_guest:
            for col in range(1, 4):
                ws.merge_cells(start_row=start_row_guest, start_column=col, end_row=end_row_guest, end_column=col)
                ws.cell(row=start_row_guest, column=col).alignment = Alignment(vertical="top", wrap_text=True)

        # Within guest block: merge by Dish (F..J) even if Added differs; then within dish merge by Added (K..L).
        r = start_row_guest
        while r <= end_row_guest:
            dish_name = ws.cell(row=r, column=5).value
            if not dish_name:
                r += 1
                continue
            r2 = r
            while r2 + 1 <= end_row_guest and ws.cell(row=r2 + 1, column=5).value == dish_name:
                r2 += 1

            # Dish-level merge: Dish..Base Ingredients
            for col in range(5, 9):
                ws.merge_cells(start_row=r, start_column=col, end_row=r2, end_column=col)
                ws.cell(row=r, column=col).alignment = Alignment(vertical="top", wrap_text=True)

            # Variant-level merge: Added Ingredients + Tags (by identical Added cell)
            rr = r
            while rr <= r2:
                added = ws.cell(row=rr, column=9).value
                rr2 = rr
                while rr2 + 1 <= r2 and ws.cell(row=rr2 + 1, column=9).value == added:
                    rr2 += 1
                for col in (9, 10):
                    ws.merge_cells(start_row=rr, start_column=col, end_row=rr2, end_column=col)
                    ws.cell(row=rr, column=col).alignment = Alignment(vertical="top", wrap_text=True)
                rr = rr2 + 1

            r = r2 + 1

    autosize_columns(ws)
    wb.save(out_path)
    if verbose:
        print(f"\nExcel saved: {out_path}")


# -----------------------------
# Entrypoint
# -----------------------------
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="", help="Path to 东方夜雀食堂.xlsx (default: ../东方夜雀食堂.xlsx)")
    parser.add_argument("--output", default="", help="Output xlsx path (default: ../稀客料理方案_输出.xlsx)")
    parser.add_argument("--min-score", type=int, default=MIN_SCORE_DEFAULT)
    parser.add_argument("--orders-per-day", type=int, default=ORDERS_PER_DAY_DEFAULT)
    parser.add_argument("--trend-like", default="", help="Comma/、/; separated trend-like anchors (optional)")
    parser.add_argument("--trend-hate", default="", help="Comma/、/; separated trend-hate anchors (optional)")
    args = parser.parse_args()

    script_dir = Path(__file__).resolve().parent
    os.chdir(script_dir)

    in_path = Path(args.input) if args.input else (script_dir.parent / "东方夜雀食堂.xlsx")
    out_path = Path(args.output) if args.output else None

    if not in_path.exists():
        raise FileNotFoundError(f"Input file not found: {in_path}")

    t_all = time.time()
    print("\n=== Izakaya Plan Generator (v5) ===")
    print(f"Working dir: {script_dir}")
    print(f"Input : {in_path}")
    print(f"Output: {out_path if out_path else '(auto, based on trend tags)'}")

    print("\n[1/3] Loading workbook...")
    wb = openpyxl.load_workbook(in_path, data_only=True)

    ingredients = parse_ingredients(wb)
    dishes = parse_dishes(wb)
    guests = parse_guests(wb)
    if not guests:
        print("[WARN] Parsed Guests=0. 请检查Excel中的'稀客'工作表列头是否匹配（例如 Name/名称/稀客/Guest 等）。")
    tdq_raw = parse_tdq_raw(wb)

    dishes_owned = [d for d in dishes if d.owned]
    print(f"[2/3] Parsed sheets: Ingredients={len(ingredients)}, Dishes={len(dishes)} (Owned={len(dishes_owned)}), Guests={len(guests)}, TDQ={len(tdq_raw)}")
    ing_sig, sig_members_sorted = build_ing_sig_maps(ingredients, tdq_raw)

    # ---- Trend tag interactive setup ----
    print("\n=== 流行 Tag 输入 ===")
    print("说明：直接回车表示【没有】；输入多个标签请用【空格】分隔。")

    if args.trend_like:
        s_like = _s(args.trend_like)
        print(f"使用命令行 --trend-like: {s_like}")
    else:
        s_like = input("流行喜爱锚点（回车=没有；空格分隔多个）：").strip()

    if args.trend_hate:
        s_hate = _s(args.trend_hate)
        print(f"使用命令行 --trend-hate: {s_hate}")
    else:
        s_hate = input("流行厌恶锚点（回车=没有；空格分隔多个）：").strip()

    def _parse_anchor_fields(s: str) -> Set[str]:
        s = _s(s)
        if not s:
            return set()
        # allow common separators too, but whitespace is the primary separator
        s = re.sub(r"[,\uFF0C;\uFF1B、|/]+", " ", s)
        return set([x.strip() for x in s.split() if x.strip()])

    trend_like_anchors = _parse_anchor_fields(s_like)
    trend_hate_anchors = _parse_anchor_fields(s_hate)

    # 如果用户没有提供某个方向的锚点，则该“流行·*”标签不会被生成；
    # 同时为了避免稀客偏好里出现“流行·*”导致无解，这里把对应标签从稀客喜好/厌恶中移除。
    if not trend_like_anchors:
        for g in guests:
            g.preferred_tags = [t for t in g.preferred_tags if t != "流行·喜爱"]
            g.disliked_tags = [t for t in g.disliked_tags if t != "流行·喜爱"]
    if not trend_hate_anchors:
        for g in guests:
            g.preferred_tags = [t for t in g.preferred_tags if t != "流行·厌恶"]
            g.disliked_tags = [t for t in g.disliked_tags if t != "流行·厌恶"]

    print(f"流行tag锚点：流行·喜爱={len(trend_like_anchors)}，流行·厌恶={len(trend_hate_anchors)}")

    # ---- Output filename (auto) ----
    if out_path is None:
        def _sanitize_filename_part(s: str) -> str:
            s = _s(s)
            if not s:
                return ""
            # Windows illegal characters: <>:"/\|?*
            s = re.sub(r'[<>:"/\\|?*]+', " ", s)
            s = re.sub(r"\s+", " ", s).strip()
            return s

        parts = []
        if trend_like_anchors:
            like_str = _sanitize_filename_part("、".join(sorted(trend_like_anchors)))
            parts.append(f"流行·喜爱_{like_str}")
        if trend_hate_anchors:
            hate_str = _sanitize_filename_part("、".join(sorted(trend_hate_anchors)))
            parts.append(f"流行·厌恶_{hate_str}")

        fname = "detailed"
        if parts:
            fname = fname + "_" + "_".join(parts)
        out_dir = script_dir.parent / "稀客料理表" / "detailed"
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / f"{fname}.xlsx"

    print(f"Output (final): {out_path}")

    print("\n[3/3] Generating & writing Excel...\n")
    write_output(
        out_path=out_path,
        guests=guests,
        dishes=dishes_owned,
        ingredients=ingredients,
        tdq_raw=tdq_raw,
        ing_sig=ing_sig,
        sig_members_sorted=sig_members_sorted,
        min_score=args.min_score,
        orders_per_day=args.orders_per_day,
        trend_like_anchors=trend_like_anchors,
        trend_hate_anchors=trend_hate_anchors,
    )

    dt_all = time.time() - t_all
    print(f"\nDone. Wrote: {out_path}  (total {dt_all:.2f}s)")

if __name__ == "__main__":
    main()