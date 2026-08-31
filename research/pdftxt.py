import sys, re
from pypdf import PdfReader
r = PdfReader(sys.argv[1])
out = []
for n, p in enumerate(r.pages, 1):
    t = p.extract_text() or ""
    out.append(f"\n<<<PAGE {n}>>>\n{t}")
txt = "".join(out)
txt = re.sub(r"[ \t]+", " ", txt)
open(sys.argv[2], "w").write(txt)
print(f"{len(r.pages)} pages, {len(txt)} chars -> {sys.argv[2]}")
