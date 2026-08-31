"""Inter-SOURCE concordance for the 12 cells.

NOT inter-coder reliability. RESEARCH_PLAN.md §9 Tier 3 requires a second
independent coder and Krippendorff's alpha; there is one coder here, so alpha is
unavailable, and a number computed from one person's two readings of the same
corpus would be a fabricated statistic.

What IS available to a single coder is how far *independent sources* agree about
the same cell. Each entry names documents in the checksummed corpus and whether
each supports, qualifies, or contradicts the coded direction. Auditable against
research/CORPUS.sha256.
"""
import collections

CELLS = {
 "export_controls.DELTA": [
   ("uscc_full", "support", "223 mentions vs 11 'arms sale'; 5 of 10 priority recs"),
   ("nss_2025", "contradict", "'export control' appears ONCE, offering allies alignment"),
   ("crs_export_controls_semi", "support", "continuous tightening 2022-25; sell->rent"),
   ("ustr_301_report", "qualify", "2 mentions in 215pp; the instrument there is tariffs"),
   ("brookings_nss", "support", "'only one operational economic policy...supply chains'"),
 ],
 "export_controls.OMEGA": [
   ("cfr_red_lines", "support", "'China's primary concern is likely US export controls'"),
   ("mofcom_2410", "support", "counts 3000 vs 900; 'not an export ban'; licensing ladder"),
   ("mofcom_dec2024", "support", "acts under Export Control Law; gallium/germanium ban"),
   ("pc20_zh", "support", "'坚决打赢关键核心技术攻坚战'"),
   ("crs_export_controls_semi", "support", "antitrust/antidumping used to pressure US controls"),
 ],
 "security_commitment.DELTA": [
   ("forum_arms_trade", "support", "$11.44bn in 2025; baseline flow undisturbed"),
   ("uscc_full", "qualify", "sole Taiwan priority rec is a reporting requirement"),
   ("nss_2025", "qualify", "Taiwan valued for the Second Island Chain, not leverage"),
   ("fa_taiwan_not_for_sale", "qualify", "argues Taiwan should not be traded, implying it is being"),
 ],
 "security_commitment.OMEGA": [
   ("prc_anti_secession_law", "support", "Art.8 triggers exclude arms sales"),
   ("taiwan_wp_zh", "support", "arms sales 3rd of 7 grievances under 以台制华"),
   ("mofa_arms_sales_dec2024", "support", "protest without announced countermeasures"),
   ("uscc_full", "contradict", "PRC sanctioned 13 US military firms over the Dec 2024 package"),
   ("cfr_red_lines", "qualify", "Taiwan is red line #1, listed first"),
 ],
 "tariffs.DELTA": [
   ("ustr_301_report", "support", "tariffs are the instrument, tech transfer the grievance"),
   ("piie_2025_imports", "qualify", "Supreme Court struck many 2025 tariffs, Feb 2026"),
   ("uscc_full", "support", "249 mentions but no priority recommendation"),
 ],
 "tariffs.OMEGA": [
   ("brookings_busan", "support", "tariff relief is what Beijing extracted at Busan"),
   ("cfr_red_lines", "support", "Wang Yi: 'stop imposing 301 tariffs'"),
   ("piie_tariff_chart", "qualify", "levels asymmetric: US 47.5% vs PRC 31.9%"),
   ("mofcom_2410", "support", "'我们不愿打，但也不怕打'"),
 ],
 "precursors.DELTA": [
   ("uscc_full", "support", "tariffs imposed over lack of precursor cooperation"),
   ("brookings_fentanyl", "support", "US seeks enforcement"),
 ],
 "precursors.OMEGA": [
   ("brookings_busan", "contradict", "cooperation purchased with 10pp of tariff relief"),
   ("uscc_full", "contradict", "tariffs imposed over non-cooperation; lever runs both ways"),
   ("brookings_fentanyl", "contradict", "'transactional compliance disconnected from commitment'"),
 ],
 "market_access.DELTA": [
   ("uscc_full", "support", "'reciprocal market access' + investment screening, 52 mentions"),
   ("ustr_301_report", "support", "JV 78, licensing 113 - access with safeguards"),
 ],
 "market_access.OMEGA": [
   ("pc20_zh", "support", "'合理缩减外资准入负面清单'"),
   ("phase_one", "support", "'China shall' 92 vs 'United States shall' 4"),
 ],
 "joint_research.DELTA": [
   ("csis_sta", "support", "STA renewed but narrowed to basic science"),
 ],
 "joint_research.OMEGA": [
   ("csis_sta", "support", "both governments signed the narrowed protocol"),
 ],
}

rows, tally = [], collections.Counter()
for cell, srcs in CELLS.items():
    v = collections.Counter(s[1] for s in srcs)
    n = len(srcs)
    status = ("uncontested" if v["contradict"] == 0 and v["qualify"] == 0 else
              "qualified" if v["contradict"] == 0 else "contested")
    tally[status] += 1
    rows.append((cell, n, v["support"], v["qualify"], v["contradict"],
                 v["support"] / n, status))

w = max(len(r[0]) for r in rows)
print(f"{'cell':<{w}}   n  sup  qual  con   conc   status")
print("-" * (w + 38))
for c, n, s_, q, x, conc, st in rows:
    print(f"{c:<{w}}  {n:2d}   {s_:2d}    {q:2d}   {x:2d}  {conc:5.0%}   {st}")
tot = sum(len(v) for v in CELLS.values())
cnt = collections.Counter(s[1] for v in CELLS.values() for s in v)
print("-" * (w + 38))
print(f"{'ALL':<{w}}  {tot:2d}   {cnt['support']:2d}    {cnt['qualify']:2d}   "
      f"{cnt['contradict']:2d}  {cnt['support']/tot:5.0%}")
print()
for k in ("uncontested", "qualified", "contested"):
    print(f"  {k:<12} {tally[k]:2d} of {len(CELLS)} cells")
singles = [c for c, v in CELLS.items() if len(v) == 1]
print(f"\n  median sources per cell: {sorted(len(v) for v in CELLS.values())[len(CELLS)//2]}")
print(f"  cells resting on ONE source: {singles or 'none'}")
