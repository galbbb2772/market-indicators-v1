from pathlib import Path

p = Path('docs/index.html')
s = p.read_text(encoding='utf-8')

# 1) Add the new tab.
if 'id="tabDivergence"' not in s:
    old = '<div class="tabs"><button class="tab active" id="tabOverall" onclick="switchTab(\'overall\')">市场综合</button><button class="tab" id="tabHistory" onclick="switchTab(\'history\')">历史探索</button><button class="tab" id="tabVariables" onclick="switchTab(\'variables\')">变量贡献</button>'
    new = '<div class="tabs"><button class="tab active" id="tabOverall" onclick="switchTab(\'overall\')">市场综合</button><button class="tab" id="tabHistory" onclick="switchTab(\'history\')">历史探索</button><button class="tab" id="tabDivergence" onclick="switchTab(\'divergence\')">背离 / 领先性</button><button class="tab" id="tabVariables" onclick="switchTab(\'variables\')">变量贡献</button>'
    if old not in s:
        raise SystemExit('tab anchor not found')
    s = s.replace(old, new, 1)

# 2) Add divergence page before variable contribution page.
if 'id="divergenceView"' not in s:
    anchor = '<section id="variablesView" class="hidden">'
    block = r'''
<section id="divergenceView" class="hidden">
<div class="historyWrap">
<h3>模型—市场背离 / 领先性</h3>
<div class="note">这里观察“底层市场状态”和“指数价格”是否暂时走向相反方向。模型下降而指数上涨 = 顶部风险背离；模型上升而指数下跌 = 底部修复背离。背离不是见顶/见底确认，而是价格尚未完全承认底层环境变化的观察信号。</div>
<div class="controls">
<label class="tiny">指数<br><select id="divIndex" onchange="renderDivergence()"><option value="sp500">S&P 500</option><option value="nasdaq">Nasdaq Composite</option><option value="dow">Dow Jones</option></select></label>
<label class="tiny">观察窗口<br><select id="divWindow" onchange="renderDivergence()"><option value="5">5个交易日</option><option value="10">10个交易日</option><option value="20" selected>20个交易日</option></select></label>
<label class="tiny">图表区间<br><select id="divRange" onchange="renderDivergence()"><option value="1y">1年</option><option value="3y" selected>3年</option><option value="5y">5年</option><option value="all">全部</option></select></label>
</div>
<div class="histStats" id="divSummary"></div>
<div class="legend"><span style="--legend:#eef5ff">模型变化 ΔScore</span><span style="--legend:#79a9ff">指数同期涨跌 %</span></div>
<div class="axisNote"><span>同一日期比较滚动窗口变化</span><span>背离强度按历史同类背离的标准化幅度百分位</span></div>
<div class="historyCanvasWrap"><canvas id="divergenceChart"></canvas></div>
<div class="hoverReadout" id="divHover">移动鼠标或触摸曲线查看该日的模型变化、指数变化和背离类型。</div>
</div>

<div class="panel"><h3>三大指数当前背离矩阵</h3><div class="tableWrap"><table class="tbl"><thead><tr><th>指数</th><th>5D</th><th>5D强度</th><th>10D</th><th>10D强度</th><th>20D</th><th>20D强度</th></tr></thead><tbody id="divMatrix"></tbody></table></div></div>

<div class="panel" style="margin-top:12px"><h3>Lead / Lag · 模型可能领先价格多少交易日</h3><div class="note">用“模型5日变化”与“指数5日收益率向后平移后的窗口”计算 Pearson 相关。正的 lag 表示价格窗口发生在模型之后。这里只找统计同步/领先关系，不直接视为预测能力。</div><div class="tableWrap"><table class="tbl"><thead><tr><th>指数</th><th>0D</th><th>1D</th><th>3D</th><th>5D</th><th>10D</th><th>15D</th><th>20D</th><th>最强关系</th></tr></thead><tbody id="leadLagBody"></tbody></table></div></div>

<div class="panel" style="margin-top:12px"><h3>拐点领先观察 · Exploratory</h3><div class="note">从历史曲线识别局部峰值/谷值，观察模型拐点后 1–20 个交易日内是否出现指数对应拐点。这个统计容易受参数和样本选择影响，所以只作为研究观察，不作为实盘规则。</div><div class="indexGrid" id="turningPointGrid"></div></div>
</section>

'''
    if anchor not in s:
        raise SystemExit('variables anchor not found')
    s = s.replace(anchor, block + anchor, 1)

