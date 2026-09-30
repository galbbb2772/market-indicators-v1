import shutil,tempfile,unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

class ResearchTerminalV2Tests(unittest.TestCase):
    def test_assets_are_presentation_only_and_have_expected_controls(self):
        js=(ROOT/'docs/research-terminal-v2.js').read_text(encoding='utf-8')
        css=(ROOT/'docs/research-terminal-v2.css').read_text(encoding='utf-8')
        for token in ('快速区间','rtCrosshair','rtBoxDetail','rtSourceMatrix','Walk-forward'):
            self.assertIn(token,js)
        for token in ('.rt-topbar','.rt-status-strip','.rt-score-grid','@media(max-width:560px)'):
            self.assertIn(token,css)
        # UI enhancement must not synthesize market datasets or run trades/backtests.
        for forbidden in ('Math.random','fetch("https://','fetch(\'https://','submitOrder','place_order','backtest('):
            self.assertNotIn(forbidden,js)

    def test_patch_is_idempotent_in_disposable_copy(self):
        from patch_research_terminal_v2 import CSS,JS,PAGES
        with tempfile.TemporaryDirectory() as tmp:
            docs=Path(tmp)/'docs';docs.mkdir()
            for page in PAGES:
                shutil.copy(ROOT/'docs'/page,docs/page)
            def apply(path):
                text=path.read_text(encoding='utf-8')
                if 'research-terminal-v2-css' not in text:
                    text=text.replace('</head>',CSS+'</head>',1)
                if 'research-terminal-v2-js' not in text:
                    text=text.replace('</body>',JS+'</body>',1)
                path.write_text(text,encoding='utf-8')
            for page in PAGES:
                p=docs/page;apply(p);apply(p);text=p.read_text(encoding='utf-8')
                self.assertEqual(text.count('research-terminal-v2-css'),1)
                self.assertEqual(text.count('research-terminal-v2-js'),1)

if __name__=='__main__':unittest.main()
