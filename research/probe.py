"""What do the sourced findings do to the payoff structure? Measure, don't assert."""
import copy, io, sys, yaml
sys.path.insert(0, '.')
from contextlib import redirect_stdout
from trackii.case import Case
from trackii.scoring import analyze
from trackii.validate import validate

raw0 = yaml.safe_load(open("cases/package_deal.yaml"))

def stats(raw, label):
    c = Case(raw)
    a = analyze(c)
    d, o = c.roles
    buf = io.StringIO()
    try:
        with redirect_stdout(buf):
            validate(c, verbose=False)
        v = "PASS"
    except Exception as e:
        v = f"FAIL: {str(e)[:70]}"
    joints = [c.payoff(p, d) + c.payoff(p, o) for p in c.packages()]
    inz = [c.payoff(p,d)+c.payoff(p,o) for p in c.packages()
           if c.payoff(p,d) >= c.batnas[d] and c.payoff(p,o) >= c.batnas[o]]
    print(f"\n--- {label} ---")
    print(f"  validator      : {v}")
    print(f"  max joint      : {max(joints)}   (in-ZOPA spread {min(inz)}-{max(inz)})")
    print(f"  ZOPA share     : {len(inz)/len(joints):.1%}")
    print(f"  frontier size  : {len(a.pareto_front)}")
    print(f"  DELTA rng: " + ", ".join(
        f"{i.id[:12]}={i.range_for(d)}" for i in c.issues))
    print(f"  OMEGA rng: " + ", ".join(
        f"{i.id[:12]}={i.range_for(o)}" for i in c.issues))

stats(raw0, "AS SHIPPED")

# Finding 1: US ranks export controls ABOVE Taiwan arms (USCC priority recs 5/10
# vs 1 reporting requirement; NSS supply chains as sole operational econ policy).
# Swap DELTA's two ranges by exchanging the two issues' DELTA columns.
r1 = copy.deepcopy(raw0)
iss = {i["id"]: i for i in r1["issues"]}
ec, sc = iss["export_controls"], iss["security_commitment"]
# DELTA on export_controls currently 30..0 descending; make it the wider issue.
for o, v in zip(ec["options"], [40, 30, 20, 10, 0]):
    o["points"]["DELTA"] = v
for o, v in zip(sc["options"], [30, 20, 10, 0]):
    o["points"]["DELTA"] = v
stats(r1, "F1: US ranks export controls above Taiwan arms")

# Finding 2: fentanyl cooperation was PURCHASED (Busan: 10pp tariff for it) and
# had been withdrawn as leverage -> OMEGA prefers LESS enforcement, not more.
r2 = copy.deepcopy(r1)
pr = {i["id"]: i for i in r2["issues"]}["precursors"]
for o, v in zip(pr["options"], [0, 6, 12]):
    o["points"]["OMEGA"] = v
stats(r2, "F1+F2: and fentanyl is not compatible")
