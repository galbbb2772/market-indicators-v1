from pathlib import Path

p = Path(__file__).resolve().parent / "docs" / "sentiment.html"
html = p.read_text(encoding="utf-8")

CSS_MARKER = "/* SENTIMENT_INDEX_RETURN_V1 */"
if CSS_MARKER not in html:
    css = r'''
/* SENTIMENT_INDEX_RETURN_V1 */
.indexReturnPanel{margin-top:12px;padding-top:12px;border-top:1px solid #1c304d}.indexReturnHead{display:flex;gap:10px;align-items:end;justify-content:space-between;flex-wrap:wrap;margin-bottom:8px}.indexReturnHead h4{margin:0}.indexReturnHead label{font-size:10px;color:var(--m)}.indexReturnHead select{border:1px solid var(--line);background:#0b1729;color:var(--t);padding:9px 11px;border-radius:10px}.indexReturnMeta{font-size:11px;color:var(--m)}.indexReturnCanvas{position:relative}.indexReturnCanvas canvas{width:100%;height:230px;display:block;touch-action:none;cursor:grab}.indexReturnCanvas canvas.dragging{cursor:grabbing}.indexReturnHover{min-height:22px;font-size:12px;color:#dbe9ff;margin-top:6px}@media(max-width:620px){.indexReturnCanvas canvas{height:210px}.indexReturnHead select{width:100%}}
'''.strip()
    html = html.replace('</style>', css + '\n</style>', 1)

ui_anchor = '<div class="stats" id="historyStats"></div>'
ui = '''<div class="indexReturnPanel" id="indexReturnPanel">
<div class="indexReturnHead"><div><h4>指数涨跌幅</h4><div class="indexReturnMeta" id="indexReturnMeta">当前视窗起点 = 0%</div></div><label>指数<br><select id="indexReturnSelect" onchange="renderIndexReturn()"><option value="sp500">S&amp;P 500</option><option value="nasdaq">Nasdaq Composite</option><option value="dow">Dow Jones</option></select></label></div>
<div class="indexReturnCanvas"><canvas id="indexReturnChart"></canvas></div>
<div class="indexReturnHover" id="indexReturnHover">和上方情绪图共用同一时间窗口。</div>
</div>'''
if 'id="indexReturnPanel"' not in html:
    if ui_anchor not in html:
        raise SystemExit('history stats anchor not found')
    html = html.replace(ui_anchor, ui_anchor + '\n' + ui, 1)

