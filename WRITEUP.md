# Track II: scoring the situation room against a computable optimum

*Submitted to ChinaTalk's Evals for the Situation Room contest.*

---

## Starting from the brief

The contest post frames the gap as decisions about "whether to escalate, how to negotiate, or what to believe." Two of those three have benchmarks. Escalation has CFPD, WarAgent, and Rivera et al. Belief-formation has a forecasting literature. **Negotiation has nothing that scores it** — what exists measures escalation *tendency* and lets that stand in for bargaining skill.

The same post names a second gap without hedging: "none of the three projects linked here evaluated Chinese models, for example."

This entry is built against both, and the second one shaped the design more than the first. Running a Chinese model on an English prompt confounds model origin with prompt language, and every benchmark that includes Chinese models does exactly that. Track II runs the identical payoff structure in English and in Mandarin, so the comparison becomes a clean 2×2 rather than a confound.

## The wall everyone hits

Read the three most serious attempts to evaluate frontier models on foreign policy and you find the same confession in each.

CSIS and Scale AI built the Critical Foreign Policy Decisions benchmark: 400 hand-written scenarios, actors swapped in and out to yield 66,473 observations. Then, in the methodology, they give up on correctness. Foreign policy scenarios, they write, often lack a single right answer, which makes standard test-and-evaluation approaches insufficient. So CFPD measures *tendencies* instead — does the model lean toward aggression or restraint, intervention or diplomacy. That is genuinely useful descriptive data. But it has no performance axis. You can report what a model prefers. You cannot report whether it is any good.

John Chen's Civilization V work goes the other way and gets real outcomes: victory, defeat, five hundred turns of consequences. ChinaTalk's own write-up names the limit — a game gives you the outcome without telling you why the decisions were made. And strategic skill is tangled up with knowing Civ V.

Scoring models against declassified NIEs has genuine ground truth and is fatally contaminated: every frontier model knows how the Sino-Soviet split turned out.

So the field has interactive-but-unscored, scored-but-contaminated, and richly-descriptive-but-unranked. Nothing that is all three.

## Borrowing an answer key from the negotiation literature

The problem "score the quality of a negotiated outcome when there is no objectively right answer" is not new, and it is not open. Business schools solved it decades ago.

A Kellogg DRRC or Harvard PON multi-issue case hands each side a **private point schedule**: a set of issues, discrete settlement options on each, and a private cardinal value for every option. Each side also gets a reservation value — what it receives if it walks. Students negotiate; the instructor scores the result against an answer key computed from the schedules.

Once both players have private cardinal utilities over a discrete issue space, a great deal becomes computable rather than arguable:

- the complete outcome space, enumerable by brute force,
- the **Pareto frontier**, exactly,
- the **maximum joint value**, and so how much value a given deal destroyed,
- the **Nash bargaining solution** and the Kalai–Smorodinsky point,
- each side's **BATNA**, and so whether a deal was worse than no deal.

Crucially, it splits performance into two independent axes that ordinary "who won" scoring conflates: **value creation** (was the pie made as large as it could be?) and **value claiming** (what share did I take?). A model can be excellent at one and terrible at the other, and policymakers should care about the difference.

Pointing this apparatus at LLMs is not itself new — Abdelnabi et al. (NeurIPS 2024) built a scoreable multi-issue testbed on *Harborco*, a Harvard PON case, with per-role secret scores and Pareto analysis. What is new here is exactness and control: **two** parties rather than six, so the frontier is enumerated rather than sampled; a single payoff structure held invariant across four framings, one of them Mandarin, so the effect of political salience is measurable rather than inferred and prompt language is separated from model origin; below-BATNA acceptance reported as a hard-error rate; and Chinese models alongside US ones, which the contest post names as a gap in all three projects it links. Applied this way, it dissolves the dead end CFPD declared unsolvable: you get tendencies *and* a performance score, out of the same run, with no rubric and no human judge.

**In one sentence:** two models negotiate a six-issue diplomatic package under private point schedules, and the deal they reach is scored against the computable Pareto frontier.

## The cases

The flagship is **The Quarantine**: a live crisis in which Beijing has declared a maritime inspection regime around Taiwan and Washington has surged two carrier groups. Five issues, 1,200 packages, walk-away values deliberately low on both sides because no-agreement means the crisis continues. It leads because it is the better-evidenced of the two — CSIS and RAND independently corroborate the premise, the inspection axis, the low walk-away values, and the direction of their asymmetry.

The second is **The Package Deal**, a US–PRC omnibus: semiconductor export controls, critical minerals controls, Section 301 tariffs, fentanyl precursor enforcement, a pending Taiwan arms package, investment screening, and science cooperation. Seven issues, 10,800 packages. Both carry the same deliberate traps in the payoff structure:

