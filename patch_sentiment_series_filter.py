from pathlib import Path

p = Path(__file__).resolve().parent / "docs" / "sentiment.html"
html = p.read_text(encoding="utf-8")

CSS_MARKER = "/* SENTIMENT_SERIES_FILTER_V1 */"
if CSS_MARKER not in html:
    css_anchor = '.legend span::before{content:"";display:inline-block;width:16px;height:3px;background:var(--c);margin-right:6px;vertical-align:middle}'
    css = r'''
/* SENTIMENT_SERIES_FILTER_V1 */
.seriesFilter{display:flex;gap:9px;flex-wrap:wrap;align-items:center;margin:10px 0 12px}.seriesBox{display:flex;align-items:center;gap:8px;padding:10px 12px;border:1px solid var(--line);border-radius:12px;background:#0b1729;color:var(--t);cursor:pointer;user-select:none;min-height:42px;transition:opacity .15s ease,border-color .15s ease,background .15s ease}.seriesBox input{width:18px;height:18px;margin:0;accent-color:#79a9ff;cursor:pointer}.seriesBox .seriesDot{width:12px;height:12px;border-radius:999px;background:var(--c);flex:0 0 auto}.seriesBox.active{border-color:#486a97;background:#10203a}.seriesBox.inactive{opacity:.48}.seriesBtn{border:1px solid var(--line);background:#0b1729;color:var(--t);padding:10px 12px;border-radius:12px;cursor:pointer;min-height:42px}.seriesBtn:hover{border-color:#486a97}.seriesEmpty{font-size:12px;color:var(--m);margin:2px 0 8px}@media(max-width:620px){.seriesFilter{gap:8px}.seriesBox{padding:10px;min-width:calc(50% - 4px);justify-content:flex-start}.seriesBtn{flex:1}}
'''.strip()
    if css_anchor not in html:
        raise SystemExit("CSS anchor not found")
    html = html.replace(css_anchor, css_anchor + css, 1)

legend_old = '<div class="legend"><span style="--c:#61dfb2">乐观度</span><span style="--c:#ff738b">悲观度</span><span style="--c:#ffc95c">总负面</span><span style="--c:#eef5ff">狂热度</span></div>'
legend_new = '''<div class="seriesFilter" id="seriesFilter">
<label class="seriesBox active" data-key="optimism"><input type="checkbox" checked onchange="toggleSeries('optimism',this.checked)"><span class="seriesDot" style="--c:#61dfb2"></span><span>乐观度</span></label>
<label class="seriesBox active" data-key="pessimism"><input type="checkbox" checked onchange="toggleSeries('pessimism',this.checked)"><span class="seriesDot" style="--c:#ff738b"></span><span>悲观度</span></label>
<label class="seriesBox active" data-key="total_negative"><input type="checkbox" checked onchange="toggleSeries('total_negative',this.checked)"><span class="seriesDot" style="--c:#ffc95c"></span><span>总负面</span></label>
<label class="seriesBox active" data-key="euphoria"><input type="checkbox" checked onchange="toggleSeries('euphoria',this.checked)"><span class="seriesDot" style="--c:#eef5ff"></span><span>狂热度</span></label>
<button type="button" class="seriesBtn" onclick="setAllSeries(true)">全选</button><button type="button" class="seriesBtn" onclick="setAllSeries(false)">清空</button>
</div><div class="seriesEmpty" id="seriesEmpty"></div>'''
if 'id="seriesFilter"' not in html:
    if legend_old not in html:
        raise SystemExit("Legend anchor not found")
    html = html.replace(legend_old, legend_new, 1)

state_old = 'let DATA={daily:[]},HIST_POINTS=[],DIV_POINTS=[];'
state_new = "let DATA={daily:[]},HIST_POINTS=[],DIV_POINTS=[];\nconst visibleSeries={optimism:true,pessimism:true,total_negative:true,euphoria:true};"
if 'const visibleSeries=' not in html:
    if state_old not in html:
        raise SystemExit("State anchor not found")
    html = html.replace(state_old, state_new, 1)

