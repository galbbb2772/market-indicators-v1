"""Idempotently integrate Research Hub navigation into existing approved site.

Only called by deployment after BOTH explicit website authorization and
verified rights to the research site's publicly published datasets.
Does not fetch market data, execute any backtests, or deploy anything.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parent / 'docs'

def patch(name: str, needle: str, addition: str) -> None:
    path = ROOT / name
    s = path.read_text(encoding='utf-8')
    if addition not in s:
        if needle not in s:
            raise RuntimeError(f'Navigation insertion anchor changed: {name}')
        s = s.replace(needle, needle + addition, 1)
        path.write_text(s, encoding='utf-8')
        print('Installed research hub link:', name)
    else:
        print('Research hub link already installed:', name)


def main() -> None:
    link = '　<a href="./research-hub.html">研究总览 →</a>'
    patch('structure-lab.html',
          '<a href="./index.html">← 返回原市场指标网站</a>', link)
    patch('cycle-lab.html',
          '<a href="./index.html">市场主站</a>', link)
    # Add one unobtrusive entry point to the current approved V2 dashboard;
    # never clobber existing dashboard HTML, scripts or indicator sections.
    idx = ROOT / 'index.html'
    html = idx.read_text(encoding='utf-8')
    marker = '<!-- research-hub-nav: approved deployment only -->'
    if marker not in html:
        anchor = '</body>'
        if anchor not in html:
            raise RuntimeError('main index missing closing body')
        widget = (marker + '<a href="./research-hub.html" '
                  'style="position:fixed;z-index:9999;right:16px;bottom:16px;'
                  'background:#16394c;color:#e0fff7;border:1px solid #6ad6c2;'
                  'padding:12px 17px;border-radius:99px;font:600 13px system-ui;'
                  'box-shadow:0 4px 18px #071c2f;text-decoration:none" '
                  'aria-label="打开市场结构研究总览">市场结构研究 →</a>')
        idx.write_text(html.replace(anchor, widget + anchor, 1), encoding='utf-8')
        print('Installed approved-only link to research hub in V2 home')
    else:
        print('Main dashboard research hub link already present')
    # The boxes/sector/distribution/macro pages share one HTML document.
    # Deep links must select the requested tab rather than showing the default.
    page = ROOT / 'structure-lab.html'
    html = page.read_text(encoding='utf-8')
    route_marker = '<!-- research-hub-deeplink -->'
    if route_marker not in html:
        route = (route_marker + '<script>(function(){'
                 'function go(){let name=location.hash.slice(1);'
                 'if(!/^(boxes|dist|sector|macro)$/.test(name))return;'
                 'let b=document.querySelector(".tabs button[data-tab=\\\""+name+"\\\"]");'
                 'if(!b)return;let status=document.getElementById("status");'
                 'if(status&&status.textContent.includes("正在读取")){'
                 'let o=new MutationObserver(function(){'
                 'if(!status.textContent.includes("正在读取")){o.disconnect();b.click()}});'
                 'o.observe(status,{childList:true,characterData:true,subtree:true});'
                 '}else{b.click()}}'
                 'window.addEventListener("hashchange",go);go()'
                 '})();</script>')
        if '</body>' not in html:
            raise RuntimeError('structure page missing closing body')
        page.write_text(html.replace('</body>', route + '</body>', 1), encoding='utf-8')
        print('Installed deep-link tab routing')
    else:
        print('Deep-link tab routing already present')

if __name__ == '__main__':
    main()