# 3) Expand tab switching logic.
old_switch = "function switchTab(which){['overall','history','variables'].forEach(x=>{document.querySelector('#'+x+'View').classList.toggle('hidden',x!==which);document.querySelector('#tab'+x[0].toUpperCase()+x.slice(1)).classList.toggle('active',x===which)});if(which==='history')renderHistoryExplorer();if(which==='variables')renderVariableTable()}"
new_switch = "function switchTab(which){['overall','history','divergence','variables'].forEach(x=>{document.querySelector('#'+x+'View').classList.toggle('hidden',x!==which);document.querySelector('#tab'+x[0].toUpperCase()+x.slice(1)).classList.toggle('active',x===which)});if(which==='history')renderHistoryExplorer();if(which==='divergence')renderDivergence();if(which==='variables')renderVariableTable()}"
if old_switch in s:
    s = s.replace(old_switch, new_switch, 1)
elif "['overall','history','divergence','variables']" not in s:
    raise SystemExit('switchTab anchor not found')

# 4) Add divergence analytics JS before card filtering logic.
if 'function renderDivergence()' not in s:
    anchor = 'function filtered(){'
    js = r'''
const DIV_INDEX_LABELS={sp500:'S&P 500',nasdaq:'Nasdaq Composite',dow:'Dow Jones'};
let DIV_POINTS=[];
function mean(a){const v=a.filter(Number.isFinite);return v.length?v.reduce((s,x)=>s+x,0)/v.length:null}
function std(a){const v=a.filter(Number.isFinite),m=mean(v);if(v.length<2||m==null)return null;return Math.sqrt(v.reduce((s,x)=>s+(x-m)*(x-m),0)/(v.length-1))}
function percentileRank(vals,x){const v=vals.filter(Number.isFinite).sort((a,b)=>a-b);if(!v.length||!Number.isFinite(x))return null;let n=0;for(const z of v)if(z<=x)n++;return 100*n/v.length}
function divergenceSeries(rows,key,w){
 const ds=[],rr=[];
 for(let i=0;i<rows.length;i++){
   if(i<w||!Number.isFinite(rows[i].score)||!Number.isFinite(rows[i-w].score)||!Number.isFinite(rows[i][key])||!Number.isFinite(rows[i-w][key])){ds.push(null);rr.push(null);continue}
   ds.push(rows[i].score-rows[i-w].score);rr.push((rows[i][key]/rows[i-w][key]-1)*100)
 }
 const sdS=std(ds),sdR=std(rr),magnitudes=[];
 for(let i=0;i<rows.length;i++)if(Number.isFinite(ds[i])&&Number.isFinite(rr[i])&&ds[i]*rr[i]<0&&sdS&&sdR)magnitudes.push(Math.abs(ds[i]/sdS)+Math.abs(rr[i]/sdR));
 return rows.map((r,i)=>{
   const a=ds[i],b=rr[i];let state='数据不足',kind='na',mag=null,strength=null;
   if(Number.isFinite(a)&&Number.isFinite(b)){
     if(a<0&&b>0){state='顶部风险背离';kind='top_divergence'}
     else if(a>0&&b<0){state='底部修复背离';kind='bottom_divergence'}
     else if(a>=0&&b>=0){state='上涨确认';kind='up_confirm'}
     else if(a<=0&&b<=0){state='下跌确认';kind='down_confirm'}
     else{state='中性';kind='neutral'}
     if(a*b<0&&sdS&&sdR){mag=Math.abs(a/sdS)+Math.abs(b/sdR);strength=percentileRank(magnitudes,mag)} else strength=0;
   }
   return {...r,scoreDelta:a,indexRet:b,divState:state,divKind:kind,divStrength:strength}
 })
}
function divergenceClass(x){return x?.divKind==='top_divergence'?'neg':x?.divKind==='bottom_divergence'?'pos':'flat'}
function renderDivSummary(series,key,w){const root=document.querySelector('#divSummary'),x=[...series].reverse().find(z=>Number.isFinite(z.scoreDelta)&&Number.isFinite(z.indexRet));root.innerHTML='';if(!x)return;
 const cards=[['模型 '+w+'D 变化',(x.scoreDelta>0?'+':'')+fmt(x.scoreDelta),cls(x.scoreDelta)],[(DIV_INDEX_LABELS[key]||key)+' '+w+'D 涨跌',pct(x.indexRet),cls(x.indexRet)],['当前关系',x.divState,divergenceClass(x)],['背离强度',x.divStrength==null?'—':fmt(x.divStrength)+'/100',divergenceClass(x)]];
 cards.forEach(v=>{const d=document.createElement('div');d.className='histStat';d.innerHTML='<small>'+v[0]+'</small><b class="'+v[2]+'">'+v[1]+'</b>';root.appendChild(d)})
}
function renderDivMatrix(rows){const body=document.querySelector('#divMatrix');body.innerHTML='';[['sp500','S&P 500'],['nasdaq','Nasdaq'],['dow','Dow Jones']].forEach(([k,n])=>{const tr=document.createElement('tr'),cells=[];[5,10,20].forEach(w=>{const s=divergenceSeries(rows,k,w),x=[...s].reverse().find(z=>Number.isFinite(z.scoreDelta)&&Number.isFinite(z.indexRet));cells.push(x||{})});tr.innerHTML='<td>'+n+'</td>'+cells.map(x=>'<td class="'+divergenceClass(x)+'">'+(x.divState||'—')+'</td><td>'+((x.divStrength==null)?'—':fmt(x.divStrength))+'</td>').join('');body.appendChild(tr)})}
function leadLagStats(rows,key){const score5=[],ret5=[];for(let i=0;i<rows.length;i++){score5[i]=i>=5&&Number.isFinite(rows[i].score)&&Number.isFinite(rows[i-5].score)?rows[i].score-rows[i-5].score:null;ret5[i]=i>=5&&Number.isFinite(rows[i][key])&&Number.isFinite(rows[i-5][key])?(rows[i][key]/rows[i-5][key]-1)*100:null}const lags=[0,1,3,5,10,15,20],vals={};lags.forEach(l=>{const a=[],b=[];for(let i=5;i<rows.length-l;i++){a.push(score5[i]);b.push(ret5[i+l])}vals[l]=corr(a,b)});let best=null;lags.forEach(l=>{const v=vals[l];if(Number.isFinite(v)&&(!best||Math.abs(v)>Math.abs(best.corr)))best={lag:l,corr:v}});return {lags,vals,best}}
function renderLeadLag(rows){const body=document.querySelector('#leadLagBody');body.innerHTML='';[['sp500','S&P 500'],['nasdaq','Nasdaq'],['dow','Dow Jones']].forEach(([k,n])=>{const r=leadLagStats(rows,k),tr=document.createElement('tr');tr.innerHTML='<td>'+n+'</td>'+r.lags.map(l=>'<td>'+fmt(r.vals[l])+'</td>').join('')+'<td>'+(r.best?('+'+r.best.lag+'D · r='+fmt(r.best.corr)):'—')+'</td>';body.appendChild(tr)})}
function localTurning(rows,key,type,radius=5){const out=[];for(let i=radius;i<rows.length-radius;i++){const v=Number(rows[i][key]);if(!Number.isFinite(v))continue;let ok=true;for(let j=i-radius;j<=i+radius;j++){if(j===i)continue;const z=Number(rows[j][key]);if(!Number.isFinite(z))continue;if(type==='peak'&&z>v){ok=false;break}if(type==='trough'&&z<v){ok=false;break}}if(ok)out.push(i)}return out}
function turningLead(rows,key,type){const sIdx=localTurning(rows,'score',type,5).filter(i=>type==='peak'?rows[i].score>=55:rows[i].score<=55),pIdx=localTurning(rows,key,type,5),lags=[];for(const i of sIdx){const j=pIdx.find(x=>x>i&&x<=i+20);if(j!=null)lags.push(j-i)}if(!lags.length)return {n:0,median:null,mean:null};const sorted=[...lags].sort((a,b)=>a-b),med=sorted.length%2?sorted[(sorted.length-1)/2]:(sorted[sorted.length/2-1]+sorted[sorted.length/2])/2;return {n:lags.length,median:med,mean:mean(lags)}}
function renderTurningPoints(rows){const root=document.querySelector('#turningPointGrid');root.innerHTML='';[['sp500','S&P 500'],['nasdaq','Nasdaq'],['dow','Dow Jones']].forEach(([k,n])=>{const pk=turningLead(rows,k,'peak'),tr=turningLead(rows,k,'trough'),d=document.createElement('div');d.className='indexCard';d.innerHTML='<small>'+n+'</small><b>顶部领先 '+(pk.median==null?'—':fmt(pk.median)+'D')+'</b><div class="tiny">顶部匹配 '+pk.n+' 次 · 平均 '+(pk.mean==null?'—':fmt(pk.mean)+'D')+'</div><div class="chg flat">底部领先 '+(tr.median==null?'—':fmt(tr.median)+'D')+'</div><div class="tiny">底部匹配 '+tr.n+' 次 · 平均 '+(tr.mean==null?'—':fmt(tr.mean)+'D')+'</div>';root.appendChild(d)})}
function drawDivergence(series){const c=document.querySelector('#divergenceChart'),ctx=c.getContext('2d'),w=c.width=Math.max(700,c.clientWidth*2),h=c.height=720;ctx.clearRect(0,0,w,h);const pts=series.filter(x=>Number.isFinite(x.scoreDelta)&&Number.isFinite(x.indexRet));if(pts.length<2){ctx.fillStyle='#91a8ca';ctx.fillText('数据不足',30,40);return}const pad={l:62,r:62,t:24,b:36},pw=w-pad.l-pad.r,ph=h-pad.t-pad.b;const maxAbs=Math.max(5,...pts.flatMap(x=>[Math.abs(x.scoreDelta),Math.abs(x.indexRet)])),lim=Math.ceil(maxAbs/5)*5,x=i=>pad.l+i/(pts.length-1)*pw,y=v=>pad.t+(lim-v)/(lim*2)*ph;ctx.strokeStyle='#20344f';ctx.beginPath();ctx.moveTo(pad.l,y(0));ctx.lineTo(w-pad.r,y(0));ctx.stroke();ctx.fillStyle='#728aaa';[-lim,-lim/2,0,lim/2,lim].forEach(v=>ctx.fillText((v>0?'+':'')+fmt(v),8,y(v)+6));const draw=(key,color,width)=>{ctx.strokeStyle=color;ctx.lineWidth=width;ctx.beginPath();pts.forEach((p,i)=>{i?ctx.lineTo(x(i),y(p[key])):ctx.moveTo(x(i),y(p[key]))});ctx.stroke()};draw('scoreDelta','#eef5ff',4);draw('indexRet','#79a9ff',3);for(let i=0;i<pts.length;i++){if(pts[i].divKind==='top_divergence'||pts[i].divKind==='bottom_divergence'){ctx.fillStyle=pts[i].divKind==='top_divergence'?'#ff738b':'#61dfb2';ctx.globalAlpha=.18;ctx.fillRect(x(i)-2,pad.t,4,ph);ctx.globalAlpha=1}}ctx.fillStyle='#728aaa';for(let i=0;i<=5;i++){const ix=Math.min(pts.length-1,Math.round(i*(pts.length-1)/5));ctx.fillText(pts[ix].date.slice(0,10),Math.max(0,x(ix)-46),h-10)}DIV_POINTS=pts.map((p,i)=>({...p,_x:x(i)}))}
function renderDivergence(){const rows=buildHistoryRows();if(!rows.length)return;const key=document.querySelector('#divIndex')?.value||'sp500',w=Number(document.querySelector('#divWindow')?.value||20),range=document.querySelector('#divRange')?.value||'3y';let series=divergenceSeries(rows,key,w);if(range!=='all'){const years=Number(range[0]),end=new Date(rows[rows.length-1].date+'T00:00:00'),start=new Date(end);start.setFullYear(start.getFullYear()-years);series=series.filter(x=>x.date>=start.toISOString().slice(0,10))}renderDivSummary(series,key,w);renderDivMatrix(rows);renderLeadLag(rows);renderTurningPoints(rows);drawDivergence(series)}
function handleDivPointer(ev){if(!DIV_POINTS.length)return;const c=document.querySelector('#divergenceChart'),r=c.getBoundingClientRect(),px=(ev.touches?ev.touches[0].clientX:ev.clientX)-r.left,scale=c.width/r.width,xp=px*scale;let best=DIV_POINTS[0],dist=Infinity;DIV_POINTS.forEach(p=>{const d=Math.abs(p._x-xp);if(d<dist){dist=d;best=p}});document.querySelector('#divHover').textContent=best.date+' · ΔScore '+(best.scoreDelta>0?'+':'')+fmt(best.scoreDelta)+' · 指数 '+pct(best.indexRet)+' · '+best.divState+' · 强度 '+fmt(best.divStrength)}
'''
    if anchor not in s:
        raise SystemExit('JS anchor not found')
    s = s.replace(anchor, js + '\n' + anchor, 1)

# 5) Bind pointer interaction to the divergence chart.
if "#divergenceChart').addEventListener('mousemove'" not in s:
    anchor = "document.querySelector('#historyChart').addEventListener('mousemove',handleHistoryPointer);"
    add = "document.querySelector('#divergenceChart').addEventListener('mousemove',handleDivPointer);document.querySelector('#divergenceChart').addEventListener('touchmove',e=>{handleDivPointer(e);e.preventDefault()},{passive:false});"
    if anchor not in s:
        raise SystemExit('event anchor not found')
    s = s.replace(anchor, anchor + add, 1)

p.write_text(s, encoding='utf-8')
print('divergence UI patched')
