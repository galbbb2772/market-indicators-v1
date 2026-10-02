from pathlib import Path

p = Path(__file__).resolve().parent / "docs" / "sentiment.html"
html = p.read_text(encoding="utf-8")

MARKER = "/* SENTIMENT_PERF_V1 */"
if MARKER not in html:
    html = html.replace("</style>", MARKER + "\n</style>", 1)

# 1) Do not reallocate the canvas backing buffer on every drag frame.
old_setup = "function setupCanvas(id){const c=$(id),w=c.width=Math.max(760,c.clientWidth*2),h=c.height=Math.max(640,c.clientHeight*2);return {c,ctx:c.getContext('2d'),w,h}}"
new_setup = "function setupCanvas(id){const c=$(id),w=Math.max(760,Math.round(c.clientWidth*2)),h=Math.max(640,Math.round(c.clientHeight*2));if(c.width!==w)c.width=w;if(c.height!==h)c.height=h;return {c,ctx:c.getContext('2d'),w,h}}"
if old_setup in html:
    html = html.replace(old_setup, new_setup, 1)

# 2) Cache the selected/resampled history. Panning now slices the cached array only.
old_hist = "function renderHistory(){let all=historyRows();all=resample(all,$('#histGran').value);HISTORY_ALL=all;const sourceKey=$('#histStart').value+'|'+$('#histEnd').value+'|'+$('#histGran').value;if(sourceKey!==HISTORY_VIEW.key){HISTORY_VIEW.key=sourceKey;const span=historyDefaultSpan(all.length);HISTORY_VIEW.start=Math.max(0,all.length-span);HISTORY_VIEW.end=all.length}"
new_hist = "function renderHistory(){const sourceKey=$('#histStart').value+'|'+$('#histEnd').value+'|'+$('#histGran').value;let all=HISTORY_ALL;if(sourceKey!==HISTORY_VIEW.key){all=resample(historyRows(),$('#histGran').value);HISTORY_ALL=all;HISTORY_VIEW.key=sourceKey;const span=historyDefaultSpan(all.length);HISTORY_VIEW.start=Math.max(0,all.length-span);HISTORY_VIEW.end=all.length}"
if old_hist in html:
    html = html.replace(old_hist, new_hist, 1)

# 3) Cache the expensive full-history divergence calculation. It is rebuilt only when
#    date/sentiment/index/window controls actually change, not on every finger movement.
old_div = "function renderDivergence(){let all=buildDiv(),start=$('#divStart').value,end=$('#divEnd').value;all=all.filter(r=>r.date>=start&&r.date<=end);DIV_ALL=all;const sourceKey=start+'|'+end+'|'+$('#divSent').value+'|'+$('#divIndex').value+'|'+$('#divWindow').value;if(sourceKey!==DIV_VIEW.key){DIV_VIEW.key=sourceKey;const span=divDefaultSpan(all.length);DIV_VIEW.start=Math.max(0,all.length-span);DIV_VIEW.end=all.length}"
new_div = "function renderDivergence(){const start=$('#divStart').value,end=$('#divEnd').value,sourceKey=start+'|'+end+'|'+$('#divSent').value+'|'+$('#divIndex').value+'|'+$('#divWindow').value;let all=DIV_ALL;if(sourceKey!==DIV_VIEW.key){all=buildDiv().filter(r=>r.date>=start&&r.date<=end);DIV_ALL=all;DIV_VIEW.key=sourceKey;const span=divDefaultSpan(all.length);DIV_VIEW.start=Math.max(0,all.length-span);DIV_VIEW.end=all.length}"
if old_div in html:
    html = html.replace(old_div, new_div, 1)

# 4) Mobile browser chrome can fire several resize events during initial load.
#    Coalesce them to one animation frame instead of re-rendering all charts repeatedly.
old_resize = "window.addEventListener('resize',()=>{renderHistory();renderDivergence()});"
new_resize = "let __sentimentResizeRAF=0;window.addEventListener('resize',()=>{if(__sentimentResizeRAF)return;__sentimentResizeRAF=requestAnimationFrame(()=>{__sentimentResizeRAF=0;renderHistory();renderDivergence()})});"
if old_resize in html:
    html = html.replace(old_resize, new_resize, 1)

p.write_text(html, encoding="utf-8")
print("sentiment chart performance optimizations installed")
