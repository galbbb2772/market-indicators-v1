from pathlib import Path

p = Path(__file__).resolve().parent / "docs" / "sentiment.html"
html = p.read_text(encoding="utf-8")

# Repair a dangling fragment introduced when legacy touch handlers were removed
# after the bounded pan/zoom patches were composed.
bad = "installHistoryPanZoom();installIndexReturnPanZoom();installDivergencePanZoom();e.preventDefault()},{passive:false});"
good = "installHistoryPanZoom();installIndexReturnPanZoom();installDivergencePanZoom();"
html = html.replace(bad, good)

# Keep browser cache usable. The file is refreshed by Pages deployment, so forcing
# a unique URL on every page open only makes mobile startup slower.
html = html.replace("fetch('./data/sentiment_history.json?ts='+Date.now())", "fetch('./data/sentiment_history.json')")

p.write_text(html, encoding="utf-8")
print("sentiment syntax/cache repair installed")
