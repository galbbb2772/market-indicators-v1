"""Add a research link after all existing UI patch scripts have run."""
from pathlib import Path

p = Path('docs/index.html')
html = p.read_text(encoding='utf-8')
if 'id="structureLabNav"' in html:
    print('Structure Lab navigation already present')
else:
    anchor = '<div class="tabs">'
    link = ('<a class="tab" id="structureLabNav" href="./structure-lab.html" '
            'style="text-decoration:none;color:#eef5ff;border-color:#416ca8">'
            '箱体与周期研究 ↗</a>')
    if anchor not in html:
        raise RuntimeError('Cannot find market dashboard tab bar')
    html = html.replace(anchor, anchor + link, 1)
    p.write_text(html, encoding='utf-8')
    print('Added Structure Lab nav to existing dashboard')
