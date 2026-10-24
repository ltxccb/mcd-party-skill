#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""demo_data.py — 演示数据快照（纯标准库）

跑一次 party_planner 的真实链路（真实门店、真实菜单、calculate-price 真实核价），
把结果序列化为 data.js：window.DEMO_DATA = {...契约 JSON...};

快照必须带 generated_at 与说明字段，明确"非实时价格"。

用法：
  export MCD_MCP_TOKEN=xxx
  python demo_data.py --city 上海 --keyword 人民广场 --people 4 --budget 120
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from party_chain import McpError  # noqa: E402
from party_planner import plan  # noqa: E402

DISCLAIMER = "本数据为演示快照，非实时价格；实时价格请以运行时 calculate-price 核价结果为准"


def main() -> int:
    ap = argparse.ArgumentParser(description="生成演示快照 data.js")
    ap.add_argument("--city", default="上海")
    ap.add_argument("--keyword", default="人民广场")
    ap.add_argument("--people", type=int, default=4)
    ap.add_argument("--budget", type=float, default=120)
    ap.add_argument("--taste", default="随便", choices=["随便", "鸡肉", "牛肉"])
    ap.add_argument("--out", default=None, help="data.js 输出路径（默认脚本同目录）")
    args = ap.parse_args()

    try:
        result = plan(args.city, args.keyword, args.people, args.budget, args.taste,
                      confirm=False, out_path=None)
    except McpError as e:
        print(f"[停止] 真实链路失败，不生成伪造快照：{e}", file=sys.stderr)
        return 1

    snapshot = dict(result)
    snapshot["generated_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
    snapshot["note"] = DISCLAIMER

    out = Path(args.out) if args.out else Path(__file__).with_name("data.js")
    out.write_text(
        "// 由 demo_data.py 生成于真实链路运行结果（含 generated_at / note 字段）\n"
        "window.DEMO_DATA = " + json.dumps(snapshot, ensure_ascii=False, indent=2) + ";\n",
        encoding="utf-8",
    )
    print(f"[完成] 演示快照已写入 {out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