- **A compatible issue.** Both sides' point schedules peak on the *same* settlement. Neither knows this. A negotiator with fixed-pie bias treats it as contested and splits the difference, burning joint value for nothing at all.
- **A log-roll pair.** Semiconductor controls are worth more to Beijing than to Washington; critical-minerals controls are worth more to Washington than to Beijing. Trading them wholesale creates 14 points of joint value — but leaves Washington nine points *worse off* than the split it most prefers, so it only closes if funded by a side payment on tariffs. That is what real integrative bargaining looks like, and it is a sharper test than a free lunch. This pairing is not authored: it is the one the record documents, after BIS rescinded EDA licence requirements in July 2025 against Beijing resuming rare-earth magnet licensing.
- **A purely distributive issue.** Tariffs are exactly zero-sum: joint value is constant at 20 whatever the settlement. This is where value claiming is measured, cleanly separated from value creation.
- **A non-monotonic issue.** Washington's optimum on market access is the *second* option, not an endpoint — catching models that assume preferences are linearly opposed instead of reading their own sheet.
- **Asymmetric BATNAs.** Washington can credibly walk from far more packages than Beijing can. The Nash solution correspondingly hands Washington the entire distributive issue, which is the right game-theoretic answer and one most human negotiators miss.

Split the difference on every issue and you capture 88% of the available joint value in the package deal, 85% in the crisis. That gap is what the eval measures against.

## Two metrics that need no interpretation

Most of the output is continuous — efficiency ratios, surplus shares, log-roll capture. Two are bright lines.

**Below-BATNA acceptance.** The role sheet states the walk-away value in points, explicitly, in the prompt. A model that signs a package worth less than that to its own side has made an unambiguous error, detectable by arithmetic, with no judge and no interpretation. *"This model signed a deal worse than walking away in 18% of runs"* is a sentence a policymaker understands instantly — the strategic-reasoning equivalent of a jailbreak rate.

**Impasse despite a ZOPA.** In the package deal 8,150 of 10,800 packages beat both sides' walk-away values. Collapsing the talks anyway is a failure with a denominator.

Neither can be argued with, and neither requires anyone to agree about foreign policy.

## The experiment that matters

ChinaTalk's explainer raised a question and left it hanging: how much of what we see in these evals is reasoning, and how much is alignment training reacting to politically loaded content? It suggested the test — swap Taiwan for Cape Verde and see what changes.

Track II runs exactly that, as its headline experiment. The *identical* payoff matrix is presented four ways: abstract placeholders; two low-salience real states (Cabo Verde and Vanuatu); the live US–PRC issue set; and that same issue set prompted entirely in Mandarin, boilerplate and all. Payoffs are defined once in the case file and the frames supply labels only, so the conditions are provably the same game — the invariant is enforced by the data structure, not by my carefulness.

The drop in Pareto efficiency from abstract to salient is the **framing tax**: how much political salience costs a model in strategic competence, in points, on a structure it demonstrably can solve.

Two further experiments follow. **Head-to-head** puts US-lab models against Chinese-lab models on the salient frame, each pairing run in both seat assignments so the result cannot be an artifact of which side of the table a model sat on; surplus share is normalised by BATNA so the seats are comparable. **Label swap** attaches the national identities to the opposite structural role, so a model must advance interests that cut against its priors about that actor.

A fourth experiment is the ablation that makes the whole thing falsifiable: the same take-it-or-leave-it close with **zero rounds of dialogue**. If models that never talk score as well as models that negotiate, this benchmark is not measuring negotiation. Two independent reproductions of Abdelnabi et al. found precisely that on their testbed, so it is reported here rather than left for a reviewer to discover.

And a **control battery** of eight games with provable solutions — strict dominance, payoff dominance, best response to a commitment, mixed strategy, iterated dominance, backward induction through a non-credible threat, the Schelling value of destroying your own options, and an equilibrium that is Pareto-dominated. Each is asked three ways: as a bare payoff matrix, as a named textbook game ("this is the Prisoner's Dilemma"), and as a US–China scenario — identical numbers throughout. The named condition separates recall from computation, replicating the memorisation result from Equilibrium Residuals.

The control is what makes the headline interpretable. Alone it is a scripted eval with an answer key — the genre the judges said they find least interesting, and they are right. Its job here is different: it establishes whether a model can solve a given structure *at all* in the abstract. Only then does failure on the same structure under political framing license a claim about framing rather than about capability. Without it, "the model bargained worse over Taiwan" is a finding with two explanations. With it, there is one.

## Why the numbers should be believed

The explainer warns against vibe-coded benches that don't faithfully represent the concept they claim to test. That warning shaped the build more than anything else.

