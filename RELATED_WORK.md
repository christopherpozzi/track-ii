# Related work, and what Track II actually claims

An earlier draft of this repo said the negotiation-scoring apparatus "has never been pointed at frontier models in a national-security setting." That was too strong. This page states the narrower claim that survives contact with the literature, and names the work Track II must be differentiated from.

## The two papers that come closest

**Abdelnabi, Gomaa, Sivaprasad, Schönherr & Fritz, "Cooperation, Competition, and Maliciousness: LLM-Stakeholders Interactive Negotiation" (NeurIPS 2024 D&B, arXiv 2309.17234).** The closest existing work by a wide margin. A multi-agent, multi-issue scoreable negotiation testbed whose base game is adapted from **Harborco** — a Harvard PON-family scoreable exercise — with six parties, five issues, per-role secret scores, issue priorities, and minimum acceptance thresholds. Two independent reproductions (arXiv 2502.16242, 2602.18230) analyse the Pareto front and add a no-communication baseline.

So: private point schedules + LLMs + Pareto scoring is *not* new. It exists, it is peer-reviewed, and it is built on a PON case.

What Track II does differently:

| | Abdelnabi et al. | Track II |
|---|---|---|
| Parties | 6 | 2 |
| Frontier | sampled / analysed post hoc | **enumerated exactly** (10,800 packages) before any run |
| Framing | fixed (infrastructure siting) | **three frames over one payoff structure**, invariant enforced by the data model |
| BATNA | minimum acceptance threshold | **below-BATNA acceptance as a reported hard-error rate** |
| Case validation | — | **15 structural checks** proving the planted traps are reachable |
| Models | Western | **US and Chinese labs**, which the contest names as an explicit gap |
| Domain | public-infrastructure dispute | US–PRC statecraft |

The two-party restriction is the enabling choice, not a limitation: it is what makes the outcome space small enough to enumerate, which is what makes every metric exact rather than estimated.

**Lorè & Heydari, "Strategic behavior of LLMs: game structure vs. contextual framing" (*Scientific Reports* 14:18490, 2024; arXiv 2309.05898).** Establishes that contextual framing changes LLM strategic choices on social dilemmas, with GPT-3.5 highly context-sensitive and GPT-4 more structure-centric. This is the nearest prior art to Track II's **frame ablation**, and the reason that experiment is well-motivated rather than speculative. Difference: they vary framing on 2×2 social dilemmas; Track II varies framing on a multi-issue bargaining problem and measures the cost in *Pareto efficiency*, not in action choice.

## Everything else worth citing

**Private point schedules, pre-LLM.** Lewis, Yarats, Dauphin, Parikh & Batra, "Deal or No Deal" (EMNLP 2017) — multi-issue divide-the-items with private point values, reporting % agreed and % Pareto-optimal. The direct ancestor of this design.

**Objective negotiation scoring.** TERMS-Bench (arXiv 2605.13909) uses Surplus Efficiency normalised by ZOPA — close kin to Track II's BATNA-normalised surplus share — across agents including Qwen, DeepSeek, GLM and Kimi. Bergemann, Ghili, Hu, Li & Yang (Cowles DP 2940, arXiv 2604.16472) separate **binding offers from natural-language messages** via tool calls so utility computation is automatic: precisely the mechanism Track II's engine uses (free-form dialogue, structured JSON commitment). The HFES/SAGE Nash-bargaining paper (DOI 10.1177/10711813251372102) scores LLMs using the Harvard Negotiation Project's principles and computes Nash products — the one peer-reviewed paper explicitly borrowing a PON scoring frame.

**Negotiation benchmarks generally.** NegotiationArena (ICML 2024) — finds LLMs improve payoffs ~20% through behavioural tactics like feigned desperation, and shows win-rate and average payoff can diverge, which is why Track II reports both surplus share and efficiency rather than a single "who won." CraigslistBargain, CaSiNo, AgreeMate, NegotiationToM round out the lane. "Counterparty Modeling is Not Strategy" (arXiv 2605.16575) finds models infer counterpart preferences accurately yet fail to convert that into better outcomes — a hypothesis Track II can test directly, since log-roll capture and compatible-issue capture separate "understood the structure" from "exploited it."

**2×2 and equilibrium reasoning — a saturated lane.** GTBench (NeurIPS 2024), TMGBench (covering all 144 Robinson-Goforth 2×2 types), Akata et al. (*Nature Human Behaviour* 2025), Fan et al. (AAAI-24), STEER/STEER-ME, GAMA-Bench (ICLR 2025). Track II's control battery is not a contribution to this literature and does not pretend to be; eight games is not coverage, and TMGBench owns coverage. The battery exists solely to establish per-model baseline competence on each structure so the framing result is interpretable.

**Contamination.** "Equilibrium Residuals" (arXiv 2605.10410) shows apparent LLM competence at Nash equilibria is substantially memorisation: accuracy collapses to 34% / 18% / 2% on anonymised 2×2 / 3×3 / 5×5 matrices. This is the origin of the named-vs-anonymised design and should be cited as such. Track II's negotiation case is uncontaminated by construction — the payoffs are synthetic and novel — which also answers the contest post's own caveat that "doing work against historical situations that will be in models' training data will be tough."

**Statecraft and escalation.** Rivera et al., "Escalation Risks from Language Models in Military and Diplomatic Decision-Making" (FAccT 2024); CSIS/Scale CFPD-Benchmark (arXiv 2503.06263) and its DeepSeek follow-up; WarAgent; Lamparth et al. on LLMs and wargames; Cicero (*Science* 2022); AI Diplomacy (Good Start Labs); CivBench. **These are escalation and preference evaluations, not scored bargaining** — none report points earned or Pareto efficiency. That distinction is the gap Track II occupies.

## The claim that survives

> Track II is, to our knowledge, the first evaluation to score frontier models on a **two-party statecraft negotiation whose Pareto frontier, Nash bargaining solution, and BATNA violations are enumerated exactly**, and the first to hold a bargaining payoff structure **invariant across abstract, neutral and politically salient framings** in order to measure the cost of political salience in efficiency terms. It is also, per the contest's own stated gap, among the few to put Chinese and US models on the same scored strategic task.

Every component of that has precedent. The combination, and the exactness, do not.

## Caveats on this page

Several cited works are 2025–2026 preprints, not peer-reviewed: Equilibrium Residuals, TERMS-Bench, Bergemann et al., Counterparty Modeling. Peer-reviewed anchors are Abdelnabi et al., GTBench and GovSim (NeurIPS 2024), Fan et al. (AAAI-24), Akata et al. (*Nature Human Behaviour* 2025), Lorè & Heydari (*Scientific Reports* 2024), Mei et al. (*PNAS* 2024), Cicero (*Science* 2022), and the HFES/SAGE paper. Citations here were compiled from a literature review rather than read end to end; verify before publication.
