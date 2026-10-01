from pathlib import Path
import re

p = Path(__file__).resolve().parent / "docs" / "sentiment.html"
html = p.read_text(encoding="utf-8")

CSS_MARKER = "/* SENTIMENT_PANZOOM_V1 */"
if CSS_MARKER not in html:
    css = r'''
/* SENTIMENT_PANZOOM_V1 */
.historyViewportBar{display:flex;gap:8px;align-items:center;flex-wrap:wrap;margin:8px 0 4px}.historyViewportBar button{border:1px solid var(--line);background:#0b1729;color:var(--t);padding:8px 11px;border-radius:10px;cursor:pointer}.historyViewportBar button:hover{border-color:#486a97}.historyWindowLabel{font-size:11px;color:var(--m);margin-left:auto}.historyGestureHint{font-size:11px;color:var(--m);margin-top:4px}.canvasWrap #historyChart{cursor:grab}.canvasWrap #historyChart.dragging{cursor:grabbing}@media(max-width:620px){.historyViewportBar button{flex:1;min-width:calc(50% - 4px)}.historyWindowLabel{width:100%;margin-left:0}}
'''.strip()
    html = html.replace('</style>', css + '\n</style>', 1)

ui_old = '<div class="canvasWrap"><canvas id="historyChart"></canvas></div><div class="hover" id="historyHover">移动鼠标 / 触摸曲线查看日期。</div>'
ui_new = '''<div class="canvasWrap"><canvas id="historyChart"></canvas></div>
<div class="historyViewportBar"><button type="button" onclick="zoomHistoryAt(0.75,0.5)">＋ 放大</button><button type="button" onclick="zoomHistoryAt(1.33,0.5)">－ 缩小</button><button type="button" onclick="resetHistoryViewport()">默认</button><button type="button" onclick="showAllHistory()">全范围</button><span class="historyWindowLabel" id="historyWindowLabel"></span></div>
<div class="historyGestureHint">单指 / 鼠标左右拖动查看历史 · 双指 / 滚轮缩放；缩放范围已限制，不会无限放大或缩小。</div>
<div class="hover" id="historyHover">移动鼠标查看当前窗口数值。</div>'''
if 'id="historyWindowLabel"' not in html:
    if ui_old not in html:
        raise SystemExit('history chart UI anchor not found')
    html = html.replace(ui_old, ui_new, 1)

state_anchor = 'const visibleSeries={optimism:true,pessimism:true,total_negative:true,euphoria:true};'
state_add = "\nlet HISTORY_ALL=[];\nconst HISTORY_VIEW={start:0,end:0,key:'',dragging:false};"
if 'const HISTORY_VIEW=' not in html:
    if state_anchor not in html:
        raise SystemExit('visibleSeries anchor not found')
    html = html.replace(state_anchor, state_anchor + state_add, 1)

