# Market Regime Lab V1

这是一个**独立于交易系统**的 28 指标市场环境面板。

## 核心
- 28 个市场指标
- Level：当前指标位置/状态
- 一级导 D1：指标变化动能
- 二级导 D2：变化动能的变化速率
- 每天自动刷新
- 与原交易系统完全分离

## 结构
- `docs/index.html`：网站
- `docs/data/current.json`：网站数据
- `update_data.py`：每日抓取与计算
- `indicator_config.json`：28 个指标定义
- `manual_inputs.json`：低频/暂时人工输入
- `.github/workflows/daily_update.yml`：自动刷新 + GitHub Pages 部署

## 日更
工作流每天 22:30 America/New_York 自动运行。周频、月频、季度数据会每天检查，但只有原始数据源发布新值时才变化。

## 数据源
- FRED CSV：宏观、利率、信用、VIX、黄金、WTI 等
- Stooq：SPY / RSP / IWM / HYG / LQD 日线与成交量

部分第一版指标使用公开代理变量，会在网站中标记为 proxy。
