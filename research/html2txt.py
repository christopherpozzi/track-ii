import re, sys, html
raw = open(sys.argv[1], encoding='utf-8', errors='replace').read()
raw = re.sub(r'(?is)<(script|style)[^>]*>.*?</\1>', ' ', raw)
raw = re.sub(r'(?is)<br\s*/?>|</p>|</div>|</tr>|</h[1-6]>', '\n', raw)
txt = html.unescape(re.sub(r'(?s)<[^>]+>', ' ', raw))
txt = re.sub(r'[ \t　]+', ' ', txt)
txt = re.sub(r'\n\s*\n+', '\n', txt)
open(sys.argv[2], 'w').write(txt)
print(f"{sys.argv[2]}: {len(txt)} chars")
