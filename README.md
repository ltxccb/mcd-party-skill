# 麦当劳聚会团餐助手（mcd-party-skill）

> 麦当劳程序员创意开发大赛参赛项目 · 基于 McDonald's MCP 的 WorkBuddy Skill

## 一句话介绍

给定人数和预算，自动查询附近麦当劳门店、拉取实时菜单、按经济型 / 均衡型 / 丰盛型三档生成聚会点单方案（整单通过 `calculate-price` 核价），并顺带探测该门店的可预订派对场次。

## 安装

```bash
# 1. 配置麦当劳 MCP Token（环境变量，绝不写进代码/仓库）
#    Token 在 https://github.com/M-China/mcd-mcp-server 指引下申请
export MCD_MCP_TOKEN=你的Token   # Windows PowerShell: $env:MCD_MCP_TOKEN="你的Token"

# 2. 本项目为 WorkBuddy Skill，后在 WorkBuddy【自定义连接器】中配置 mcd-mcp：
#    type=streamablehttp, url=https://mcp.mcd.cn, Authorization: Bearer <Token>
```

## 使用示例

```
在 WorkBuddy 对话框输入：
"我们 4 个人预算 120，帮我安排一顿麦当劳聚会，顺便看看能不能订派对"

Skill 执行链路：
query-nearby-stores（选门店）→ query-meals（实时菜单）
→ 组合三档方案 → calculate-price（每档整单核价，禁止用菜单价拼凑）
→ query-party-city / query-party-store / query-partystore-date / query-partystore-session（派对探测）
→ 输出结构化方案 JSON
```

输出示例（节选）：

```json
{
  "store": { "name": "麦当劳上海黄浦华旭国际大厦餐厅", "address": "南京东路街道西藏中路336号" },
  "people": 4, "budget": 120,
  "plans": [
    { "tier": "经济型", "total": 89.0, "per_person": 22.25, "over_budget": false, "items": [...] },
    { "tier": "均衡型", "total": 118.5, "per_person": 29.63, "over_budget": false, "items": [...] },
    { "tier": "丰盛型", "total": 156.0, "per_person": 39.0, "over_budget": true, "items": [...] }
  ],
  "party": { "bookable": false, "note": "该门店暂无派对场次" }
}
```

## 目标用户

- 班级/社团/部门聚餐的组织者：给预算就能拿到现成方案，不用挨个问价
- 家长组团遛娃：顺带查派对房可订场次
- 麦门省钱党的搭子：三档方案按预算对号入座

## 工程约定

- 任何餐品组合变化都必须重新调用 `calculate-price` 整单核价
- 接口失败即停：不猜价格、不自动重试（仅 429 指数退避）
- 所有写操作默认 `dry_run`，显式 `--confirm` 才真实调用
- Token 只走环境变量 `MCD_MCP_TOKEN`

## 文件说明

| 文件 | 说明 |
|------|------|
| `CONTEST_DECLARATION.md` | 官方参赛声明（原样引用，未做任何修改） |
| `MCP_INTEGRATION.md` | 麦当劳 MCP 工具集成说明 |
| `scripts/party_chain.py` | MCP 链路编排（节流/退避/dry_run） |
| `scripts/party_planner.py` | 方案组装 + calculate-price 真实核价 |
| `scripts/demo_data.py` | 演示快照 data.js 生成器 |

