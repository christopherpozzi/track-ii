"""What the sourced findings did to the payoff structure. Measure, don't assert.

This originally applied the findings to a throwaway copy of the pre-revision
case to predict their effect (PROPOSAL.md §5). The findings are now implemented,
so it reports the realised numbers against the recorded pre-revision baseline.
"""
import sys
sys.path.insert(0, ".")
from trackii.case import Case
from trackii.scoring import analyze

# Pre-revision baseline, recorded before the case files were rewritten.
BASE = {
    "package_deal": dict(issues=6, packages=3600, max_joint=160,
                         zopa_lo=85, zopa_hi=160, frontier=33),
    "quarantine":   dict(issues=5, packages=1200, max_joint=158,
                         zopa_lo=None, zopa_hi=None, frontier=31),
}

for path, key in [("cases/quarantine.yaml", "quarantine"),
                  ("cases/package_deal.yaml", "package_deal")]:
    c, b = Case.load(path), BASE[key]
    a = analyze(c)
    d, o = c.roles
    inz = [c.payoff(p, d) + c.payoff(p, o) for p in c.packages()
           if c.payoff(p, d) >= c.batnas[d] and c.payoff(p, o) >= c.batnas[o]]
    mean = sum(inz) / len(inz)
    sd = (sum((x - mean) ** 2 for x in inz) / len(inz)) ** 0.5
    print(f"\n=== {c.title} ({c.id}) ===")
    print(f"  issues            {b['issues']} -> {len(c.issues)}")
    print(f"  packages          {b['packages']:,} -> {a.n_packages:,}")
    print(f"  max joint         {b['max_joint']} -> {a.max_joint}")
    print(f"  Pareto frontier   {b['frontier']} -> {len(a.pareto_front)}")
    if b["zopa_lo"]:
        print(f"  in-ZOPA spread    {b['zopa_hi'] - b['zopa_lo']} -> "
              f"{max(inz) - min(inz)}   ({min(inz)}-{max(inz)})")
    else:
        print(f"  in-ZOPA spread    {max(inz) - min(inz)}   ({min(inz)}-{max(inz)})")
    print(f"  in-ZOPA sd        {sd:.1f}")
    print(f"  ZOPA share        {a.zopa_size / a.n_packages:.1%}")
    print(f"  log-roll pair     {', '.join(a.log_roll_issues)}")
    print(f"  compatible        {', '.join(a.compatible_issues) or 'none'}")
    print(f"  distributive      {', '.join(a.distributive_issues)}")

print("\nThe package deal's integrative range narrowed when the findings were "
      "applied.\nThat trade-off is stated in PROPOSAL.md §5 and in the site's "
      "Limitations.")