labels_anchor = "const labels={optimism:'乐观度',pessimism:'悲观度',total_negative:'总负面',euphoria:'狂热度'},idxLabels={sp500:'S&P 500',nasdaq:'Nasdaq',dow:'Dow Jones'};"
filter_functions = r'''
function syncSeriesBoxes(){document.querySelectorAll('#seriesFilter .seriesBox').forEach(box=>{const key=box.dataset.key,on=!!visibleSeries[key],input=box.querySelector('input');if(input)input.checked=on;box.classList.toggle('active',on);box.classList.toggle('inactive',!on)});const n=Object.values(visibleSeries).filter(Boolean).length,empty=$('#seriesEmpty');if(empty)empty.textContent=n?'':'当前没有选择指标；勾选上方任意一项即可显示。'}
function toggleSeries(key,checked){visibleSeries[key]=!!checked;syncSeriesBoxes();renderHistory()}
function setAllSeries(flag){Object.keys(visibleSeries).forEach(k=>visibleSeries[k]=!!flag);syncSeriesBoxes();renderHistory()}
'''.strip()
if 'function syncSeriesBoxes()' not in html:
    if labels_anchor not in html:
        raise SystemExit("Labels anchor not found")
    html = html.replace(labels_anchor, labels_anchor + '\n' + filter_functions, 1)

lines_old = "line(ctx,pts,'optimism','#61dfb2',y,3);line(ctx,pts,'pessimism','#ff738b',y,3);line(ctx,pts,'total_negative','#ffc95c',y,3);line(ctx,pts,'euphoria','#eef5ff',y,4);"
lines_new = "const defs=[['optimism','#61dfb2',3],['pessimism','#ff738b',3],['total_negative','#ffc95c',3],['euphoria','#eef5ff',4]],activeCount=Object.values(visibleSeries).filter(Boolean).length;defs.forEach(([key,color,width])=>{if(visibleSeries[key])line(ctx,pts,key,color,y,width+(activeCount===1?2:0))});"
if 'activeCount=Object.values(visibleSeries)' not in html:
    if lines_old not in html:
        raise SystemExit("History line anchor not found")
    html = html.replace(lines_old, lines_new, 1)

pointer_old = "function historyPointer(ev){if(!HIST_POINTS.length)return;const c=$('#historyChart'),r=c.getBoundingClientRect(),px=((ev.touches?ev.touches[0].clientX:ev.clientX)-r.left)*c.width/r.width;let best=HIST_POINTS[0],dist=Infinity;HIST_POINTS.forEach(p=>{const d=Math.abs(p.x-px);if(d<dist){dist=d;best=p}});$('#historyHover').textContent=best.date+' · 乐观 '+fmt(best.optimism)+' · 悲观 '+fmt(best.pessimism)+' · 总负面 '+fmt(best.total_negative)+' · 狂热 '+fmt(best.euphoria)}"
pointer_new = "function historyPointer(ev){if(!HIST_POINTS.length)return;const c=$('#historyChart'),r=c.getBoundingClientRect(),px=((ev.touches?ev.touches[0].clientX:ev.clientX)-r.left)*c.width/r.width;let best=HIST_POINTS[0],dist=Infinity;HIST_POINTS.forEach(p=>{const d=Math.abs(p.x-px);if(d<dist){dist=d;best=p}});const parts=[best.date];if(visibleSeries.optimism)parts.push('乐观 '+fmt(best.optimism));if(visibleSeries.pessimism)parts.push('悲观 '+fmt(best.pessimism));if(visibleSeries.total_negative)parts.push('总负面 '+fmt(best.total_negative));if(visibleSeries.euphoria)parts.push('狂热 '+fmt(best.euphoria));$('#historyHover').textContent=parts.join(' · ')}"
if "parts.join(' · ')" not in html:
    if pointer_old not in html:
        raise SystemExit("History pointer anchor not found")
    html = html.replace(pointer_old, pointer_new, 1)

init_old = "renderLatest();renderHistory();renderDivergence();renderEuphoria();$('#updated').textContent='更新时间 '+new Date(DATA.generated_at).toLocaleString()"
init_new = "renderLatest();syncSeriesBoxes();renderHistory();renderDivergence();renderEuphoria();$('#updated').textContent='更新时间 '+new Date(DATA.generated_at).toLocaleString()"
if 'renderLatest();syncSeriesBoxes();renderHistory()' not in html:
    if init_old not in html:
        raise SystemExit("Init anchor not found")
    html = html.replace(init_old, init_new, 1)

p.write_text(html, encoding="utf-8")
print("sentiment series filter installed")
