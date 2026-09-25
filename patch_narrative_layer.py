from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA_PATH = ROOT / "docs" / "data" / "current.json"
HTML_PATH = ROOT / "docs" / "index.html"

# sense = +1 means a HIGH indicator score supports this narrative.
# sense = -1 means a LOW indicator score supports this narrative.
# The layer is explanatory only; it never feeds back into Market Model V2.
NARRATIVES = [
    {
        "id": "bear_ai_crowding",
        "side": "bear",
        "title": "AI / 大型科技拥挤与估值风险",
        "description": "观察 AI / 大型科技波动、集中度、估值和流动性风险是否共同升温。这里衡量的是市场风险映射，不等同于判断 AI 产业本身是否存在泡沫。",
        "evidence": [
            ("ai7_volatility", +1, 1.15),
            ("mag7_volatility", +1, 1.00),
            ("mega_liquidity_blowup", +1, 1.20),
            ("concentration", +1, 1.15),
            ("valuation_percentile", +1, 1.00),
            ("market_overextension", +1, 0.80),
        ],
    },
    {
        "id": "bear_rates",
        "side": "bear",
        "title": "高利率 / 再定价压力",
        "description": "观察长端利率、紧缩周期、收益率曲线与股市利率敏感度是否共同构成估值和融资压力。",
        "evidence": [
            ("treasury_rate_regime", +1, 1.20),
            ("global_cb_cycle_entry", +1, 1.00),
            ("yield_curve", +1, 1.00),
            ("rate_cycle_sensitivity", +1, 0.90),
        ],
    },
    {
        "id": "bear_credit_liquidity",
        "side": "bear",
        "title": "信用 / 流动性收缩",
        "description": "观察信用利差、系统性风险、杠杆与市场流动性是否出现一致恶化。",
        "evidence": [
            ("liquidity_risk", +1, 1.25),
            ("high_yield", +1, 1.10),
            ("leverage_liquidity", +1, 1.10),
            ("systemic_risk", +1, 1.25),
            ("market_liquidity", -1, 1.00),
        ],
    },
    {
        "id": "bear_breadth",
        "side": "bear",
        "title": "市场宽度不足 / 集中度脆弱",
        "description": "观察上涨是否过度依赖少数大盘股，以及市场支撑、散户参与和中小盘生存状态是否不足。",
        "evidence": [
            ("concentration", +1, 1.20),
            ("breadth_concentration", +1, 1.15),
            ("market_support", -1, 1.15),
            ("retail_participation", -1, 0.80),
            ("sme_survival_growth", -1, 0.90),
        ],
    },
    {
        "id": "bear_geo",
        "side": "bear",
        "title": "地缘政治 / 事件冲击",
        "description": "观察地缘风险代理、跨资产事件冲击和恐慌是否在市场价格里留下持续痕迹。V1 不使用新闻文本分类。",
        "evidence": [
            ("geopolitical_risk", +1, 1.25),
            ("geo_news_impact", +1, 1.10),
            ("geo_lag_reaction", +1, 0.90),
            ("market_fear", +1, 1.00),
        ],
    },
    {
        "id": "bull_breadth",
        "side": "bull",
        "title": "市场支撑 / 宽度改善",
        "description": "观察市场支撑、赚钱效应、参与度和中小盘相对状态是否说明上涨基础在扩散。",
        "evidence": [
            ("market_support", +1, 1.25),
            ("money_making_effect", +1, 1.10),
            ("retail_participation", +1, 0.85),
            ("sme_survival_growth", +1, 0.95),
            ("concentration", -1, 1.10),
        ],
    },
    {
        "id": "bull_liquidity",
        "side": "bull",
        "title": "信用稳定 / 流动性健康",
        "description": "观察市场流动性是否充足，同时信用、系统性和杠杆风险是否保持低位。",
        "evidence": [
            ("market_liquidity", +1, 1.15),
            ("liquidity_risk", -1, 1.25),
            ("high_yield", -1, 1.10),
            ("systemic_risk", -1, 1.25),
            ("leverage_liquidity", -1, 1.00),
        ],
    },
    {
        "id": "bull_risk_appetite",
        "side": "bull",
        "title": "风险偏好 / 乐观情绪",
        "description": "观察乐观、市场偏向和恐慌类指标是否共同指向更健康的风险承受环境。",
        "evidence": [
            ("market_optimism", +1, 1.20),
            ("market_bias", +1, 1.10),
            ("market_pessimism", -1, 1.10),
            ("market_fear", -1, 1.15),
            ("largecap_panic", -1, 0.90),
        ],
    },
    {
        "id": "bull_easing",
        "side": "bull",
        "title": "利率 / 金融条件缓和",
        "description": "观察央行节奏、国债利率与收益率曲线压力是否在缓解，从而降低估值和融资约束。",
        "evidence": [
            ("global_cb_rhythm", +1, 1.15),
            ("treasury_rate_regime", -1, 1.20),
            ("global_cb_cycle_entry", -1, 1.00),
            ("yield_curve", -1, 0.95),
            ("rate_cycle_sensitivity", -1, 0.80),
        ],
    },
    {
        "id": "bull_ai_contained",
        "side": "bull",
        "title": "AI / 大型科技风险暂未扩散",
        "description": "不是“AI 盈利兑现”判断；这里只观察 AI / 大型科技波动、集中度和流动性风险是否仍受控。",
        "evidence": [
            ("ai7_volatility", -1, 1.15),
            ("mag7_volatility", -1, 1.00),
            ("mega_liquidity_blowup", -1, 1.20),
            ("tech100_volatility", -1, 0.95),
            ("concentration", -1, 1.00),
        ],
    },
]