**The case is validated before any model is called.** The validator brute-forces all 10,800 packages and asserts fifteen properties: the ZOPA is non-empty but not trivial, both sides can be pushed below BATNA, the frontier is non-degenerate and carries a distributive dimension, each compatible issue really is compatible, the distributive issue is exactly zero-sum, the log-roll genuinely creates joint value, that surplus is compensable via the distributive issue, and the naive baseline leaves enough headroom for the eval to discriminate.

**The answer key is re-derived, not asserted.** The battery ships solvers for dominance, pure and mixed Nash, iterated elimination, and backward induction, and every stated answer must match solver output before anything runs. This caught a real error in my own work: my first Schelling commitment game gave the committing player 6 points whether or not it destroyed its retreat option, so commitment bought nothing and my stated answer was wrong. The game needed the opponent moving first. A hand-checked answer key would have shipped that.

**There is a null control.** The offline mock client ignores prompt content entirely, making it frame-blind by construction, and a test asserts it scores identically across all three frames. If the harness itself leaked a framing artifact — prompt-length effects, option ordering drifting, seeds consumed at different rates — that test fails. It passes, and the flat 78% across frames in the demo report is that control visible on the page.

**Grading does not punish notation.** A model answering `50%`, `1/2`, or `.5` on the mixed-strategy question is marked correct. Strictness there would measure formatting compliance rather than game theory — the failure mode the explainer describes as stacking constraints to manufacture low scores.

**The LLM judge is quarantined.** Every headline metric is arithmetic. The judge touches only two things that genuinely cannot be derived from the final package — whether a player lied about its own valuations, and whether it used coercive language — and it is handed the player's true point schedule so misrepresentation claims are checkable against ground truth. Any finding whose supporting quote does not literally appear in the transcript is discarded, which is the main failure mode of LLM-as-judge on adversarial text.

Seventy-one tests, including a cross-check of the fast Pareto frontier against the naive O(n²) definition and of every solver against textbook games with known solutions.

## What this gives a policymaker

Three numbers that do not currently exist:

1. **How much strategic competence a model loses when the countries are named** — measured against a structure it provably can solve when they are not.
2. **How often a model accepts a deal worse than walking away** — a bright-line error rate on a task where the walk-away value was stated in the prompt.
3. **Whether it creates value or merely claims it** — separated, rather than collapsed into a single "who won."

None requires anyone to agree about the substance of foreign policy. That is the point.

## Two cases, not one

The package deal is a grand bargain under no time pressure. That is deal-making, and against a brief titled "the situation room" it is a fair criticism that deal-making is not crisis management. So there is a second case, **The Quarantine**: the PRC has begun a maritime inspection regime around Taiwan, the US has surged two carrier groups, there has been one collision, and delegations are negotiating de-escalation through a back channel.

Same scoring apparatus, inverted strategic character. BATNAs are deliberately *low* for both sides, because no agreement means the crisis continues — so below-BATNA acceptance becomes nearly impossible and **impasse** becomes the headline failure. A model that holds out for a better split and blows up the talks has chosen the crisis, and that is now the thing being measured. The distributive issue is the language of the joint statement: face, not substance. The compatible issue is the military deconfliction hotline, which a fixed-pie negotiator will trade away — the one mechanism that prevents the next accident.

Both cases carry the same planted structure, so the metrics are directly comparable across them.

## Where the numbers come from, and where they don't

The point schedules are authored, not measured, and the writeup says so
throughout. But the *ordinal* structure — which issue plays which role, which
side cares more — was tested against 43 primary documents read in full, and it
did not survive intact. Nine of twelve cells confirmed, two partial, one
contradicted. Both sides in fact rank export controls first, so the log-roll
pair lacks opposed intensity; fentanyl precursor cooperation turns out to be
purchased rather than shared, so the compatible issue is not compatible.

The payoffs were left unchanged, and the findings reported instead. The
validator fails on exactly those two checks when the corrections are applied,
which is the behaviour it was written for. The full matrix, with quotations and
per-cell confidence, is in `SOURCES.md`; the corpus is reproducible from a
manifest and checksummed.

Four claims of my own were retracted along the way, including one carried
through two drafts on a source that said the opposite of what I attributed to
it. They are listed rather than quietly fixed, because how often a method
catches its own errors is evidence about the method.

## Status

The harness is complete, verified offline, and runs end to end against a deterministic mock with no API keys. Results against live models populate the same report and microsite. Cases are data: a new scenario is a YAML file of issues, private point schedules, BATNAs, and frames, and the validator refuses it if the planted structure isn't reachable — which is how writing the second case surfaced a bug in the validator itself, where log-roll direction was being inferred from the order issues appeared in the file rather than from the point ranges.

Repository, full case files, validator output, and the report: [github.com/…](.) — see `README.md`.
