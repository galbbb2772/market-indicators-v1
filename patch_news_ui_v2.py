from pathlib import Path

ROOT = Path(__file__).resolve().parent
HTML = ROOT / "docs" / "index.html"
MARKER = "NEWS_SIGNAL_V2_CONFIRMATION_UI"


def main() -> None:
    text = HTML.read_text(encoding="utf-8")
    if MARKER in text:
        print("News confirmation UI already installed; no changes.")
        return
    if "NEWS_SIGNAL_V1_UI" not in text:
        raise RuntimeError("News Signal V1 UI must be installed first")

    css = r'''
/* NEWS_SIGNAL_V2_CONFIRMATION_UI */
.newsConfirm{margin-top:9px;padding-top:9px;border-top:1px solid #263852;font-size:12px;line-height:1.55;color:#aebed8}
.newsConfirm b{color:#e9f1ff}.newsConfirm.confirmed b{color:#61dfb2}.newsConfirm.partial b{color:#ffc95c}.newsConfirm.contradicted b{color:#ff738b}.newsConfirm.unconfirmed b{color:#91a8ca}
.newsAssets{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:10px;margin:12px 0}.newsAsset{background:#0e1725;border:1px solid #253752;border-radius:12px;padding:11px}.newsAsset small{display:block;color:#91a8ca}.newsAsset b{font-size:18px}.newsAsset .tiny{margin-top:4px}
@media(max-width:800px){.newsAssets{grid-template-columns:repeat(2,minmax(0,1fr))}}@media(max-width:520px){.newsAssets{grid-template-columns:1fr}}
'''
    text = text.replace("</style>", css + "\n</style>", 1)

    old = '<div class="newsHero" id="newsSignalCards"><div class="empty">正在读取新闻信号…</div></div>\n  <div class="newsEvents" id="newsEventPanels"></div>'
    new = '<div class="newsHero" id="newsSignalCards"><div class="empty">正在读取新闻信号…</div></div>\n  <div class="newsAssets" id="marketReactionAssets"><div class="empty">正在读取 VIX / WTI / 黄金 / SPY 市场确认…</div></div>\n  <div class="newsEvents" id="newsEventPanels"></div>'
    if old not in text:
        raise RuntimeError("news cards anchor not found")
    text = text.replace(old, new, 1)

    text = text.replace(
        'News Signal V1 · 新闻 / 事件层',
        'News Signal V1.4 · 新闻 + 市场反应确认层',
        1,
    )
    text = text.replace(
        '自动抓取市场相关政策、地缘、系统性风险、AI 与负面叙事新闻。V1 只做解释与前瞻记录，<b>暂不参与 Market Model V2 总分</b>，避免未经 Forward 验证的文本信号污染现有 20 个 Active 指标。',
        '自动抓取市场相关政策、地缘、系统性风险、AI 与负面叙事新闻，并用 <b>VIX / WTI 原油 / 黄金 / SPY</b> 的实际价格反应自动确认。原始新闻分、市场确认分、反应调整分都会留档；<b>暂不参与 Market Model V2 总分</b>，先做 Forward 验证。',
        1,
    )

    js_anchor = "\nfunction filtered(){"
    if js_anchor not in text:
        raise RuntimeError("JS insertion anchor not found")
    news_js = r'''

// NEWS_SIGNAL_V2_CONFIRMATION_UI
function renderNewsSignals(){
  const n=DATA.news_signal_v1||{},signals=n.signals||{},root=document.querySelector('#newsSignalCards'),panels=document.querySelector('#newsEventPanels'),status=document.querySelector('#newsSourceStatus'),assetsRoot=document.querySelector('#marketReactionAssets');
  if(!root||!panels||!status)return;
  const defs=[
    ['us_policy_event_sentiment','🏛️','美国政策事件'],
    ['geopolitical_news_risk','🌍','地缘政治'],
    ['systemic_news_risk','🏦','系统性风险'],
    ['ai_narrative_risk','🤖','AI 叙事风险'],
    ['negative_narrative_density','👻','负面叙事密度']
  ];
  const stateLabel={confirmed:'已确认',partial:'部分确认',contradicted:'市场反向',unconfirmed:'尚未确认'};
  const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  root.innerHTML='';panels.innerHTML='';
  defs.forEach(([id,icon,label])=>{
    const x=signals[id]||{},score=Number(x.score),safe=Number.isFinite(score)?Math.max(0,Math.min(100,score)):0,mc=x.market_confirmation||{},mcs=Number(mc.score),st=mc.state||'unconfirmed';
    const c=document.createElement('article');c.className='newsCard';
    c.innerHTML='<small>'+icon+' '+label+'</small><div class="newsScore">'+fmt(x.score)+'</div><div class="newsBar"><i style="width:'+safe+'%"></i></div><div class="newsMeta">风险成分 '+fmt(x.risk_component)+' · 关注度 '+fmt(x.attention_component)+'<br>事件 '+(x.event_count??0)+' · 来源 '+(x.source_count??0)+'</div><div class="newsConfirm '+st+'"><b>市场确认 '+fmt(mc.score)+' · '+(stateLabel[st]||st)+'</b><br>反应调整分 '+fmt(x.reaction_adjusted_score)+(mc.confirmed_by?.length?'<br>确认资产：'+esc(mc.confirmed_by.join(' / ')):'')+(mc.contradicted_by?.length?'<br>反向资产：'+esc(mc.contradicted_by.join(' / ')):'')+'</div>';
    root.appendChild(c);
    const p=document.createElement('div');p.className='newsEventPanel';p.innerHTML='<h3>'+icon+' '+label+' · 重点事件</h3>';
    const events=(x.top_events||[]).slice(0,5);
    if(!events.length){p.innerHTML+='<div class="empty">当前没有通过金融语境过滤的重点事件。</div>'}
    events.forEach(e=>{const row=document.createElement('div');row.className='newsEvent';const href=esc(e.url||'#');row.innerHTML='<a href="'+href+'" target="_blank" rel="noopener noreferrer">'+esc(e.title||'Untitled')+'</a><div class="newsEventMeta">'+esc((e.sources||[]).join(' · '))+' · '+fmt(e.age_hours)+'h 前 · severity '+fmt(e.severity)+'</div>';p.appendChild(row)});
    panels.appendChild(p);
  });
  if(assetsRoot){
    assetsRoot.innerHTML='';const a=(n.market_reaction||{}).assets||{};
    [['vix','VIX'],['oil','WTI 原油'],['gold','黄金'],['spy','SPY']].forEach(([k,label])=>{const x=a[k]||{},d=document.createElement('div');d.className='newsAsset';d.innerHTML='<small>'+label+'</small><b>'+fmt(x.day_pct)+'%</b><div class="tiny">1D · 5D '+fmt(x.five_day_pct)+'% · close '+fmt(x.close)+'</div>';assetsRoot.appendChild(d)});
    if(!assetsRoot.children.length)assetsRoot.innerHTML='<div class="empty">市场确认价格数据暂不可用。</div>';
  }
  const s=n.source_status||{},errs=s.errors||{},mr=n.market_reaction||{},mre=mr.errors||{};status.innerHTML='<b>数据状态：</b> '+esc(n.version||'—')+' · 模式 '+esc(s.query_mode||'—')+' · 去重事件 '+(s.events_after_dedupe??0)+' · 独立来源 '+(s.unique_sources_seen??0)+' · 新闻源错误 '+Object.keys(errs).length+' · 市场数据错误 '+Object.keys(mre).length+'<br><b>说明：</b> '+esc(n.policy||'News layer is context-only.')+(Object.keys(errs).length?'<br><b>新闻源错误：</b> '+esc(JSON.stringify(errs)):'')+(Object.keys(mre).length?'<br><b>市场数据错误：</b> '+esc(JSON.stringify(mre)):'');
}
'''
    text = text.replace(js_anchor, news_js + js_anchor, 1)
    HTML.write_text(text, encoding="utf-8")
    print("News confirmation UI installed.")


if __name__ == "__main__":
    main()