replacement = r'''function historyMinPoints(){const g=$('#histGran')?.value||'day';return g==='month'?6:g==='week'?8:20}
function historyDefaultSpan(len){const g=$('#histGran')?.value||'day';const cap=g==='month'?60:g==='week'?156:504;return Math.min(len,Math.max(historyMinPoints(),cap))}
function clampHistoryWindow(start,span){const len=HISTORY_ALL.length,min=Math.min(len,historyMinPoints());span=Math.max(min,Math.min(len,Math.round(span||len)));start=Math.round(start||0);start=Math.max(0,Math.min(Math.max(0,len-span),start));return [start,start+span]}
function setHistoryWindow(start,span){if(!HISTORY_ALL.length)return;const [s,e]=clampHistoryWindow(start,span);HISTORY_VIEW.start=s;HISTORY_VIEW.end=e;renderHistory()}
function resetHistoryViewport(){if(!HISTORY_ALL.length)return;const span=historyDefaultSpan(HISTORY_ALL.length);HISTORY_VIEW.start=Math.max(0,HISTORY_ALL.length-span);HISTORY_VIEW.end=HISTORY_ALL.length;renderHistory()}
function showAllHistory(){if(!HISTORY_ALL.length)return;HISTORY_VIEW.start=0;HISTORY_VIEW.end=HISTORY_ALL.length;renderHistory()}
function zoomHistoryAt(factor,ratio=0.5){if(!HISTORY_ALL.length)return;const start=HISTORY_VIEW.start,end=HISTORY_VIEW.end,span=Math.max(1,end-start),anchor=start+span*Math.max(0,Math.min(1,ratio));const newSpan=Math.max(historyMinPoints(),Math.min(HISTORY_ALL.length,Math.round(span*factor)));let newStart=Math.round(anchor-newSpan*Math.max(0,Math.min(1,ratio)));const [s,e]=clampHistoryWindow(newStart,newSpan);HISTORY_VIEW.start=s;HISTORY_VIEW.end=e;renderHistory()}
function panHistoryTo(start){if(!HISTORY_ALL.length)return;const span=HISTORY_VIEW.end-HISTORY_VIEW.start,[s,e]=clampHistoryWindow(start,span);HISTORY_VIEW.start=s;HISTORY_VIEW.end=e;renderHistory()}
function renderHistory(){let all=historyRows();all=resample(all,$('#histGran').value);HISTORY_ALL=all;const sourceKey=$('#histStart').value+'|'+$('#histEnd').value+'|'+$('#histGran').value;if(sourceKey!==HISTORY_VIEW.key){HISTORY_VIEW.key=sourceKey;const span=historyDefaultSpan(all.length);HISTORY_VIEW.start=Math.max(0,all.length-span);HISTORY_VIEW.end=all.length}if(!all.length){const {ctx}=setupCanvas('#historyChart');ctx.clearRect(0,0,99999,99999);return}const [vs,ve]=clampHistoryWindow(HISTORY_VIEW.start,HISTORY_VIEW.end-HISTORY_VIEW.start);HISTORY_VIEW.start=vs;HISTORY_VIEW.end=ve;let rows=all.slice(vs,ve);const {c,ctx,w,h}=setupCanvas('#historyChart');ctx.clearRect(0,0,w,h);if(rows.length<2){ctx.fillStyle='#91a8ca';ctx.fillText('所选区间数据不足',30,40);return}const pad={l:58,r:28,t:22,b:38},pw=w-pad.l-pad.r,ph=h-pad.t-pad.b,x=i=>pad.l+i/(rows.length-1)*pw,y=v=>pad.t+(100-v)/100*ph;ctx.font='20px system-ui';[0,20,30,50,60,80,100].forEach(v=>{ctx.fillStyle='#728aaa';ctx.fillText(v,8,y(v)+6);ctx.strokeStyle=v===80?'#62333f':'#20344f';ctx.beginPath();ctx.moveTo(pad.l,y(v));ctx.lineTo(w-pad.r,y(v));ctx.stroke()});const pts=rows.map((r,i)=>({...r,x:x(i)}));const defs=[['optimism','#61dfb2',3],['pessimism','#ff738b',3],['total_negative','#ffc95c',3],['euphoria','#eef5ff',4]];defs.forEach(([key,color,width])=>{if(visibleSeries[key])line(ctx,pts,key,color,y,width)});ctx.fillStyle='#728aaa';for(let i=0;i<=5;i++){const j=Math.min(rows.length-1,Math.round(i*(rows.length-1)/5));ctx.fillText(rows[j].date,Math.max(0,pts[j].x-46),h-10)}HIST_POINTS=pts;const label=$('#historyWindowLabel');if(label)label.textContent=rows[0].date+' → '+rows[rows.length-1].date+' · '+rows.length+' 点';const s=$('#historyStats');s.innerHTML='';[['乐观均值',mean(rows.map(r=>r.optimism))],['悲观均值',mean(rows.map(r=>r.pessimism))],['总负面均值',mean(rows.map(r=>r.total_negative))],['狂热均值',mean(rows.map(r=>r.euphoria))],['狂热≥80天数',rows.filter(r=>Number(r.euphoria)>=80).length]].forEach(([n,v])=>{const d=document.createElement('div');d.className='stat';d.innerHTML='<small>'+n+'</small><b>'+fmt(v)+'</b>';s.appendChild(d)})}
function historyPointer(ev){if(!HIST_POINTS.length||HISTORY_VIEW.dragging)return;const c=$('#historyChart'),r=c.getBoundingClientRect(),px=((ev.touches?ev.touches[0].clientX:ev.clientX)-r.left)*c.width/r.width;let best=HIST_POINTS[0],dist=Infinity;HIST_POINTS.forEach(p=>{const d=Math.abs(p.x-px);if(d<dist){dist=d;best=p}});const parts=[best.date];if(visibleSeries.optimism)parts.push('乐观 '+fmt(best.optimism));if(visibleSeries.pessimism)parts.push('悲观 '+fmt(best.pessimism));if(visibleSeries.total_negative)parts.push('总负面 '+fmt(best.total_negative));if(visibleSeries.euphoria)parts.push('狂热 '+fmt(best.euphoria));$('#historyHover').textContent=parts.join(' · ')}
function installHistoryPanZoom(){const c=$('#historyChart');if(!c||c.dataset.panzoomInstalled)return;c.dataset.panzoomInstalled='1';let mouseBase=null,touchBase=null,pinchBase=null;const width=()=>Math.max(1,c.getBoundingClientRect().width);c.addEventListener('wheel',e=>{if(!HISTORY_ALL.length)return;e.preventDefault();const r=c.getBoundingClientRect(),ratio=(e.clientX-r.left)/Math.max(1,r.width);zoomHistoryAt(e.deltaY>0?1.18:0.84,ratio)},{passive:false});c.addEventListener('mousedown',e=>{if(e.button!==0||!HISTORY_ALL.length)return;HISTORY_VIEW.dragging=true;c.classList.add('dragging');mouseBase={x:e.clientX,start:HISTORY_VIEW.start,span:HISTORY_VIEW.end-HISTORY_VIEW.start}});window.addEventListener('mousemove',e=>{if(!mouseBase)return;const dx=e.clientX-mouseBase.x,shift=Math.round(-dx/width()*mouseBase.span);panHistoryTo(mouseBase.start+shift)});window.addEventListener('mouseup',()=>{mouseBase=null;HISTORY_VIEW.dragging=false;c.classList.remove('dragging')});c.addEventListener('mousemove',historyPointer);c.addEventListener('touchstart',e=>{if(!HISTORY_ALL.length)return;if(e.touches.length===1){HISTORY_VIEW.dragging=true;touchBase={x:e.touches[0].clientX,start:HISTORY_VIEW.start,span:HISTORY_VIEW.end-HISTORY_VIEW.start};pinchBase=null}else if(e.touches.length>=2){const a=e.touches[0],b=e.touches[1],dist=Math.hypot(a.clientX-b.clientX,a.clientY-b.clientY),r=c.getBoundingClientRect(),mid=(a.clientX+b.clientX)/2;pinchBase={dist:Math.max(1,dist),span:HISTORY_VIEW.end-HISTORY_VIEW.start,anchor:HISTORY_VIEW.start+(HISTORY_VIEW.end-HISTORY_VIEW.start)*((mid-r.left)/Math.max(1,r.width))};touchBase=null}}, {passive:true});c.addEventListener('touchmove',e=>{if(!HISTORY_ALL.length)return;e.preventDefault();if(e.touches.length===1&&touchBase){const dx=e.touches[0].clientX-touchBase.x,shift=Math.round(-dx/width()*touchBase.span);panHistoryTo(touchBase.start+shift)}else if(e.touches.length>=2&&pinchBase){const a=e.touches[0],b=e.touches[1],dist=Math.max(1,Math.hypot(a.clientX-b.clientX,a.clientY-b.clientY)),r=c.getBoundingClientRect(),mid=(a.clientX+b.clientX)/2,ratio=Math.max(0,Math.min(1,(mid-r.left)/Math.max(1,r.width))),newSpan=Math.max(historyMinPoints(),Math.min(HISTORY_ALL.length,Math.round(pinchBase.span*pinchBase.dist/dist))),newStart=Math.round(pinchBase.anchor-newSpan*ratio);const [s,en]=clampHistoryWindow(newStart,newSpan);HISTORY_VIEW.start=s;HISTORY_VIEW.end=en;renderHistory()}},{passive:false});c.addEventListener('touchend',()=>{touchBase=null;pinchBase=null;HISTORY_VIEW.dragging=false})}
function riskOn'''

pattern = r"function renderHistory\(\)\{.*?\}\nfunction historyPointer\(ev\)\{.*?\}\nfunction riskOn"
if 'function installHistoryPanZoom()' not in html:
    html2, n = re.subn(pattern, replacement, html, count=1, flags=re.S)
    if n != 1:
        raise SystemExit(f'history function block replace failed: {n}')
    html = html2

old_events = "$('#historyChart').addEventListener('mousemove',historyPointer);$('#historyChart').addEventListener('touchmove',e=>{historyPointer(e);e.preventDefault()},{passive:false});"
if old_events in html:
    html = html.replace(old_events, 'installHistoryPanZoom();', 1)
elif 'installHistoryPanZoom();' not in html:
    raise SystemExit('history event anchor not found')

p.write_text(html, encoding='utf-8')
print('sentiment history pan/zoom installed')
