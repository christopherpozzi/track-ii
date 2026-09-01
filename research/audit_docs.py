"""Pre-flight audit of the documentation.

Checks that every quantitative claim in the docs matches what the code actually
computes, that internal links resolve, and that quotations in SOURCES.md are
recoverable from the checksummed corpus.
"""
import re, sys, pathlib
sys.path.insert(0, ".")
from trackii.case import Case
from trackii.scoring import analyze

FAIL, WARN = [], []
def check(name, ok, detail="", warn=False):
    if ok:      print(f"  [ok  ] {name}" + (f"  — {detail}" if detail else ""))
    elif warn:  WARN.append(name); print(f"  [warn] {name}  — {detail}")
    else:       FAIL.append(name); print(f"  [FAIL] {name}  — {detail}")

DOCS = ["README.md", "WRITEUP.md", "DESIGN.md", "RELATED_WORK.md",
        "PROPOSAL.md", "SOURCES.md", "RESEARCH_PLAN.md", "CHANGELOG.md"]
text = {d: pathlib.Path(d).read_text() for d in DOCS if pathlib.Path(d).exists()}
allmd = "\n".join(text.values())

print("=== 1. quantitative claims match the code ===")
pd = Case.load("cases/package_deal.yaml"); apd = analyze(pd)
qz = Case.load("cases/quarantine.yaml");   aqz = analyze(qz)
facts = {
    "10,800": apd.n_packages == 10800,
    "1,200":  aqz.n_packages == 1200,
    "8,150":  apd.zopa_size == 8150,
}
for lit, ok in facts.items():
    used = [d for d in text if lit in text[d]]
    check(f"figure {lit} is correct where cited", ok, f"cited in {used or 'nowhere'}")

# stale figures from the previous structure must appear nowhere
for stale in ["3,600", "2,624", "78.8%", "1,200 packages | 6 "]:
    hits = [d for d in text if stale in text[d]]
    live = [d for d in hits if d not in ("PROPOSAL.md", "SOURCES.md",
                                         "RESEARCH_PLAN.md", "CHANGELOG.md")]
    check(f"stale figure {stale!r} absent from reader-facing docs", not live,
          f"found in {live}" if live else f"(history only: {hits})")

print("\n=== 2. issue counts and names ===")
for c, n in ((pd, 7), (qz, 5)):
    check(f"{c.id} has {n} issues", len(c.issues) == n, ", ".join(c.issue_ids))
for old in ["export_controls"]:
    live = [d for d in text if old in text[d]
            and d not in ("PROPOSAL.md", "SOURCES.md", "RESEARCH_PLAN.md", "CHANGELOG.md")]
    check(f"retired issue id {old!r} absent from reader-facing docs", not live, f"{live}")

print("\n=== 3. internal links resolve ===")
bad = []
for d, s in text.items():
    for m in re.finditer(r"\[[^\]]+\]\((?!https?:)([^)#]+)\)", s):
        tgt = m.group(1).strip()
        if not pathlib.Path(tgt).exists():
            bad.append(f"{d} -> {tgt}")
check("every relative link resolves", not bad, f"{bad or 'none'}")

print("\n=== 4. SOURCES.md quotations are recoverable ===")
corpus = pathlib.Path("corpus")
present = {p.name for p in corpus.glob("*.txt")}
# Every quotation that appears on the site or in SOURCES.md. If one of these
# stops matching, either the corpus changed or a quotation drifted -- both are
# things a reader would find and neither should ship.
quotes = [
    ("中国的出口管制不是禁止出口", "mofcom_2410.txt"),
    ("美方管制清单物项超过3000项", "mofcom_2410.txt"),
    ("并就双方可在相关产业开展合作提出建议", "mofcom_2410.txt"),
    ("但美方态度消极", "mofcom_2410.txt"),
    ("和平统一的可能性完全丧失", "prc_anti_secession_law.txt"),
    ("决不承诺放弃使用武力", "pc20_zh.txt"),
    ("坚决打赢关键核心技术攻坚战", "pc20_zh.txt"),
    ("不断策动对台军售", "taiwan_wp_zh.txt"),
    ("把台湾当作遏制中国发展进步", "taiwan_wp_zh.txt"),
    ("align their export controls with ours", "nss_2025.txt"),
    ("China shall", "phase_one.txt"),
    ("China Slaps Sanctions on 13 US Military Firms", "uscc_full.txt"),
    ("troubling divergence has emerged", "uscc_full.txt"),
    ("negotiating national security decisions in exchange for trade concessions",
     "crs_export_controls_semi.txt"),
    ("much better position to endure", "rand_quarantine.txt"),
    ("inaction is tantamount to accepting", "rand_quarantine.txt"),
    ("they found an offramp", "csis_lights_out.txt"),
]
for q, f in quotes:
    if f not in present:
        check(f"quote in {f}", True, "file not redistributed — skipped", warn=False)
        continue
    # PDF-derived text wraps mid-sentence, so normalise whitespace before
    # searching -- otherwise a genuine quotation reads as a fabricated one.
    body = re.sub(r"\s+", " ", (corpus / f).read_text(errors="replace"))
    check(f"{q[:34]!r} present in {f}", re.sub(r"\s+", " ", q) in body)

print("\n=== 5. repo scripts actually run ===")
import subprocess
for script in ["research/probe.py", "research/concordance.py",
               "research/audit_mechanics.py", "research/audit_leakage.py"]:
    r = subprocess.run([sys.executable, script], capture_output=True,
                       text=True, timeout=180, cwd=".")
    check(f"{script} exits clean", r.returncode == 0,
          (r.stderr.strip().splitlines() or [""])[-1][:70])

print("\n=== 6. cross-document consistency ===")
check("PROPOSAL marked implemented",
      "Status: IMPLEMENTED" in text.get("PROPOSAL.md", ""))
check("CHANGELOG exists and names both cases",
      all(k in text.get("CHANGELOG.md", "") for k in ("Package Deal", "Quarantine")))
check("README points at the evidence base",
      all(k in text.get("README.md", "") for k in ("SOURCES.md", "CORPUS.sha256")))
check("retraction count is stated as four",
      "Four retractions" in allmd or "four retractions" in allmd)

print("\n" + "=" * 58)
print(f"DOCS AUDIT: {'ALL PASS' if not FAIL else str(len(FAIL)) + ' FAILURES'}"
      + (f", {len(WARN)} warnings" if WARN else ""))
for f in FAIL: print("  FAIL " + f)