def strength_label(v: float) -> str:
    if v >= 70:
        return "强"
    if v >= 58:
        return "中等偏强"
    if v >= 45:
        return "混合"
    return "弱"


def trend_label(v: float) -> str:
    if v >= 1.5:
        return "强化"
    if v <= -1.5:
        return "削弱"
    return "稳定"


def build_narrative_layer(data: dict) -> dict:
    items = {x.get("id"): x for x in data.get("indicators", [])}
    built = []
    for cfg in NARRATIVES:
        rows = []
        total_weight = sum(float(w) for _, _, w in cfg["evidence"])
        used_weight = 0.0
        weighted_strength = 0.0
        weighted_d1 = 0.0
        aligned_weight = 0.0
        for indicator_id, sense, weight in cfg["evidence"]:
            item = items.get(indicator_id)
            if not item or item.get("score") is None:
                continue
            score = float(item["score"])
            d1 = float(item.get("d1") or 0.0)
            oriented = score if sense > 0 else 100.0 - score
            oriented_d1 = d1 if sense > 0 else -d1
            weight = float(weight)
            used_weight += weight
            weighted_strength += weight * oriented
            weighted_d1 += weight * oriented_d1
            if oriented >= 60:
                aligned_weight += weight
            rows.append({
                "id": indicator_id,
                "name": item.get("name", indicator_id),
                "score": round(score, 2),
                "oriented_score": round(oriented, 2),
                "d1_oriented": round(oriented_d1, 2),
                "quality": item.get("quality"),
                "asof": item.get("asof"),
                "weight": weight,
            })

        if used_weight <= 0:
            strength = None
            trend = None
            consistency = None
        else:
            strength = weighted_strength / used_weight
            trend = weighted_d1 / used_weight
            consistency = 100.0 * aligned_weight / used_weight

        support = sorted(rows, key=lambda r: r["oriented_score"], reverse=True)[:3]
        counter = sorted(rows, key=lambda r: r["oriented_score"])[:2]
        built.append({
            "id": cfg["id"],
            "side": cfg["side"],
            "title": cfg["title"],
            "description": cfg["description"],
            "strength": round(strength, 2) if strength is not None else None,
            "strength_label": strength_label(strength) if strength is not None else "数据不足",
            "trend_score": round(trend, 2) if trend is not None else None,
            "trend": trend_label(trend) if trend is not None else "数据不足",
            "evidence_consistency_pct": round(consistency, 1) if consistency is not None else None,
            "coverage_pct": round(100.0 * used_weight / total_weight, 1) if total_weight else 0.0,
            "supporting_evidence": support,
            "counter_evidence": counter,
            "available_evidence": len(rows),
            "configured_evidence": len(cfg["evidence"]),
        })

    bull = sorted([x for x in built if x["side"] == "bull"], key=lambda x: x["strength"] if x["strength"] is not None else -1, reverse=True)
    bear = sorted([x for x in built if x["side"] == "bear"], key=lambda x: x["strength"] if x["strength"] is not None else -1, reverse=True)

    def side_strength(rows: list[dict]) -> float | None:
        valid = [x for x in rows if x["strength"] is not None and x["coverage_pct"] >= 40]
        if not valid:
            return None
        weights = [max(0.4, x["coverage_pct"] / 100.0) for x in valid]
        return sum(x["strength"] * w for x, w in zip(valid, weights)) / sum(weights)

    bull_strength = side_strength(bull)
    bear_strength = side_strength(bear)
    net = (bull_strength - bear_strength) if bull_strength is not None and bear_strength is not None else None
    if net is None:
        balance_label = "数据不足"
    elif net >= 10:
        balance_label = "多头叙事占优"
    elif net <= -10:
        balance_label = "空头叙事占优"
    else:
        balance_label = "多空叙事接近平衡"

    return {
        "version": "NARRATIVE-LAYER-V1",
        "scope": "quantitative_proxy_only",
        "feeds_market_model": False,
        "news_nlp_connected": False,
        "summary": {
            "bull_strength": round(bull_strength, 2) if bull_strength is not None else None,
            "bear_strength": round(bear_strength, 2) if bear_strength is not None else None,
            "net_balance": round(net, 2) if net is not None else None,
            "balance_label": balance_label,
        },
        "bull": bull,
        "bear": bear,
        "methodology": {
            "strength": "Fixed weighted average of already-connected indicator scores after narrative-specific direction mapping.",
            "trend": "Weighted D1 after the same direction mapping; positive means the narrative is strengthening.",
            "consistency": "Share of available evidence weight with narrative-oriented score >= 60.",
            "counterevidence": "The weakest narrative-oriented evidence is shown explicitly to reduce confirmation bias.",
            "warning": "Narrative Layer is explanatory context only. It does not change Market Model V2, predict future returns, or constitute a trade signal. V1 has no live-news NLP.",
        },
    }


