# MCP_INTEGRATION — 麦当劳 MCP 集成说明

本项目（聚会团餐助手 mcd-party-skill）基于 McDonald's China MCP 构建，全部工具调用已在真实链路中验证通过（2026-10-24，上海实测）。

## 一、使用的 MCP Server

| 项 | 值 |
|----|----|
| Server | McDonald's China MCP（`mcd-mcp`） |
| 传输方式 | Streamable HTTP（JSON-RPC 2.0） |
| 接入地址 | `https://mcp.mcd.cn`（见 `mcp-config.example.json`） |
| 鉴权 | `Authorization: Bearer ${MCD_MCP_TOKEN}`，Token 仅存于环境变量，不入仓库、不写死 |
| 客户端实现 | `scripts/party_chain.py`（纯 Python 标准库 urllib，无第三方依赖） |

## 二、实际使用的 Tool 及作用

| # | Tool | 作用 | 调用时机 |
|---|------|------|----------|
| 1 | `query-nearby-stores` | 按城市+关键词查询可点餐门店，返回 storeName/address/storeCode 等 | 用户给出聚会城市后第一步 |
| 2 | `query-meals` | 拉取指定门店实时菜单：`categories[]`（分类+code）+ `data.meals[code]` 详情（name/currentPrice/originalPrice/discountType） | 选定门店后 |
| 3 | `calculate-price` | **整单真实核价**（含优惠），输入商品 `productCode`+`quantity` 列表，返回 `data.price`（单位：分） | 每生成一个候选组合就调用一次 |
| 4 | `query-party-city` | 查询支持派对业务的城市 | 派对探测链路第一级 |
| 5 | `query-party-store` | 查询该城市支持派对的门店 | 第二级 |
| 6 | `query-party-store-date` | 查询门店可预约日期（需 spuId） | 第三级 |
| 7 | `query-party-store-session` | 查询某日期的场次列表（需 spuId + dateStr） | 第四级 |

## 三、完整调用流程（输入 → 输出）

```
用户输入：{城市, 关键词, 人数, 预算, 口味偏好}
        │
        ▼
[1] query-nearby-stores(searchType=2, city, keyword, beType=1)
        │ 取第一个门店 storeCode
        ▼
[2] query-meals(storeCode, orderType=1, beType=1)
        │ 菜单整理成素材池（mains/sides/drinks/platters）
        │ 过滤规则：discountType 非空（促销/随单购麦金卡）商品剔除；
        │           sides 严格按 tags["小食"] 判定，防止周边玩具混入
        ▼
[3] 按 经济型/均衡型/丰盛型 三档组装候选组合（qty 随人数线性放大）
        │
        ▼
[4] 每档组合独立调用 calculate-price(storeCode, orderType=1, beType=1,
        │   items=[{productCode, quantity}, ...])
        │ total = data.price / 100（分→元）
        │ 核价失败 → 该档位写入 skipped_tiers 透明披露，绝不拿菜单价凑数
        ▼
[5] 派对探测（可选，逐级失败即降级）：
    query-party-city → query-party-store → query-party-store-date
    → query-party-store-session
    │ 任一级无数据 → party.bookable=false，不影响点单方案输出
        ▼
输出：契约 Schema JSON
{ "store": {...}, "people": N, "budget": M,
  "plans": [{ "tier": "经济型|均衡型|丰盛型", "total", "per_person",
              "over_budget", "items": [{name, qty}] }],
  "party": { "bookable", "note" } }
```

### 工程铁律（与 CONTRACT.md 一致）

1. **核价强制**：任何餐品组合变化都必须重新调 `calculate-price` 整单核价，`total` 唯一来源是核价返回，禁止菜单显示价加减
2. **失败即停**：接口失败立即终止本轮，保留已成功核价的结果；不猜价格、不自动重试（仅 HTTP 429 按 1s→2s→4s 指数退避，最多 3 次）
3. **写操作默认 dry_run**：写类工具（create-order / party-order-create 等）默认不真实调用，仅显式 `--confirm` 才执行
4. **Token 安全**：只走环境变量 `MCD_MCP_TOKEN`
5. **节流**：滑动窗口限 300 次/分钟（官方上限 600，留一半余量）

## 四、业务价值：解决多人聚餐的什么问题

1. **"众口难调 + 算钱烦" → 一句话出方案**：组织者只需给出人数和预算，三档方案（保底 / 标准 / 吃好）连同人均价自动生成，超没超预算一目了然，不用挨个问、拿计算器拼
2. **价格可信，不会"到了店里发现价格不对"**：所有总价来自 calculate-price 官方核价接口（含优惠），与真实下单口径一致，避免用菜单显示价拼凑导致的差额尴尬
3. **点单 + 订派对房一次搞定**：聚餐经常伴随生日会/亲子局，派对四级链路顺带探测该门店可订日期与场次，省去单独查的步骤
4. **失败可预期，不会给你编数据**：接口失败就停、未核价的档位明确标注跳过——宁可少给一档，也不给一个编造的价格

## 五、实测记录

- 环境：WorkBuddy + mcd-mcp 连接器，2026-10-24
- 用例：上海 / 人民广场 / 4 人 / 预算 ¥120 / 无口味偏好
- 结果：三档全部真实核价通过 —— 经济型 ¥119.6（人均 ¥29.9，预算内）、均衡型 ¥185.6、丰盛型 ¥383.5
- 已知限制：`query-party-store-date/session` 依赖 `spuId`（需先经 mall-points-products 获取），当前版本派对探测降级输出，点单主链路不受影响
