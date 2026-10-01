from pathlib import Path

p = Path(__file__).resolve().parent / "docs" / "index.html"
html = p.read_text(encoding="utf-8")
link = '<a class="tab" href="./sentiment.html" style="text-decoration:none">情绪周期 / 狂热</a>'
if link not in html:
    marker = '<button class="tab" id="tabNews" onclick="switchTab(\'news\')">新闻信号</button>'
    if marker not in html:
        raise SystemExit("sentiment tab marker not found")
    html = html.replace(marker, marker + link, 1)
p.write_text(html, encoding="utf-8")
print("sentiment tab installed")
