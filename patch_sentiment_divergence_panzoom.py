from pathlib import Path
import re

p = Path(__file__).resolve().parent / "docs" / "sentiment.html"
html = p.read_text(encoding="utf-8")

CSS_MARKER = "/* SENTIMENT_DIVERGENCE_PANZOOM_V1 */"
if CSS_MARKER not in html:
    css = r'''
/* SENTIMENT_DIVERGENCE_PANZOOM_V1 */
.canvasWrap #divChart{cursor:grab}.canvasWrap #divChart.dragging{cursor:grabbing}
'''.strip()
    html = html.replace('</style>', css + '\n</style>', 1)

ui_old = '<div class="canvasWrap"><canvas id="divChart"></canvas></div><div class="hover" id="divHover">移动鼠标 / 触摸曲线查看背离状态。</div>'
ui_new = '''<div class="canvasWrap"><canvas id="divChart"></canvas></div>
<div class="historyViewportBar" id="divViewportBar"><button type="button" onclick="zoomDivAt(0.75,0.5)">＋ 放大</button><button type="button" onclick="zoomDivAt(1.33,0.5)">－ 缩小</button><button type="button" onclick="resetDivViewport()">默认</button><button type="button" onclick="showAllDiv()">全范围</button><span class="historyWindowLabel" id="divWindowLabel"></span></div>
<div class="historyGestureHint">单指 / 鼠标左右拖动查看历史 · 双指 / 滚轮缩放；缩放范围已限制，不会无限放大或缩小。</div>
<div class="hover" id="divHover">移动鼠标查看当前窗口背离状态。</div>'''
if 'id="divWindowLabel"' not in html:
    if ui_old not in html:
        raise SystemExit('divergence chart UI anchor not found')
    html = html.replace(ui_old, ui_new, 1)

state_anchor = "const HISTORY_VIEW={start:0,end:0,key:'',dragging:false};"
state_add = "\nlet DIV_ALL=[];\nconst DIV_VIEW={start:0,end:0,key:'',dragging:false};"
if 'const DIV_VIEW=' not in html:
    if state_anchor not in html:
        raise SystemExit('history view state anchor not found')
    html = html.replace(state_anchor, state_anchor + state_add, 1)

