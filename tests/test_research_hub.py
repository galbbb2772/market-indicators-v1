"""Static site acceptance tests; no backtest and no outbound HTTP needed."""
from html.parser import HTMLParser
from pathlib import Path
import json, unittest

ROOT = Path(__file__).resolve().parents[1]
HUB = ROOT / 'docs/research-hub.html'
NEWS = ROOT / 'docs/data/news_history.json'

class Tags(HTMLParser):
    def __init__(self):
        super().__init__(); self.anchors=[]; self.articles=[]; self.scripts=[]; self.id_values=set()
    def handle_starttag(self, tag, attrs):
        a=dict(attrs)
        if tag=='a': self.anchors.append(a.get('href',''))
        if tag=='article': self.articles.append(a)
        if a.get('id'): self.id_values.add(a['id'])
        if tag=='script': self.scripts.append(a)

class ResearchHubTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html=HUB.read_text(encoding='utf-8'); cls.tags=Tags(); cls.tags.feed(cls.html)

    def test_six_navigation_modules_and_chart_sections(self):
        self.assertEqual(len(self.tags.articles),6)
        for url in ('./index.html','./structure-lab.html',
                    './structure-lab.html#sector','./structure-lab.html#dist',
                    './structure-lab.html#macro','./cycle-lab.html','#newsPanel'):
            self.assertIn(url,self.tags.anchors)
        self.assertTrue({'newsPanel','newsChart','newsDays','dataState',
                         'coverageMessage'}.issubset(self.tags.id_values))

    def test_real_archive_only_and_explicit_missing_states(self):
        self.assertIn("fetch('./data/news_history.json'",self.html)
        self.assertIn("fetch('./data/structure_lab.json'",self.html)
        self.assertIn('没有经核准的数据文件时',self.html)
        self.assertIn('不使用样本数据伪装历史结果',self.html)
        self.assertNotIn('Math.random(',self.html)
        self.assertEqual(len(self.tags.scripts),1)
        self.assertNotIn('src',self.tags.scripts[0])

    def test_existing_archive_has_authenticated_values(self):
        content=json.loads(NEWS.read_text(encoding='utf-8'))
        rows=content.get('history') or []
        self.assertGreater(len(rows),0)
        self.assertTrue(any('reaction_adjusted' in x and 'generated_at' in x for x in rows))

if __name__=='__main__':unittest.main()
