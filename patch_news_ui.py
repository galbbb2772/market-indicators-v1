from pathlib import Path

ROOT = Path(__file__).resolve().parent
HTML = ROOT / "docs" / "index.html"
MARKER = "NEWS_SIGNAL_V1_UI"


def main() -> None:
    text = HTML.read_text(encoding="utf-8")
    if MARKER in text:
        print("News Signal UI already installed; no changes.")
        return

    css = r'''
/* NEWS_SIGNAL_V1_UI */
.newsHero{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:12px;margin:14px 0}
.newsCard{background:#111a29;border:1px solid #273957;border-radius:14px;padding:14px;min-width:0}
.newsCard small{color:#91a3bd}.newsCard .newsScore{font-size:30px;font-weight:800;margin:5px 0}.newsCard .newsMeta{font-size:12px;color:#9babc1;line-height:1.55}
.newsBar{height:7px;background:#1b2a40;border-radius:999px;overflow:hidden;margin:8px 0 10px}.newsBar i{display:block;height:100%;background:linear-gradient(90deg,#6d9dff,#e0a45c);border-radius:999px}
.newsEvents{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px;margin-top:12px}.newsEventPanel{background:#0e1725;border:1px solid #253752;border-radius:14px;padding:14px}
.newsEventPanel h3{margin:0 0 9px}.newsEvent{padding:9px 0;border-top:1px solid #21314a}.newsEvent:first-of-type{border-top:0}.newsEvent a{color:#dbe8ff;text-decoration:none;font-weight:650}.newsEvent a:hover{text-decoration:underline}.newsEventMeta{font-size:11px;color:#8496af;margin-top:4px}
.newsStatus{margin-top:12px;padding:12px 14px;border:1px solid #2a3c58;border-radius:12px;background:#0e1725;color:#9eb0c8;font-size:12px;line-height:1.65}
@media(max-width:900px){.newsHero{grid-template-columns:repeat(2,minmax(0,1fr))}.newsEvents{grid-template-columns:1fr}}
@media(max-width:560px){.newsHero{grid-template-columns:1fr}}
'''
    if "</style>" not in text:
        raise RuntimeError("style close anchor not found")
    text = text.replace("</style>", css + "\n</style>", 1)

    narrative_tab = '<button class="tab" id="tabNarrative" onclick="switchTab(\'narrative\')">市场叙事</button>'
    news_tab = '<button class="tab" id="tabNews" onclick="switchTab(\'news\')">新闻信号</button>'
    if narrative_tab not in text:
        raise RuntimeError("Narrative tab anchor not found")
    text = text.replace(narrative_tab, narrative_tab + news_tab, 1)

    section = r'''
<section id="newsView" class="hidden">
  <div class="hero">
    <div class="cat">News Signal V1 · 新闻 / 事件层</div>
    <div class="sub">自动抓取市场相关政策、地缘、系统性风险、AI 与负面叙事新闻。V1 只做解释与前瞻记录，<b>暂不参与 Market Model V2 总分</b>，避免未经 Forward 验证的文本信号污染现有 20 个 Active 指标。</div>
  </div>
  <div class="newsHero" id="newsSignalCards"><div class="empty">正在读取新闻信号…</div></div>
  <div class="newsEvents" id="newsEventPanels"></div>
  <div class="newsStatus" id="newsSourceStatus">等待新闻源状态…</div>
</section>
'''
    main_anchor = "</main>\n<script>"
    if main_anchor not in text:
        raise RuntimeError("main/script anchor not found")
    text = text.replace(main_anchor, section + "\n</main>\n<script>", 1)

    old_switch = "function switchTab(which){['overall','history','divergence','variables','narrative'].forEach(x=>{document.querySelector('#'+x+'View').classList.toggle('hidden',x!==which);document.querySelector('#tab'+x[0].toUpperCase()+x.slice(1)).classList.toggle('active',x===which)});if(which==='history')renderHistoryExplorer();if(which==='divergence')renderDivergence();if(which==='variables')renderVariableTable();if(which==='narrative')renderNarratives()}"
    new_switch = "function switchTab(which){['overall','history','divergence','variables','narrative','news'].forEach(x=>{document.querySelector('#'+x+'View').classList.toggle('hidden',x!==which);document.querySelector('#tab'+x[0].toUpperCase()+x.slice(1)).classList.toggle('active',x===which)});if(which==='history')renderHistoryExplorer();if(which==='divergence')renderDivergence();if(which==='variables')renderVariableTable();if(which==='narrative')renderNarratives();if(which==='news')renderNewsSignals()}"
    if old_switch not in text:
        raise RuntimeError("switchTab anchor not found")
    text = text.replace(old_switch, new_switch, 1)

    js_anchor = "\nfunction filtered(){"
    if js_anchor not in text:
        raise RuntimeError("JS insertion anchor not found")
    news_js = r'''

function renderNewsSignals(){
  const n=DATA.news_signal_v1||{},signals=n.signals||{},root=document.querySelector('#newsSignalCards'),panels=document.querySelector('#newsEventPanels'),status=document.querySelector('#newsSourceStatus');
  if(!root||!panels||!status)return;
  const defs=[
    ['us_policy_event_sentiment','🏛️','美国政策事件'],
    ['geopolitical_news_risk','🌍','地缘政治'],
    ['systemic_news_risk','🏦','系统性风险'],
    ['ai_narrative_risk','🤖','AI 叙事风险'],
    ['negative_narrative_density','👻','负面叙事密度']
  ];
  const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  root.innerHTML='';panels.innerHTML='';
  defs.forEach(([id,icon,label])=>{
    const x=signals[id]||{},score=Number(x.score),safe=Number.isFinite(score)?Math.max(0,Math.min(100,score)):0;
    const c=document.createElement('article');c.className='newsCard';
    c.innerHTML='<small>'+icon+' '+label+'</small><div class="newsScore">'+fmt(x.score)+'</div><div class="newsBar"><i style="width:'+safe+'%"></i></div><div class="newsMeta">风险成分 '+fmt(x.risk_component)+' · 关注度 '+fmt(x.attention_component)+'<br>事件 '+(x.event_count??0)+' · 来源 '+(x.source_count??0)+'</div>';
    root.appendChild(c);
    const p=document.createElement('div');p.className='newsEventPanel';p.innerHTML='<h3>'+icon+' '+label+' · 重点事件</h3>';
    const events=(x.top_events||[]).slice(0,5);
    if(!events.length){p.innerHTML+='<div class="empty">当前没有通过金融语境过滤的重点事件。</div>'}
    events.forEach(e=>{const row=document.createElement('div');row.className='newsEvent';const href=esc(e.url||'#');row.innerHTML='<a href="'+href+'" target="_blank" rel="noopener noreferrer">'+esc(e.title||'Untitled')+'</a><div class="newsEventMeta">'+esc((e.sources||[]).join(' · '))+' · '+fmt(e.age_hours)+'h 前 · severity '+fmt(e.severity)+'</div>';p.appendChild(row)});
    panels.appendChild(p);
  });
  if(!root.children.length)root.innerHTML='<div class="empty">尚未生成 News Signal V1 数据。</div>';
  const s=n.source_status||{},errs=s.errors||{};status.innerHTML='<b>数据状态：</b> '+esc(n.version||'—')+' · 模式 '+esc(s.query_mode||'—')+' · 去重事件 '+(s.events_after_dedupe??0)+' · 独立来源 '+(s.unique_sources_seen??0)+' · 错误 '+Object.keys(errs).length+'<br><b>说明：</b> '+esc(n.policy||'News layer is context-only.')+(Object.keys(errs).length?'<br><b>源错误：</b> '+esc(JSON.stringify(errs)):'');
}
'''
    text = text.replace(js_anchor, news_js + js_anchor, 1)

    HTML.write_text(text, encoding="utf-8")
    print("News Signal UI installed.")


if __name__ == "__main__":
    main()
