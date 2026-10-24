# MCP_INTEGRATION — 麦当劳 MCP 集成说明

## 使用的 MCP Server

| 项 | 值 |
|----|----|
| Server | McDonald's China MCP（`mcd-mcp`） |
| 接入方式 | WorkBuddy 自定义连接器，`type: streamablehttp`，`url: https://mcp.mcd.cn` |
| 鉴权 | `Authorization: Bearer <MCD_MCP_TOKEN>`，Token 仅存于环境变量/连接器配置，不入仓库 |

## 使用的 Tool 及调用流程

### 主链路（每轮固定顺序）

| 顺序 | Tool | 用途 | 关键入参 | 本项目使用方式 |
|------|------|------|----------|----------------|
| 1 | `query-nearby-stores` | 查询附近可点餐门店 | `searchType=2, city, keyword, beType=1` | 取 `storeCode`（beType=1 无 beCode，后续不传） |
| 2 | `query-meals` | 拉取该店实时菜单 | `storeCode, orderType=1, beType=1` | `categories[]` 提供分类与 code，`data.meals[code]` 提供详情；价格字段为字符串需 float 转换 |
| 3 | `calculate-price` | **整单核价** | 门店 + 餐品 code/数量明细 | 三档方案中任何组合变化都必须重新调用；`total` 一律以本工具返回为准，禁止用菜单显示价加减 |
| 4 | `query-party-city` | 查询可订派对的城市 | — | 确认目标城市是否有派对业务 |
| 5 | `query-party-store` | 查询该城市可订派对的门店 | 城市 | 确认目标门店是否支持 |
| 6 | `query-partystore-date` | 查询可订日期 | 门店 | 生成可选日期 |
| 7 | `query-partystore-session` | 查询某日场次 | 门店 + 日期 | 生成可选场次；无场次时输出 `"该门店暂无派对场次"` |

### 业务价值

- **价格可信**：所有档位总价来自官方核价接口，展示给用户的价格与真实下单一致
- **派对闭环**：点单方案与派对场次探测一体完成，覆盖"聚餐+订派对房"完整场景
- **降级友好**：派对链路任一环节无数据时，主点单方案照常输出

## 失败处理约定

- 任一接口失败：立即终止本轮，不猜测、不自动重试
- 唯一例外：HTTP 429 按 1s → 2s → 4s 指数退避后重试，最多 3 次
- 所有写操作（下单/订场次）默认 `dry_run=True`，仅显式 `--confirm` 才真实调用
