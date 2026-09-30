"""Install shared research-terminal V2 assets into research-only pages.

This is presentation-only: no data fetch, backtest, signal change or deployment.
Safe to run repeatedly in disposable preview / explicitly approved deployment.
"""
from pathlib import Path

ROOT=Path(__file__).resolve().parent/'docs'
PAGES=('research-hub.html','structure-lab.html','cycle-lab.html')
CSS='<link rel="stylesheet" href="./research-terminal-v2.css"><!-- research-terminal-v2-css -->'
JS='<script src="./research-terminal-v2.js"></script><!-- research-terminal-v2-js -->'


def patch(name:str)->None:
    path=ROOT/name
    text=path.read_text(encoding='utf-8')
    changed=False
    if 'research-terminal-v2-css' not in text:
        if '</head>' not in text:raise RuntimeError(f'{name}: missing </head>')
        text=text.replace('</head>',CSS+'</head>',1);changed=True
    if 'research-terminal-v2-js' not in text:
        if '</body>' not in text:raise RuntimeError(f'{name}: missing </body>')
        text=text.replace('</body>',JS+'</body>',1);changed=True
    if changed:
        path.write_text(text,encoding='utf-8')
        print('Installed terminal V2:',name)
    else:
        print('Terminal V2 already installed:',name)


def main()->None:
    for page in PAGES:patch(page)

if __name__=='__main__':main()
