"""Did the two seats ever see each other's private point schedules?

Two independent failure modes, checked separately:

  1. HARNESS  — a bug putting one role's numbers in the other's prompt. Checked
     structurally against every frame and role, before any run.
  2. BEHAVIOUR — a model citing a value it was never told. Checked against the
     transcripts by ORDERING: a citation only counts as leakage if it precedes
     the counterpart's own disclosure of that value.

Voluntary disclosure is NOT leakage. The rules handed to each side say the
schedule need not be revealed and may not be shown; stating your own walk-away
in conversation is a legitimate negotiating move, and models do it constantly.
What would be damning is a side naming a number nobody gave it.

Usage:  python research/audit_leakage.py [results/live]
"""
import gzip, json, pathlib, re, sys
sys.path.insert(0, ".")
from trackii.case import Case

# A bare integer is not evidence: "30 days" and "30 percent" are not points.
# Only count a number sitting in explicit point language.
PT = r"(?:points?|分|reservation|walk[- ]?away|BATNA|floor|threshold|保留价值)"


NUM_IN_POINTS = (r"(?<![\w.])({n})(?![\w.%])\s*(?:-|–)?\s*{PT}"
                 r"|{PT}\D{{0,24}}(?<![\w.])({n})(?![\w.%])")
# Whose number is it? "44 points for us" is the speaker's own score and proves
# nothing, even when it coincides with the counterpart's walk-away. Only a
# number attributed to the OTHER side can evidence leakage.
THEIRS = r"(?:your|yours|you['’]re|you have|贵方|对方|你方|美方|中方)"
MINE = r"(?:our|ours|we|us|my|mine|我方|本方)"


def _states(text: str | None, n: int) -> bool:
    """The number appears in point language at all."""
    if not text:
        return False
    return bool(re.search(NUM_IN_POINTS.format(n=n, PT=PT), text, re.I))


def cites(text: str | None, n: int, whose: str = "any") -> bool:
    """whose='theirs' requires the value be attributed to the counterpart."""
    if not _states(text, n):
        return False
    if whose == "any":
        return True
    for m in re.finditer(NUM_IN_POINTS.format(n=n, PT=PT), text, re.I):
        window = text[max(0, m.start() - 60):m.end() + 60]
        if re.search(THEIRS, window, re.I) and not re.search(
                rf"{MINE}\W{{0,12}}$", text[max(0, m.start() - 30):m.start()], re.I):
            return True
    return False


def load_case(case_id: str) -> Case:
    if case_id.startswith("package_deal_i"):
        return Case.load(f"cases/instances/{case_id}.yaml")
    stem = "quarantine" if case_id.startswith("quarantine") else "package_deal"
    return Case.load(f"cases/{stem}.yaml")


fail = []

print("1. HARNESS — is any counterpart value present in a role sheet?")
mismatched = 0
for path in ["cases/quarantine.yaml", "cases/package_deal.yaml"]:
    c = Case.load(path)
    for frame in c.frames:
        for role in c.roles:
            for line in c.render_role_sheet(frame, role).splitlines():
                m = re.match(r"\s*\[(\w+)\]\s.*?—\s*(-?\d+)", line)
                if not m:
                    continue
                oid, val = m.group(1), int(m.group(2))
                issue = next((i for i in c.issues if oid in i.option_ids), None)
                if issue and val != issue.points[oid][role]:
                    mismatched += 1
print(f"   mismatched point lines: {mismatched}")
if mismatched:
    fail.append("role sheet carries a counterpart value")

root = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "results/live")
recs = []
for p in sorted(list(root.rglob("*.jsonl")) + list(root.rglob("*.jsonl.gz"))):
    opener = gzip.open if p.suffix == ".gz" else open
    recs += [json.loads(l) for l in opener(p, "rt")]
neg = [r for r in recs if r.get("kind") == "negotiation" and r.get("transcript")]

print(f"\n2. BEHAVIOUR — {len(neg)} negotiations with transcripts")
never = after = 0
premature = []
disclosers = {0: 0, 1: 0, 2: 0}
for r in neg:
    c = load_case(r["case_id"])
    tr = r["transcript"]
    disclosers[sum(
        1 for role in c.roles
        if any(t["role"] == role and cites(t["text"], c.batnas[role]) for t in tr)
    )] += 1
    for role in c.roles:
        other = c.roles[1] if role == c.roles[0] else c.roles[0]
        b = c.batnas[other]
        if b == c.batnas[role]:          # ambiguous: skip
            continue
        disc = next((i for i, t in enumerate(tr)
                     if t["role"] == other and cites(t["text"], b)), None)
        cite = next((i for i, t in enumerate(tr)
                     if t["role"] == role and cites(t["text"], b, whose="theirs")), None)
        if cite is None:
            never += 1
        elif disc is not None and disc < cite:
            after += 1
        else:
            premature.append((r["case_id"], r["frame"], r["seed"], role, b))

print(f"   never cited the counterpart's walk-away : {never}")
print(f"   cited AFTER disclosure (inference)      : {after}")
print(f"   cited with NO prior disclosure          : {len(premature)}")
for p in premature[:10]:
    print(f"      {p[0]} {p[1]} seed={p[2]} {p[3]} cited {p[4]}")
if premature:
    fail.append(f"{len(premature)} pre-disclosure citations")

print(f"\n3. VOLUNTARY DISCLOSURE (not leakage, but it changes the game)")
tot = sum(disclosers.values()) or 1
for k in (0, 1, 2):
    print(f"   {k} side(s) stated their own walk-away: {disclosers[k]:4d}  ({disclosers[k]/tot:.0%})")

print("\n" + "=" * 56)
print("LEAKAGE AUDIT: " + ("CLEAN" if not fail else "FAILURES — " + "; ".join(fail)))
sys.exit(1 if fail else 0)