NARRATIVE_CSS = r'''
/* NARRATIVE_LAYER_V1 */
.narrHero{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin:12px 0}.narrHero .sum{min-height:104px}.narrHero .sum b{font-size:30px}.narrColumns{display:grid;grid-template-columns:1fr 1fr;gap:12px}.narrGrid{display:grid;gap:10px}.narrCard{background:linear-gradient(180deg,rgba(19,36,61,.97),rgba(12,24,42,.97));border:1px solid var(--line);border-radius:15px;padding:14px}.narrCard.bull{border-color:#295b4d}.narrCard.bear{border-color:#663743}.narrHead{display:flex;justify-content:space-between;gap:12px;align-items:flex-start}.narrTitle{font-weight:800;font-size:15px}.narrStrength{font-size:27px;font-weight:900}.narrBar{height:7px;background:#172a45;border-radius:99px;overflow:hidden;margin:9px 0}.narrBar>i{display:block;height:100%;background:linear-gradient(90deg,#355d93,#79a9ff)}.narrCard.bull .narrBar>i{background:linear-gradient(90deg,#27775f,#61dfb2)}.narrCard.bear .narrBar>i{background:linear-gradient(90deg,#823c4b,#ff738b)}.narrMeta{display:flex;gap:8px;flex-wrap:wrap;margin:8px 0}.narrEvidence{margin-top:10px;border-top:1px solid #1c304d;padding-top:8px}.narrEvidenceRow{display:flex;justify-content:space-between;gap:12px;padding:5px 0;font-size:11px}.narrEvidenceRow span:first-child{color:#aebed8}.narrCounter{color:#ffc95c}.narrDesc{color:#91a8ca;font-size:12px;line-height:1.55;margin-top:7px}.narrMethod{margin-top:12px}.narrBalancePos{color:var(--g)}.narrBalanceNeg{color:var(--r)}
@media(max-width:900px){.narrColumns{grid-template-columns:1fr}.narrHero{grid-template-columns:1fr 1fr}}
@media(max-width:650px){.narrHero{grid-template-columns:1fr}}
'''

NARRATIVE_SECTION = r'''
<section id="narrativeView" class="hidden">
  <div class="hero">
    <div class="cat">Narrative Layer V1 · 市场叙事层</div>
    <div class="sub">把现有硬指标组织成“市场现在有哪些可被数据支持的多头 / 空头故事”。这一层只负责解释，不修改 Market Model V2，也不直接生成交易信号。</div>
  </div>
  <div class="narrHero">
    <div class="sum"><small>🟢 Bull Narrative Strength</small><b id="bullNarrScore">—</b><div class="tiny">多头叙事综合强度 / 0–100</div></div>
    <div class="sum"><small>🔴 Bear Narrative Strength</small><b id="bearNarrScore">—</b><div class="tiny">空头叙事综合强度 / 0–100</div></div>
    <div class="sum"><small>⚖️ Narrative Balance</small><b id="narrBalance">—</b><div class="tiny" id="narrBalanceLabel">—</div></div>
  </div>
  <div class="narrColumns">
    <div class="panel"><h3>🟢 乐观故事 / Bull Case</h3><div class="narrGrid" id="bullNarratives"><div class="empty">等待叙事数据…</div></div></div>
    <div class="panel"><h3>🔴 鬼故事 / Bear Case</h3><div class="narrGrid" id="bearNarratives"><div class="empty">等待叙事数据…</div></div></div>
  </div>
  <div class="note narrMethod" id="narrMethod">V1 仅使用已经接入的量化 / 宏观代理数据，不使用新闻文本 NLP。某个故事强，不代表未来一定按该故事发展；反证会同时显示。</div>
</section>
'''

