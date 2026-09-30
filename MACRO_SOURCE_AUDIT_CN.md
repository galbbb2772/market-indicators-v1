# Market Structure Lab｜其余四条宏观数据的官方来源核验

状态：**官方入口已识别；精确序列映射、自动抓取、历史覆盖、授权和真实发布时点仍待验证。未接入网站，不能假称数据已齐。** 此清单仅用于私人研究与开发审核。

| 待接入ID | 候选官方来源 | 原始频率/关键问题 | 目前状态 |
| --- | --- | --- | --- |
| `INDPRO` | Federal Reserve G.17 官方历史工业生产文件：https://www.federalreserve.gov/releases/g17/download.htm | 月度；必须选择与 FRED INDPRO 完全一致的**总工业生产、季调、指数基期/修订版**，并验证官方系列代码。历史修订值不是当年公布的原始值。 | 官方入口确认；精确代码及解析待验 |
| `PERMIT` | U.S. Census New Residential Construction 官方历史序列：https://www.census.gov/construction/nrc/data/series.html | 月度；在 *Housing Units Authorized in Permit-Issuing Places* 中核对 FRED PERMIT 对应的**全国、新私人住宅许可、季调年率、千套**单位，不能混用未季调实际月数量。历史 Excel/下载格式变化需单独解析测试。 | 官方入口确认；准确表格/字段待验 |
| `DRTSCILM` | Federal Reserve SLOOS 官方下载：https://www.federalreserve.gov/DataDownload/Choose.aspx?rel=SLOOS | **季度调查**；必须按正式问题、贷款类型、机构规模、净收紧百分比匹配 FRED DRTSCILM 原始定义，不得把任意 SLOOS 大类替代。调查截止、发布时间与对应季度分开存储。 | 官方入口确认；具体序列映射待验 |
| `NFCI` | Federal Reserve Bank of Chicago 官方 NFCI：https://www.chicagofed.org/research/data/nfci/current-data | **周度，截止上周五；通常周三美东8:30发布，特殊假期可能顺延**。不可把上周五观察标记当作上周五已可交易数据；全历史可能重新修订。官方页面提供指数下载，具体 CSV 自动下载地址/字段仍需验。 | 官方入口与发布节奏确认；CSV schema待验 |

## 现有已验证来源

- `T10Y3M` 显示的是**美国财政部10年－3个月每日票面收益率差，取每月最后实际交易日**的替代代理，不能宣称等同 FRED `T10Y3M`，也不是历史实时 vintage。
- `UNRATE` 使用官方 BLS `LNS14000000`。1948-01 至 2026-08 共943个月有真实观测，2025-10 住户调查因政府停摆未采集，官方不存在原值，需显式结构性缺失，禁止插值。

## 可验证的工程门槛

1. **定义先于下载：** 记录 `source_url`、官方系列码、季调口径、单位、原始频率、年份起止和官方发布日期；用官方文档与 FRED 元数据逐项核对后再写入解析器。
2. **原频率入库：** 月度保持月度、SLOOS 保持季度、NFCI 保持周度；可另生成明确标注的显示汇总，但不得前填后伪装为真实观测。
3. **价格/宏观因果对齐：** 回测只在该期**实际发布之后**使用；若只有事后修订历史而无历史 vintage，研究结果统一标为描述性研究，不能声称真实可交易的历史预测力。
4. **故障与许可：** 官方接口变更、429、过时缓存、缺月均须显式状态；不能合成真实值；网站历史原始数据展示权单独审查，发布还需所有者明确授权。
5. **端到端验证：** 每条新源独立真实环境下载、完整性/错误输入单测、市场V2回归测试通过，再从 `unverified_direct_source` 转为 `verified_direct_source`。本文件的收录不表示已完成接入。
