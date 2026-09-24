from pathlib import Path

p = Path('docs/index.html')
s = p.read_text(encoding='utf-8')
old = "function divFutureOutcome(rows,divSeries,i,key){if(i<21||i>=rows.length-2||!Number.isFinite(rows[i]?.[key]))return null;"
new = "function divFutureOutcome(rows,divSeries,i,key){if(i<21||!Number.isFinite(rows[i]?.[key]))return null;"
if old in s:
    s = s.replace(old, new, 1)
    p.write_text(s, encoding='utf-8')
    print('fixed analog current support/resistance calculation')
elif new in s:
    print('analog current-level fix already applied')
else:
    raise SystemExit('analog fix anchor not found')
