"""Pre-flight audit of case mechanics — properties the validator does NOT check.

The validator proves the planted structure is reachable. This asks the separate
question: is the case a good *instrument*, and are there degeneracies that would
make a live run uninterpretable or cheap to game?
"""
import itertools, sys
sys.path.insert(0, ".")
from pathlib import Path
from trackii.case import Case
from trackii.scoring import analyze

FAIL = []
def check(case_id, name, ok, detail=""):
    mark = "ok  " if ok else "FAIL"
    if not ok:
        FAIL.append(f"{case_id}: {name}")
    print(f"  [{mark}] {name}" + (f"  — {detail}" if detail else ""))

for path in ["cases/quarantine.yaml", "cases/package_deal.yaml"]:
    c = Case.load(path)
    a = analyze(c)
    d, o = c.roles
    print(f"\n=== {c.title}  ({c.id}) ===")

    # 1. Frame invariance — the load-bearing claim of the whole ablation.
    frames = list(c.frames)
    ref = {i.id: dict(i.points) for i in c.issues}
    same = all(
        set(c.frames[f]["issues"]) == set(c.issue_ids)
        and all(set(c.frames[f]["issues"][i.id]["options"]) == set(i.option_ids)
                for i in c.issues)
        for f in frames
    )
    check(c.id, "every frame covers every issue and option", same, f"{len(frames)} frames")

    # 2. No option-id collisions across issues (a silent scoring hazard).
    ids = [(i.id, o) for i in c.issues for o in i.option_ids]
    dupes = {o for _, o in ids if sum(1 for _, x in ids if x == o) > 1}
    check(c.id, "no option-id collisions across issues", not dupes, f"{dupes or 'none'}")

    # 3. Dominated options. On a COMPATIBLE issue these are definitional (both
    #    sides peak on the same rung, so every other rung is jointly worse) and
    #    on an interior-optimum issue they are expected. The defect would be a
    #    dominated rung on a LOG-ROLL or DISTRIBUTIVE issue, where the ladder is
    #    supposed to be a real trade-off: that would be a fake rung nobody could
    #    ever rationally settle on.
    def dominated(i):
        out = []
        for x in i.option_ids:
            for y in i.option_ids:
                if x != y and i.points[y][d] >= i.points[x][d] and \
                   i.points[y][o] >= i.points[x][o] and \
                   (i.points[y][d] > i.points[x][d] or i.points[y][o] > i.points[x][o]):
                    out.append(f"{i.id}:{x}<{y}")
                    break
        return out
    bargaining = [i for i in c.issues
                  if i.design_role.startswith("log_roll") or i.design_role == "distributive"]
    bad = [x for i in bargaining for x in dominated(i)]
    check(c.id, "no dominated rungs on log-roll or distributive issues",
          not bad, f"{bad or 'none'}")
    expected = [x for i in c.issues if i not in bargaining for x in dominated(i)]
    print(f"  [note] dominated by design (compatible / interior optimum): "
          f"{expected or 'none'}")

    # 3b. Every rung on a bargaining issue must actually move both sheets, or
    #     the ladder is shorter than it advertises.
    flat = [f"{i.id}:{x}" for i in bargaining for k, x in enumerate(i.option_ids[1:], 1)
            if i.points[x][d] == i.points[i.option_ids[k-1]][d]
            and i.points[x][o] == i.points[i.option_ids[k-1]][o]]
    check(c.id, "every bargaining rung changes the payoff", not flat, f"{flat or 'none'}")

    # 4. Neither side can compute the joint optimum from its own sheet alone.
    own_opt_d = {i.id: i.best_for(d) for i in c.issues}
    own_opt_o = {i.id: i.best_for(o) for i in c.issues}
    jd = c.payoff(own_opt_d, d) + c.payoff(own_opt_d, o)
    jo = c.payoff(own_opt_o, d) + c.payoff(own_opt_o, o)
    check(c.id, "own-optimum is NOT the joint optimum for either side",
          jd < a.max_joint and jo < a.max_joint,
          f"{d} own-opt joint={jd}, {o} own-opt joint={jo}, max={a.max_joint}")

    # 5. The max-joint package is rare — you have to find it, not stumble on it.
    nmax = sum(1 for p in c.packages()
               if c.payoff(p, d) + c.payoff(p, o) == a.max_joint)
    check(c.id, "joint optimum is rare in the outcome space",
          nmax / a.n_packages < 0.01, f"{nmax}/{a.n_packages} packages")

    # 6. NOT near-zero-sum inside the ZOPA — the criticism levelled at prior work.
    inz = [c.payoff(p, d) + c.payoff(p, o) for p in c.packages()
           if c.payoff(p, d) >= c.batnas[d] and c.payoff(p, o) >= c.batnas[o]]
    spread = max(inz) - min(inz)
    mean = sum(inz) / len(inz)
    var = (sum((x - mean) ** 2 for x in inz) / len(inz)) ** 0.5
    check(c.id, "joint value varies materially inside the ZOPA",
          spread >= 30 and var >= 8,
          f"range {min(inz)}-{max(inz)} (spread {spread}), sd {var:.1f}")

    # 7. Max-joint splits differ — value creation and claiming are separable.
    splits = {c.payoff(p, d) for p in c.packages()
              if c.payoff(p, d) + c.payoff(p, o) == a.max_joint}
    check(c.id, "several distinct splits achieve max joint",
          len(splits) > 1, f"{d} gets {min(splits)}-{max(splits)} across {len(splits)} splits")

    # 8. Label swap leaves payoffs untouched.
    n_swap = c.frame_roles("salient", label_swap=True)
    n_norm = c.frame_roles("salient", label_swap=False)
    check(c.id, "label swap exchanges identities only",
          n_swap[d]["name"] == n_norm[o]["name"] and n_swap[o]["name"] == n_norm[d]["name"])

    # 9. BATNA is beatable but not trivially.
    beat_d = sum(1 for p in c.packages() if c.payoff(p, d) >= c.batnas[d]) / a.n_packages
    beat_o = sum(1 for p in c.packages() if c.payoff(p, o) >= c.batnas[o]) / a.n_packages
    check(c.id, "each BATNA is a real constraint",
          0.2 < beat_d < 0.98 and 0.2 < beat_o < 0.98,
          f"{d} beats in {beat_d:.0%}, {o} in {beat_o:.0%}")

    # 10. Role sheets render in every frame and never leak the other side's points.
    leak = []
    for f in frames:
        for r in c.roles:
            sheet = c.render_role_sheet(f, r)
            other = c._other(r)
            for i in c.issues:
                for oid in i.option_ids:
                    mine, theirs = i.points[oid][r], i.points[oid][other]
                    if mine != theirs and f"{theirs} " in sheet and f"[{oid}]" in sheet:
                        seg = sheet.split(f"[{oid}]")[1].split("\n")[0]
                        if f"{theirs}" in seg and f"{mine}" not in seg:
                            leak.append(f"{f}/{r}/{oid}")
    check(c.id, "no role sheet leaks the counterpart's points", not leak, f"{leak[:3] or 'none'}")

print("\n" + "=" * 60)
print(f"MECHANICS AUDIT: {'ALL PASS' if not FAIL else str(len(FAIL)) + ' FAILURES'}")
for f in FAIL:
    print("  " + f)
