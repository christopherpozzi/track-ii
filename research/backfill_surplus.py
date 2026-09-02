"""Backfill surplus_realised into records written before the field existed.

A long run loads scoring.py at launch, so a field added mid-run is absent from
everything that run produces. Because the analysis helpers read it with
`.get(x) or 0`, absent silently became zero -- and zero is a plausible-looking
score. Run this after any sweep that started before a scoring change.

    python research/backfill_surplus.py [results ...]
"""
import glob, gzip, json, sys
sys.path.insert(0, ".")
from trackii.case import Case
from trackii.scoring import analyze

_cache: dict = {}


def case_for(case_id: str):
    if case_id not in _cache:
        path = (f"cases/instances/{case_id}.yaml" if case_id.startswith("package_deal_i")
                else f"cases/{'quarantine' if case_id.startswith('quarantine') else 'package_deal'}.yaml")
        c = Case.load(path)
        _cache[case_id] = (c, analyze(c))
    return _cache[case_id]


targets = sys.argv[1:] or (glob.glob("results/*.jsonl") + glob.glob("results/live/*.jsonl.gz"))
for f in targets:
    opener = gzip.open if f.endswith(".gz") else open
    out, fixed = [], 0
    for line in opener(f, "rt"):
        r = json.loads(line)
        sc = r.get("score") or {}
        if r.get("kind") == "negotiation" and "surplus_realised" not in sc:
            c, a = case_for(r["case_id"])
            d, o = c.roles
            floor, ceil = c.batnas[d] + c.batnas[o], a.max_joint
            j = sc.get("joint", floor)
            sc["surplus_realised"] = (
                0.0 if not r.get("agreement") or ceil <= floor
                else max(0.0, (j - floor) / (ceil - floor)))
            fixed += 1
        out.append(json.dumps(r, default=str))
    if fixed:
        with opener(f, "wt") as fh:
            fh.write("\n".join(out) + "\n")
    print(f"  {f}: {fixed} backfilled")