NARRATIVE_JS = r'''
function renderNarratives(){
  const n=DATA.narrative_layer||{},s=n.summary||{};
  const bull=document.querySelector('#bullNarrScore'),bear=document.querySelector('#bearNarrScore'),bal=document.querySelector('#narrBalance'),lab=document.querySelector('#narrBalanceLabel');
  if(!bull||!bear||!bal||!lab)return;
  bull.textContent=fmt(s.bull_strength);bear.textContent=fmt(s.bear_strength);bal.textContent=(s.net_balance==null?'—':(s.net_balance>0?'+':'')+fmt(s.net_balance));lab.textContent=s.balance_label||'—';
  bal.className=s.net_balance>0?'narrBalancePos':s.net_balance<0?'narrBalanceNeg':'';
  const evidenceRows=(arr,counter=false)=>(arr||[]).map(e=>'<div class="narrEvidenceRow '+(counter?'narrCounter':'')+'"><span>'+e.name+'</span><b>'+fmt(e.oriented_score)+' · D1 '+(e.d1_oriented>0?'+':'')+fmt(e.d1_oriented)+'</b></div>').join('');
  const paint=(id,rows,side)=>{const root=document.querySelector(id);root.innerHTML='';(rows||[]).forEach(x=>{const d=document.createElement('article');d.className='narrCard '+side;const trend=x.trend==='强化'?'↑ 强化':x.trend==='削弱'?'↓ 削弱':'→ 稳定';d.innerHTML='<div class="narrHead"><div><div class="narrTitle">'+x.title+'</div><div class="narrDesc">'+x.description+'</div></div><div class="narrStrength">'+fmt(x.strength)+'</div></div><div class="narrBar"><i style="width:'+Math.max(0,Math.min(100,Number(x.strength)||0))+'%"></i></div><div class="narrMeta"><span class="pill">'+x.strength_label+'</span><span class="pill">'+trend+'</span><span class="pill">证据一致 '+fmt(x.evidence_consistency_pct)+'%</span><span class="pill">覆盖 '+fmt(x.coverage_pct)+'%</span></div><div class="narrEvidence"><div class="tiny">主要支持证据</div>'+evidenceRows(x.supporting_evidence,false)+'<div class="tiny" style="margin-top:7px">主要反证 / 最弱证据</div>'+evidenceRows(x.counter_evidence,true)+'</div>';root.appendChild(d)});if(!root.children.length)root.innerHTML='<div class="empty">当前叙事数据不足。</div>'};
  paint('#bullNarratives',n.bull,'bull');paint('#bearNarratives',n.bear,'bear');
  const m=n.methodology||{};document.querySelector('#narrMethod').textContent=(m.warning||'')+' 证据一致度 = 已接入证据中，叙事方向评分≥60的权重占比。';
}
'''


def patch_html() -> None:
    html = HTML_PATH.read_text(encoding="utf-8")

    if "/* NARRATIVE_LAYER_V1 */" not in html:
        html = html.replace("</style>", NARRATIVE_CSS + "\n</style>", 1)

    if 'id="tabNarrative"' not in html:
        marker = '<a class="tab" href="https://github.com/galbbb2772/market-indicators-v1/actions/workflows/daily_update.yml"'
        tab = '<button class="tab" id="tabNarrative" onclick="switchTab(\'narrative\')">市场叙事</button>'
        if marker not in html:
            raise RuntimeError("Could not locate update-data tab marker")
        html = html.replace(marker, tab + marker, 1)

    if 'id="narrativeView"' not in html:
        marker = '<section id="historyView" class="hidden">'
        if marker not in html:
            raise RuntimeError("Could not locate history section marker")
        html = html.replace(marker, NARRATIVE_SECTION + "\n\n" + marker, 1)

    old_tabs = "['overall','history','divergence','variables']"
    if old_tabs in html:
        html = html.replace(old_tabs, "['overall','history','divergence','variables','narrative']", 1)
    old_switch_tail = "if(which==='variables')renderVariableTable()}"
    if old_switch_tail in html:
        html = html.replace(old_switch_tail, "if(which==='variables')renderVariableTable();if(which==='narrative')renderNarratives()}", 1)

    if "function renderNarratives()" not in html:
        marker = "function filtered(){"
        if marker not in html:
            raise RuntimeError("Could not locate JS insertion marker")
        html = html.replace(marker, NARRATIVE_JS + "\n" + marker, 1)

    HTML_PATH.write_text(html, encoding="utf-8")


def main() -> None:
    data = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    data["narrative_layer"] = build_narrative_layer(data)
    DATA_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    patch_html()
    print("Narrative Layer V1 patched")


if __name__ == "__main__":
    main()