replacement = r'''function divMinPoints(){return 20}
function divDefaultSpan(len){return Math.min(len,Math.max(divMinPoints(),504))}
function clampDivWindow(start,span){const len=DIV_ALL.length,min=Math.min(len,divMinPoints());span=Math.max(min,Math.min(len,Math.round(span||len)));start=Math.round(start||0);start=Math.max(0,Math.min(Math.max(0,len-span),start));return [start,start+span]}
function resetDivViewport(){if(!DIV_ALL.length)return;const span=divDefaultSpan(DIV_ALL.length);DIV_VIEW.start=Math.max(0,DIV_ALL.length-span);DIV_VIEW.end=DIV_ALL.length;renderDivergence()}
function showAllDiv(){if(!DIV_ALL.length)return;DIV_VIEW.start=0;DIV_VIEW.end=DIV_ALL.length;renderDivergence()}
function zoomDivAt(factor,ratio=0.5){if(!DIV_ALL.length)return;const start=DIV_VIEW.start,end=DIV_VIEW.end,span=Math.max(1,end-start),r=Math.max(0,Math.min(1,ratio)),anchor=start+span*r,newSpan=Math.max(divMinPoints(),Math.min(DIV_ALL.length,Math.round(span*factor))),newStart=Math.round(anchor-newSpan*r),[s,e]=clampDivWindow(newStart,newSpan);DIV_VIEW.start=s;DIV_VIEW.end=e;renderDivergence()}
function panDivTo(start){if(!DIV_ALL.length)return;const span=DIV_VIEW.end-DIV_VIEW.start,[s,e]=clampDivWindow(start,span);DIV_VIEW.start=s;DIV_VIEW.end=e;renderDivergence()}
function renderDivergence(){let all=buildDiv(),start=$('#divStart').value,end=$('#divEnd').value;all=all.filter(r=>r.date>=start&&r.date<=end);DIV_ALL=all;const sourceKey=start+'|'+end+'|'+$('#divSent').value+'|'+$('#divIndex').value+'|'+$('#divWindow').value;if(sourceKey!==DIV_VIEW.key){DIV_VIEW.key=sourceKey;const span=divDefaultSpan(all.length);DIV_VIEW.start=Math.max(0,all.length-span);DIV_VIEW.end=all.length}const {c,ctx,w,h}=setupCanvas('#divChart');ctx.clearRect(0,0,w,h);if(!all.length){ctx.fillStyle='#91a8ca';ctx.font='20px system-ui';ctx.fillText('所选区间数据不足',30,40);DIV_POINTS=[];return}const [vs,ve]=clampDivWindow(DIV_VIEW.start,DIV_VIEW.end-DIV_VIEW.start);DIV_VIEW.start=vs;DIV_VIEW.end=ve;let s=all.slice(vs,ve),good=s.filter(r=>Number.isFinite(r.sentDelta)&&Number.isFinite(r.indexRet)),latest=[...good].reverse()[0],stats=$('#divStats');stats.innerHTML='';const cards=latest?[[labels[$('#divSent').value]+' '+$('#divWindow').value+'D方向变化',(latest.sentDelta>0?'+':'')+fmt(latest.sentDelta),cls(latest.sentDelta)],[idxLabels[$('#divIndex').value]+' '+$('#divWindow').value+'D涨跌',pct(latest.indexRet),cls(latest.indexRet)],['当前关系',latest.divState,latest.divKind==='top'?'neg':latest.divKind==='bottom'?'pos':'flat'],['背离强度',fmt(latest.divStrength)+'/100','flat'],['窗口背离占比',good.length?fmt(100*good.filter(x=>x.divKind==='top'||x.divKind==='bottom').length/good.length)+'%':'—','flat']]:[];cards.forEach(v=>{const d=document.createElement('div');d.className='stat';d.innerHTML='<small>'+v[0]+'</small><b class="'+v[2]+'">'+v[1]+'</b>';stats.appendChild(d)});const label=$('#divWindowLabel');if(label)label.textContent=s.length?s[0].date+' → '+s[s.length-1].date+' · '+s.length+' 点':'';if(good.length<2){ctx.fillStyle='#91a8ca';ctx.font='20px system-ui';ctx.fillText('当前视窗数据不足',30,40);DIV_POINTS=[];return}const pad={l:62,r:28,t:22,b:38},pw=w-pad.l-pad.r,ph=h-pad.t-pad.b,lim=Math.max(5,Math.ceil(Math.max(...good.flatMap(x=>[Math.abs(x.sentDelta),Math.abs(x.indexRet)]))/5)*5),x=i=>pad.l+i/Math.max(1,good.length-1)*pw,y=v=>pad.t+(lim-v)/(2*lim)*ph;ctx.font='20px system-ui';[-lim,-lim/2,0,lim/2,lim].forEach(v=>{ctx.fillStyle='#728aaa';ctx.fillText(fmt(v),8,y(v)+6);ctx.strokeStyle='#20344f';ctx.beginPath();ctx.moveTo(pad.l,y(v));ctx.lineTo(w-pad.r,y(v));ctx.stroke()});const pts=good.map((r,i)=>({...r,x:x(i)}));line(ctx,pts,'sentDelta','#eef5ff',y,4);line(ctx,pts,'indexRet','#79a9ff',y,3);pts.forEach(p=>{if(p.divKind==='top'||p.divKind==='bottom'){ctx.fillStyle=p.divKind==='top'?'#ff738b':'#61dfb2';ctx.globalAlpha=.18;ctx.fillRect(p.x-2,pad.t,4,ph);ctx.globalAlpha=1}});ctx.fillStyle='#728aaa';for(let i=0;i<=5;i++){const j=Math.min(pts.length-1,Math.round(i*(pts.length-1)/5));ctx.fillText(pts[j].date,Math.max(0,pts[j].x-46),h-10)}DIV_POINTS=pts}
function divPointer(ev){if(!DIV_POINTS.length||DIV_VIEW.dragging)return;const c=$('#divChart'),r=c.getBoundingClientRect(),px=((ev.touches?ev.touches[0].clientX:ev.clientX)-r.left)*c.width/r.width;let best=DIV_POINTS[0],dist=Infinity;DIV_POINTS.forEach(p=>{const d=Math.abs(p.x-px);if(d<dist){dist=d;best=p}});$('#divHover').textContent=best.date+' · 情绪方向变化 '+(best.sentDelta>0?'+':'')+fmt(best.sentDelta)+' · 指数 '+pct(best.indexRet)+' · '+best.divState+' · 强度 '+fmt(best.divStrength)}
function installDivergencePanZoom(){const c=$('#divChart');if(!c||c.dataset.panzoomInstalled)return;c.dataset.panzoomInstalled='1';let mouseBase=null,touchBase=null,pinchBase=null;const width=()=>Math.max(1,c.getBoundingClientRect().width);c.addEventListener('wheel',e=>{if(!DIV_ALL.length)return;e.preventDefault();const r=c.getBoundingClientRect(),ratio=(e.clientX-r.left)/Math.max(1,r.width);zoomDivAt(e.deltaY>0?1.18:0.84,ratio)},{passive:false});c.addEventListener('mousedown',e=>{if(e.button!==0||!DIV_ALL.length)return;DIV_VIEW.dragging=true;c.classList.add('dragging');mouseBase={x:e.clientX,start:DIV_VIEW.start,span:DIV_VIEW.end-DIV_VIEW.start}});window.addEventListener('mousemove',e=>{if(!mouseBase)return;const dx=e.clientX-mouseBase.x,shift=Math.round(-dx/width()*mouseBase.span);panDivTo(mouseBase.start+shift)});window.addEventListener('mouseup',()=>{mouseBase=null;DIV_VIEW.dragging=false;c.classList.remove('dragging')});c.addEventListener('mousemove',divPointer);c.addEventListener('touchstart',e=>{if(!DIV_ALL.length)return;if(e.touches.length===1){DIV_VIEW.dragging=true;touchBase={x:e.touches[0].clientX,start:DIV_VIEW.start,span:DIV_VIEW.end-DIV_VIEW.start};pinchBase=null}else if(e.touches.length>=2){const a=e.touches[0],b=e.touches[1],dist=Math.hypot(a.clientX-b.clientX,a.clientY-b.clientY),r=c.getBoundingClientRect(),mid=(a.clientX+b.clientX)/2;pinchBase={dist:Math.max(1,dist),span:DIV_VIEW.end-DIV_VIEW.start,anchor:DIV_VIEW.start+(DIV_VIEW.end-DIV_VIEW.start)*((mid-r.left)/Math.max(1,r.width))};touchBase=null}}, {passive:true});c.addEventListener('touchmove',e=>{if(!DIV_ALL.length)return;e.preventDefault();if(e.touches.length===1&&touchBase){const dx=e.touches[0].clientX-touchBase.x,shift=Math.round(-dx/width()*touchBase.span);panDivTo(touchBase.start+shift)}else if(e.touches.length>=2&&pinchBase){const a=e.touches[0],b=e.touches[1],dist=Math.max(1,Math.hypot(a.clientX-b.clientX,a.clientY-b.clientY)),r=c.getBoundingClientRect(),mid=(a.clientX+b.clientX)/2,ratio=Math.max(0,Math.min(1,(mid-r.left)/Math.max(1,r.width))),newSpan=Math.max(divMinPoints(),Math.min(DIV_ALL.length,Math.round(pinchBase.span*pinchBase.dist/dist))),newStart=Math.round(pinchBase.anchor-newSpan*ratio),[s,en]=clampDivWindow(newStart,newSpan);DIV_VIEW.start=s;DIV_VIEW.end=en;renderDivergence()}},{passive:false});c.addEventListener('touchend',()=>{touchBase=null;pinchBase=null;DIV_VIEW.dragging=false})}
function renderEuphoria'''

if 'function installDivergencePanZoom()' not in html:
    pattern = r"function renderDivergence\(\)\{.*?\}\nfunction divPointer\(ev\)\{.*?\}\nfunction renderEuphoria"
    html2, n = re.subn(pattern, replacement, html, count=1, flags=re.S)
    if n != 1:
        raise SystemExit(f'divergence function block replace failed: {n}')
    html = html2

old_event = "$('#divChart').addEventListener('mousemove',divPointer);"
if old_event in html:
    html = html.replace(old_event, 'installDivergencePanZoom();', 1)
elif 'installDivergencePanZoom();' not in html:
    # Put installer next to the already-installed history/index chart installers.
    anchor = 'installHistoryPanZoom();installIndexReturnPanZoom();'
    if anchor not in html:
        raise SystemExit('divergence event install anchor not found')
    html = html.replace(anchor, anchor + 'installDivergencePanZoom();', 1)

# Remove any legacy touch handler for divChart if it exists.
html = re.sub(r"\$\('#divChart'\)\.addEventListener\('touchmove'.*?\);", "", html, flags=re.S)

p.write_text(html, encoding='utf-8')
print('sentiment divergence bounded pan/zoom installed')
