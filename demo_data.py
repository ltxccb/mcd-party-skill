#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""demo_data.py — 生成演示数据 data.js

输出 data.js 内容为 `window.PARTY_DATA = {...}`，结构与 CONTRACT.md
的数据 JSON Schema 完全一致，供 Skill 前端演示页直接 <script> 引入。

⚠️ 本文件中的数字是【演示样例】，真实运行时价格必须来自
calculate-price 核价结果（见 party_planner.py）。
"""

from __future__ import annotations

import json
from pathlib import Path

DEMO = {
    "store": {"name": "麦当劳上海黄浦华旭国际大厦餐厅", "address": "南京东路街道西藏中路336号"},
    "people": 4,
    "budget": 120,
    "plans": [
        {
            "tier": "经济型",
            "total": 89.0,
            "per_person": 22.25,
            "over_budget": False,
            "items": [
                {"name": "麦乐鸡套餐", "qty": 2, "price": 25.0},
                {"name": "麦乐鸡", "qty": 2, "price": 14.0},
                {"name": "可乐", "qty": 4, "price": 9.5},
            ],
        },
        {
            "tier": "均衡型",
            "total": 118.5,
            "per_person": 29.63,
            "over_budget": False,
            "items": [
                {"name": "板烧鸡腿堡三件套", "qty": 2, "price": 34.5},
                {"name": "BFF四宫格小食盘", "qty": 1, "price": 39.8},
                {"name": "可乐", "qty": 4, "price": 9.5},
            ],
        },
        {
            "tier": "丰盛型",
            "total": 156.0,
            "per_person": 39.0,
            "over_budget": True,
            "items": [
                {"name": "板烧鸡腿堡三件套", "qty": 2, "price": 34.5},
                {"name": "巨无霸三件套", "qty": 1, "price": 36.5},
                {"name": "薄皮V翅双拼十翅", "qty": 1, "price": 49.9},
                {"name": "薯条", "qty": 2, "price": 13.5},
                {"name": "可乐", "qty": 4, "price": 9.5},
            ],
        },
    ],
    "party": {"bookable": False, "note": "该门店暂无派对场次"},
}


def main() -> None:
    out = Path(__file__).with_name("data.js")
    out.write_text(
        "// 由 demo_data.py 生成（演示数据，价格为样例）\n"
        "window.PARTY_DATA = " + json.dumps(DEMO, ensure_ascii=False, indent=2) + ";\n",
        encoding="utf-8",
    )
    print(f"[完成] 演示数据已写入 {out}")


if __name__ == "__main__":
    main()