js_anchor = 'function riskOn'
js = r'''
const INDEX_RETURN_LABELS={sp500:'S&P 500',nasdaq:'Nasdaq Composite',dow:'Dow Jones'};
let INDEX_RETURN_POINTS=[];
function renderIndexReturn(){const c=$('#indexReturnChart');if(!c||!HISTORY_ALL.length)return;const key=$('#indexReturnSelect')?.value||'sp500';const rows=HISTORY_ALL.slice(HISTORY_VIEW.start,HISTORY_VIEW.end);const {ctx,w,h}=setupCanvas('#indexReturnChart');ctx.clearRect(0,0,w,h);const valid=rows.filter(r=>Number.isFinite(Number(r[key])));if(valid.length<2){ctx.fillStyle='#91a8ca';ctx.font='20px system-ui';ctx.fillText('该指数在当前窗口数据不足',30,42);INDEX_RETURN_POINTS=[];return}const base=Number(valid[0][key]);const vals=rows.map(r=>Number.isFinite(Number(r[key]))&&base?((Number(r[key])/base)-1)*100:null);const finite=vals.filter(Number.isFinite);let lo=Math.min(...finite),hi=Math.max(...finite);if(lo===hi){lo-=1;hi+=1}const padAmt=Math.max(1,(hi-lo)*0.12);lo=Math.min(lo-padAmt,0);hi=Math.max(hi+padAmt,0);const pad={l:62,r:28,t:20,b:36},pw=w-pad.l-pad.r,ph=h-pad.t-pad.b,x=i=>pad.l+i/Math.max(1,rows.length-1)*pw,y=v=>pad.t+(hi-v)/(hi-lo)*ph;ctx.font='19px system-ui';const ticks=4;for(let i=0;i<=ticks;i++){const v=lo+(hi-lo)*i/ticks;ctx.fillStyle='#728aaa';ctx.fillText((v>0?'+':'')+v.toFixed(1)+'%',4,y(v)+6);ctx.strokeStyle=Math.abs(v)<(hi-lo)/ticks/2?'#3d587c':'#20344f';ctx.beginPath();ctx.moveTo(pad.l,y(v));ctx.lineTo(w-pad.r,y(v));ctx.stroke()}const zeroY=y(0);if(zeroY>=pad.t&&zeroY<=h-pad.b){ctx.strokeStyle='#506b91';ctx.lineWidth=2;ctx.beginPath();ctx.moveTo(pad.l,zeroY);ctx.lineTo(w-pad.r,zeroY);ctx.stroke()}const pts=rows.map((r,i)=>({date:r.date,value:vals[i],x:x(i)}));ctx.strokeStyle='#79a9ff';ctx.lineWidth=3;ctx.beginPath();let on=false;pts.forEach(p=>{if(!Number.isFinite(p.value)){on=false;return}if(on)ctx.lineTo(p.x,y(p.value));else{ctx.moveTo(p.x,y(p.value));on=true}});ctx.stroke();ctx.fillStyle='#728aaa';for(let i=0;i<=5;i++){const j=Math.min(rows.length-1,Math.round(i*(rows.length-1)/5));ctx.fillText(rows[j].date,Math.max(0,pts[j].x-46),h-9)}INDEX_RETURN_POINTS=pts;const last=[...pts].reverse().find(p=>Number.isFinite(p.value));const meta=$('#indexReturnMeta');if(meta)meta.textContent=INDEX_RETURN_LABELS[key]+' · '+rows[0].date+' = 0% · 当前 '+(last?((last.value>0?'+':'')+last.value.toFixed(2)+'%'):'—')}
function indexReturnPointer(ev){if(!INDEX_RETURN_POINTS.length||HISTORY_VIEW.dragging)return;const c=$('#indexReturnChart'),r=c.getBoundingClientRect(),px=((ev.touches?ev.touches[0].clientX:ev.clientX)-r.left)*c.width/r.width;let best=INDEX_RETURN_POINTS[0],dist=Infinity;INDEX_RETURN_POINTS.forEach(p=>{const d=Math.abs(p.x-px);if(d<dist&&Number.isFinite(p.value)){dist=d;best=p}});if(best&&Number.isFinite(best.value))$('#indexReturnHover').textContent=best.date+' · '+INDEX_RETURN_LABELS[$('#indexReturnSelect').value]+' '+(best.value>0?'+':'')+best.value.toFixed(2)+'%'}
function installIndexReturnPanZoom(){const c=$('#indexReturnChart');if(!c||c.dataset.panzoomInstalled)return;c.dataset.panzoomInstalled='1';let mouseBase=null,touchBase=null,pinchBase=null;const width=()=>Math.max(1,c.getBoundingClientRect().width);c.addEventListener('wheel',e=>{if(!HISTORY_ALL.length)return;e.preventDefault();const r=c.getBoundingClientRect(),ratio=(e.clientX-r.left)/Math.max(1,r.width);zoomHistoryAt(e.deltaY>0?1.18:0.84,ratio)},{passive:false});c.addEventListener('mousedown',e=>{if(e.button!==0||!HISTORY_ALL.length)return;HISTORY_VIEW.dragging=true;c.classList.add('dragging');mouseBase={x:e.clientX,start:HISTORY_VIEW.start,span:HISTORY_VIEW.end-HISTORY_VIEW.start}});window.addEventListener('mousemove',e=>{if(!mouseBase)return;const dx=e.clientX-mouseBase.x,shift=Math.round(-dx/width()*mouseBase.span);panHistoryTo(mouseBase.start+shift)});window.addEventListener('mouseup',()=>{mouseBase=null;HISTORY_VIEW.dragging=false;c.classList.remove('dragging')});c.addEventListener('mousemove',indexReturnPointer);c.addEventListener('touchstart',e=>{if(!HISTORY_ALL.length)return;if(e.touches.length===1){HISTORY_VIEW.dragging=true;touchBase={x:e.touches[0].clientX,start:HISTORY_VIEW.start,span:HISTORY_VIEW.end-HISTORY_VIEW.start};pinchBase=null}else if(e.touches.length>=2){const a=e.touches[0],b=e.touches[1],dist=Math.hypot(a.clientX-b.clientX,a.clientY-b.clientY),r=c.getBoundingClientRect(),mid=(a.clientX+b.clientX)/2;pinchBase={dist:Math.max(1,dist),span:HISTORY_VIEW.end-HISTORY_VIEW.start,anchor:HISTORY_VIEW.start+(HISTORY_VIEW.end-HISTORY_VIEW.start)*((mid-r.left)/Math.max(1,r.width))};touchBase=null}}, {passive:true});c.addEventListener('touchmove',e=>{if(!HISTORY_ALL.length)return;e.preventDefault();if(e.touches.length===1&&touchBase){const dx=e.touches[0].clientX-touchBase.x,shift=Math.round(-dx/width()*touchBase.span);panHistoryTo(touchBase.start+shift)}else if(e.touches.length>=2&&pinchBase){const a=e.touches[0],b=e.touches[1],dist=Math.max(1,Math.hypot(a.clientX-b.clientX,a.clientY-b.clientY)),r=c.getBoundingClientRect(),mid=(a.clientX+b.clientX)/2,ratio=Math.max(0,Math.min(1,(mid-r.left)/Math.max(1,r.width))),newSpan=Math.max(historyMinPoints(),Math.min(HISTORY_ALL.length,Math.round(pinchBase.span*pinchBase.dist/dist))),newStart=Math.round(pinchBase.anchor-newSpan*ratio);const [s,en]=clampHistoryWindow(newStart,newSpan);HISTORY_VIEW.start=s;HISTORY_VIEW.end=en;renderHistory()}},{passive:false});c.addEventListener('touchend',()=>{touchBase=null;pinchBase=null;HISTORY_VIEW.dragging=false})}
const __renderHistoryWithIndex=renderHistory;
renderHistory=function(){__renderHistoryWithIndex();renderIndexReturn();};
'''.strip()
if 'function renderIndexReturn()' not in html:
    if js_anchor not in html:
        raise SystemExit('riskOn anchor not found')
    html = html.replace(js_anchor, js + '\n' + js_anchor, 1)

if 'installHistoryPanZoom();installIndexReturnPanZoom();' not in html:
    html = html.replace('installHistoryPanZoom();', 'installHistoryPanZoom();installIndexReturnPanZoom();', 1)

p.write_text(html, encoding='utf-8')
print('sentiment synchronized index-return chart installed')
