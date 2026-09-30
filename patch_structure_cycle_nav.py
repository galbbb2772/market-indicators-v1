"""Idempotent navigation patch; does not trigger website deployment."""
from pathlib import Path
path=Path('docs/structure-lab.html')
s=path.read_text(encoding='utf-8')
link='<a href="./cycle-lab.html">周期性与预测能力图表 →</a>'
if link not in s:
    needle='<a href="./index.html">← 返回原市场指标网站</a>'
    if needle not in s:raise RuntimeError('structure page navigation anchor not found')
    s=s.replace(needle,needle+'　'+link,1)
    path.write_text(s,encoding='utf-8')
    print('Added cycle-research link')
else:print('Cycle-research link already present')
