from pathlib import Path

p=Path('docs/index.html')
s=p.read_text(encoding='utf-8')

if '已形成年龄' in s:
    print('box formed-age UI already present')
    raise SystemExit(0)

needle="<div class=\"boxLine\"><span>当前估计年龄</span><b>'+(b.box_age_estimate_trading_days||0)+' 天</b></div>"
if needle not in s:
    raise SystemExit('range-box age row not found')

formed="<div class=\"boxLine\"><span>已形成年龄</span><b>'+((b.formed)?Math.max(1,(b.box_age_estimate_trading_days||0)-(b.window_days||0)+1):0)+' 交易日</b></div>"
estimate=needle.replace('当前估计年龄','结构年龄估计')
s=s.replace(needle,formed+estimate,1)
p.write_text(s,encoding='utf-8')
print('added exact formed-age row and renamed estimated structural age')
