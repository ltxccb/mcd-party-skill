#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""party_planner.py — 麦当劳聚会团餐助手核心脚本

遵循 CONTRACT.md 接口契约：
- 三档方案（经济型/均衡型/丰盛型），总价一律以 calculate-price 核价缓存为准，
  绝不用菜单显示价加减拼凑（见 verify_totals：无核价缓存即报错退出）。
- 接口失败即停：不猜价格、不自动重试（429 指数退避由 MCP 连接器层处理）。
- 本脚本不直接发起任何写操作，无 --confirm 入口，天然满足 dry_run 默认。

数据流（WorkBuddy Skill 运行时）：
  1. Agent 调 query-nearby-stores / query-meals，将原始返回存为 menu_snapshot.json
  2. Agent 按脚本给出的候选组合调用 calculate-price，把 {组合签名: 整单总价}
     存入 price_cache.json
  3. 运行本脚本生成最终方案 JSON（CONTRACT Schema）
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

TIERS = ("经济型", "均衡型", "丰盛型")


def load_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        sys.exit(f"[停止] 文件不存在：{path}")
    except json.JSONDecodeError as e:
        sys.exit(f"[停止] JSON 解析失败：{path}: {e}")


def combo_signature(items: list[dict]) -> str:
    """组合签名：排序后的 code:qty 列表哈希，用于与 price_cache 对账。"""
    norm = sorted((str(i["code"]), int(i["qty"])) for i in items)
    return hashlib.sha1(json.dumps(norm, ensure_ascii=False).encode()).hexdigest()


def pick_candidates(menu: dict) -> dict[str, list[dict]]:
    """从菜单快照中挑选三档候选组合。

    选择原则：
    - 避开 discountType='随单购麦金卡优惠' 的商品（价格有歧义，见 docs/mcp_probe）
    - 套餐/单品以 tags 区分；价格字段 currentPrice 为字符串，float 转换
    """
    meals = menu["data"]["meals"]
    categories = menu["data"]["categories"]

    # 分类名可能带换行，strip 后归类
    def cat_items(keyword: str) -> list[dict]:
        out = []
        for cat in categories:
            if keyword in cat["name"]:
                for m in cat["meals"]:
                    detail = meals.get(m["code"])
                    if detail and detail.get("discountType") is None:
                        out.append({**detail, "code": m["code"], "tags": m.get("tags", [])})
        return out

    singles = cat_items("小食甜品") + cat_items("饮品")
    combos = cat_items("精选单人餐") + cat_items("鸡肉汉堡") + cat_items("巨无霸")
    sharing = cat_items("小食拼盘")  # 多人餐/拼盘，适合丰盛型

    budget_tier = sorted(
        (i for i in singles if i.get("tags") and "小食" in i["tags"]),
        key=lambda x: float(x["currentPrice"]),
    )
    drinks = sorted(
        (i for i in singles if i.get("tags") and ("冷饮" in i["tags"] or "热饮" in i["tags"])),
        key=lambda x: float(x["currentPrice"]),
    )
    main_dishes = sorted(combos, key=lambda x: float(x["currentPrice"]))
    platters = sorted(sharing, key=lambda x: float(x["currentPrice"]))

    return {
        "budget": (main_dishes, budget_tier, drinks),  # 经济型素材
        "balance": (main_dishes, platters, drinks),    # 均衡型素材
        "feast": (main_dishes, platters, drinks),      # 丰盛型素材
    }


def build_combo(tier: str, people: int, cand: dict) -> list[dict]:
    """按档位确定性生成 {code, name, qty} 组合。数量随人数线性放大。"""
    mains, sides, drinks = cand["budget"] if tier == "经济型" else cand["balance"] if tier == "均衡型" else cand["feast"]
    items: list[dict] = []
    if mains:
        items.append({"code": mains[0]["code"], "name": mains[0]["name"], "qty": people})
    if sides:
        items.append({"code": sides[0]["code"], "name": sides[0]["name"], "qty": people})
    if drinks and tier != "经济型":
        items.append({"code": drinks[0]["code"], "name": drinks[0]["name"], "qty": people})
    if tier == "丰盛型" and len(mains) > 1:
        items.append({"code": mains[1]["code"], "name": mains[1]["name"], "qty": people})
    if tier == "丰盛型" and len(sides) > 1:
        items.append({"code": sides[1]["code"], "name": sides[1]["name"], "qty": people})
    return items


def verify_totals(combo: list[dict], price_cache: dict) -> float:
    """整单核价对账：组合必须在 price_cache 中有 calculate-price 结果，否则停止。"""
    sig = combo_signature(combo)
    if sig not in price_cache:
        sys.exit(
            "[停止] 该组合未经 calculate-price 核价，按契约拒绝输出。\n"
            f"组合签名：{sig}\n"
            f"组合明细：{json.dumps(combo, ensure_ascii=False)}\n"
            "请让 Agent 先对以上组合调用 calculate-price，并把结果写入 price_cache.json。"
        )
    return round(float(price_cache[sig]), 2)


def main() -> None:
    ap = argparse.ArgumentParser(description="麦当劳聚会团餐三档方案生成器")
    ap.add_argument("--menu", required=True, help="菜单+门店快照 JSON（query-meals 原始返回，含 store 字段）")
    ap.add_argument("--price-cache", required=True, help="calculate-price 核价缓存 JSON：{组合签名: 整单总价}")
    ap.add_argument("--people", type=int, required=True)
    ap.add_argument("--budget", type=float, required=True)
    ap.add_argument("--party-note", default="该门店暂无派对场次", help="派对探测结论文案（Agent 由 query-party-* 工具得出）")
    ap.add_argument("--party-bookable", action="store_true", help="派对是否可订（由 query-party-* 工具得出）")
    ap.add_argument("--out", default="plan.json", help="输出文件路径")
    args = ap.parse_args()

    if args.people <= 0:
        sys.exit("[停止] people 必须为正整数")
    if args.budget <= 0:
        sys.exit("[停止] budget 必须为正数")

    menu = load_json(Path(args.menu))
    price_cache = load_json(Path(args.price_cache))
    candidates = pick_candidates(menu)

    plans = []
    for tier in TIERS:
        combo = build_combo(tier, args.people, candidates)
        if not combo:
            sys.exit(f"[停止] {tier}:菜单快照中无可用候选，拒绝猜测。")
        total = verify_totals(combo, price_cache)
        plans.append({
            "tier": tier,
            "total": total,
            "per_person": round(total / args.people, 2),
            "over_budget": total > args.budget,
            "items": [{"name": it["name"], "qty": it["qty"]} for it in combo],
        })

    result = {
        "store": menu.get("store", {"name": "", "address": ""}),
        "people": args.people,
        "budget": args.budget,
        "plans": plans,
        "party": {"bookable": args.party_bookable, "note": args.party_note},
    }

    Path(args.out).write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"[完成] 方案已写入 {args.out}（组合均已经 calculate-price 核价）")


if __name__ == "__main__":
    main()
