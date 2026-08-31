# Track II

**Two frontier models negotiate a multi-issue diplomatic package under private point schedules, and the deal they reach is scored against the mathematically computable Pareto frontier.**

An entry for [ChinaTalk's $25k *Evals for the Situation Room* contest](https://www.chinatalk.media/p/25k-contest-evals-for-the-situation).

---

## Two lines from the brief

The contest post names the capability gap as decisions about **"whether to escalate, how to negotiate, or what to believe."** Of those three, *how to negotiate* is the one with no scored benchmark at all. Escalation has CFPD, WarAgent, Rivera et al. Belief-formation has forecasting work. Negotiation has escalation-tendency measurement standing in for it.

The same post names a second gap, plainly: **"none of the three projects linked here evaluated Chinese models, for example."**

Track II is built against both. It scores negotiation on a computable optimum, and it runs US and Chinese models on the same task — in English *and* in Mandarin, so prompt language is separated from model origin rather than confounded with it.

## The problem this solves

Every existing foreign-policy eval hits the same wall, and each says so out loud.

- **[CFPD](https://arxiv.org/abs/2503.06263)** (CSIS + Scale AI) builds 400 scenarios and swaps actors into 66,473 observations — then explicitly abandons correctness, because foreign policy has no single right answer. It measures *tendencies*: aggression vs. restraint, intervention vs. diplomacy. Rich descriptive data, but no performance axis. You can say what a model prefers. You can never say whether it is any good.
- **CivBench / Civ V** gives real outcomes and genuine interactivity, but as ChinaTalk's own write-up concedes, a game tells you *what* happened without telling you *why* — and strategic skill is entangled with knowing Civ V.
- **Scoring against declassified NIEs** has real ground truth, but every frontier model already knows the Sino-Soviet split happened.

So there is no eval that is interactive, objectively scored, *and* uncontaminated.

## The unlock

That exact problem — how to score negotiation quality when there is no right answer — was solved decades ago by the negotiation-teaching literature. Kellogg DRRC and Harvard PON multi-issue cases ship with **private point schedules** for each side. Once every player has a private cardinal utility function over a discrete issue space, you get for free:

- an enumerable outcome space,
- a computable **Pareto frontier**,
- a computable **Nash bargaining solution** and Kalai–Smorodinsky point,
- a per-side **BATNA**, and therefore
- an objective answer to "how well did this player do", cleanly separable into **value creation** (was the pie maximised?) and **value claiming** (what share did I take?).

This dissolves the dead end CFPD declared unsolvable — you get tendencies *and* a performance score, from the same run.

**On novelty, precisely.** The apparatus itself is not new to LLM research: Abdelnabi et al. (NeurIPS 2024) already built a scoreable multi-issue negotiation testbed on *Harborco*, a Harvard PON case, with per-role secret scores and Pareto analysis. What Track II adds is **exactness and control** — two parties instead of six, so the frontier is enumerated rather than sampled; one payoff structure held invariant across four framings including a Mandarin rendering, so the framing effect is measurable and prompt language is separated from model origin; BATNA violation reported as a hard-error rate; and US *and* Chinese models, which the contest post names as an explicit gap in the existing work. See [RELATED_WORK.md](RELATED_WORK.md) for the full differentiation.

## Quickstart

```bash
python -m venv .venv && .venv/bin/pip install -r requirements.txt
```

Verify the case and the answer key before spending anything — this proves the game is well-posed and every stated solution is re-derived by a solver:

```bash
.venv/bin/python -m trackii.run validate
```

Run the crisis case instead of the grand bargain:

```bash
.venv/bin/python -m trackii.run frames --models mock --case cases/quarantine.yaml
```

Run the whole thing against the offline mock (no API keys, no spend):

```bash
.venv/bin/python -m trackii.run all --models mock --seeds 6 --out results/demo.jsonl
```

Build the report:

```bash
.venv/bin/python -m trackii.report results/demo.jsonl -o site/index.html
```

Run live. Set `ANTHROPIC_API_KEY` and/or `OPENROUTER_API_KEY`, then:

```bash
.venv/bin/python -m trackii.run --list
```

```bash
.venv/bin/python -m trackii.run all --models haiku-4.5,deepseek,qwen,glm --seeds 5 --judge haiku-4.5
```

## What gets measured

Nothing in the headline metrics is graded by a language model. All of it is arithmetic over the private point schedules.

| Metric | What it captures |
|---|---|
| **Pareto efficiency ratio** | joint value achieved ÷ maximum joint value available |
| **Below-BATNA acceptance** | signed a deal worse than its own stated walk-away value — a hard error |
| **Impasse despite a ZOPA** | talks collapsed although 8,150 of 10,800 packages beat both walk-away values — a hard error |
| **Log-roll capture** | traded the issue it cares less about for the one it cares more about |
| **Compatible-issue capture** | two issues have the same preferred settlement on *both* sides; splitting them is pure waste (fixed-pie bias) |
| **Distributive share** | share claimed on the one exactly zero-sum issue |
| **Surplus share** | share of bargaining surplus, normalised by BATNA so it is comparable across seats |
| **Nash distance** | distance from the Nash bargaining solution |

Two of these need no interpretation at all. *"Model X signed a deal worse than walking away in 18% of runs"* is a bright line a policymaker understands instantly — the strategic-reasoning equivalent of a jailbreak rate.

Only two measures use an LLM judge, and it is quarantined: **misrepresentation** (did it lie about its own valuations?) and **coercion**. The judge is handed the player's true point schedule so its verdicts are checkable against ground truth, and any finding whose supporting quote does not literally appear in the transcript is discarded.

## The experiments

**1. Frame ablation — the headline.** The *identical* payoff matrix is run under four skins: abstract placeholders, two low-salience real states (Cabo Verde / Vanuatu), the live US–PRC issue set, and that same issue set prompted **entirely in Mandarin**. Payoffs are defined once and frames supply labels only, so the conditions are provably the same game. The efficiency drop from abstract to salient measures how much political salience degrades strategic reasoning — the explainer asked for exactly this ("strip out any clue that Taiwan or China is involved"). The Mandarin condition turns the model comparison into a clean 2×2 of (US / Chinese lab) × (English / Mandarin prompt): running a Chinese model on an English prompt confounds the two, and every prior benchmark does.

**2. Head to head.** US-lab models against Chinese-lab models on the salient frame, each pairing run in both seat assignments so the result is not an artifact of which side of the table a model sat on.

**3. Label swap.** National labels attached to the opposite structural role, so a model must advance interests that cut against its priors about that actor. Payoffs untouched.

**4. No-communication ablation.** The same close with zero rounds of dialogue. If models that never talk score as well as models that negotiate, the benchmark is not measuring negotiation. Reproduction studies of Abdelnabi et al. found exactly that failure on their testbed, so it is reported openly here rather than left for a reviewer to find.

**Control battery.** Eight games with provable solutions — strict dominance, payoff dominance, best response to a commitment, mixed strategy, iterated dominance, backward induction through a non-credible threat, the value of destroying your own options, and a Pareto-dominated equilibrium. Each is asked three ways: as a bare matrix, as a **named** textbook game ("this is the Prisoner's Dilemma"), and dressed as a US–China scenario — with identical numbers throughout. The named condition isolates recall from computation, replicating the memorisation split from Equilibrium Residuals.

The control is what makes the headline causally interpretable. On its own it is a scripted eval with an answer key, the weaker genre. Its job is to establish whether a model can solve a given structure *at all* in the abstract. Only then does failure on the same structure under political framing support a claim about framing rather than about capability.

## Why you should believe the numbers

This is the part most benchmarks skip.

- **The case is validated before any model is called.** `trackii/validate.py` brute-forces all 10,800 packages and asserts 15 properties: the ZOPA is non-empty but not trivial, both sides can be pushed below BATNA, the frontier is non-degenerate and has a distributive dimension, each compatible issue really is compatible, the distributive issue is exactly zero-sum, the log-roll creates joint value, that surplus is compensable via the distributive issue, and the split-the-difference baseline leaves real headroom (it scores 88%, so the eval can actually discriminate).
- **The answer key is re-derived, not asserted.** `trackii/solved_games.py` ships solvers for dominance, pure and mixed Nash, IESDS, and backward induction, and every stated answer must match the solver output before the battery runs. Writing this caught a real error: my first `commitment_value` game gave the committing player the same payoff either way, so the stated answer was simply wrong.
- **The frame invariant is structural, not aspirational.** Payoffs live in exactly one place. Frames cannot alter them, only label them. Sequential games are asserted to contain no digits in their prose, so every number comes from the shared outcome table.
- **There is a null control.** The mock client ignores prompt content, making it frame-blind by construction, and a test asserts it scores *identically* across all three frames. If the harness itself leaked a framing artifact — prompt lengths, option ordering, seed consumption — that test would fail.
- **Grading does not penalise notation.** A model answering `50%`, `1/2`, or `.5` is marked correct. Strictness there would measure formatting compliance, not game theory.
- **87 tests**, including cross-checks of the fast Pareto frontier against the naive O(n²) definition and of every solver against textbook games with known solutions. Writing case 2 caught a bug in the validator itself: log-roll direction was inferred from the order issues appeared in the file rather than from the point ranges, so a case declaring its pair the other way round was scored against the wrong trade.

```bash
.venv/bin/python -m pytest tests/ -q
```

## Findings

Not yet run against live models — the harness is complete and verified offline, and the results in `site/` are from the deterministic offline mock. Live results populate the same report and microsite.

The mock's flat 78% across all three frames is the null control doing its job: a frame-blind player shows exactly zero framing tax.

## The two cases

| | **The Package Deal** | **The Quarantine** |
|---|---|---|
| Situation | US–PRC grand bargain, no time pressure | Taiwan Strait quarantine, live crisis |
| Issues | 7 (10,800 packages) | 5 (1,200 packages) |
| BATNAs | Moderate and asymmetric | **Low for both** — no deal means the crisis continues |
| Headline failure | Below-BATNA acceptance | **Impasse** — holding out means choosing the crisis |
| Distributive issue | Section 301 tariffs | The public statement: face, not substance |
| Compatible issue | Fentanyl precursor enforcement | The military deconfliction hotline |

The first is deal-making; the second is crisis management. Both carry the same planted structure — compatible issue, log-roll pair, exactly zero-sum issue, interior optimum — so the metrics are directly comparable across them.

## Layout

```
cases/
  package_deal.yaml     six-issue grand bargain: payoffs once, four frames of labels
  quarantine.yaml       five-issue crisis case, low BATNAs
  solved_games.yaml     eight provable games, up to three framings each
trackii/
  case.py               loading, role-sheet rendering
  scoring.py            frontier, Nash, KS, all objective metrics
  validate.py           15 structural checks on the case
  solved_games.py       game solvers + the control battery
  engine.py             the negotiation protocol
  judge.py              quarantined LLM judge, quote-verified
  models.py             Anthropic / OpenRouter / deterministic mock
  run.py                experiment runner
  report.py             results.jsonl -> self-contained HTML
tests/                  87 tests
```

## Design notes

- The outcome space is 5×4×5×3×3×4×3 = 10,800 packages, small enough to enumerate exactly. The frontier is brute-forced, never approximated.
- Free-form dialogue, structured commitment: models talk however they like and commit through a parsed JSON package.
- Who speaks first and who closes are randomised per run and recorded, because the last mover in a take-it-or-leave-it close holds an advantage that would otherwise contaminate the model comparison.
- Full transcripts are logged, so the *why* is auditable — the thing games alone don't give you.
- Temperature and round budget are fixed and reported. No constraint-stacking to manufacture low scores.

## Adding a case

Cases are data. Write a YAML file with issues, per-role point schedules, BATNAs, and frames; run `python -m trackii.run validate --case yours.yaml`. If the planted structure isn't reachable, the validator will say so before you spend anything.

## Licence

MIT.

## Where the point schedules come from

**They are synthetic.** They are authored, not measured — not derived from any
licensed DRRC/PON exercise, any dataset, any expert elicitation, or any
published source. They are **not** a claim about real-world preferences: that
semiconductor controls carry 40 points for OMEGA does not assert what Beijing
actually values relative to tariffs.

The method is to design backwards from the metrics. Each issue is assigned a
structural role from the negotiation-teaching tradition — compatible issue,
log-roll pair, pure distributive issue, interior optimum — and then magnitudes
are tuned until every planted trap is both reachable and detectable: splitting
the compatible issue must destroy enough joint value to move the efficiency
ratio, below-BATNA must be reachable without being routine, the naive baseline
must leave real headroom. The 15 checks in `validate.py` are the specification
that process targets, not a test applied afterwards.

What is defensible is the **ordinal** structure — which issue plays which role,
and which side cares more about what. The cardinal values are not claims; they
are chosen to make the structure work. That is the deeper reason instance
sampling matters: a finding that survives many independently drawn magnitude
sets satisfying the same structural spec is a property of the structure rather
than of one author's arithmetic.

**Known limitation.** Assigning real issues to structural roles rests on the
author's judgment alone. Independent expert ranking of issue intensities per
side would strengthen it, and has not been done.

## Instance sampling

A single hand-authored payoff structure gives you n=many on conversations and
n=1 on games — seeds vary the dialogue, not the problem, so any model
difference could be an artifact of one draw. The sampler turns a case into a
family of instances:

```bash
.venv/bin/python -m trackii.sample --n 10 --seed 0
```

```bash
.venv/bin/python -m trackii.run frames --models haiku-4.5,deepseek --seeds 3 --instances cases/instances
```

The design template is fixed — which issue is compatible, which pair carries
the log-roll, which is exactly zero-sum, which has an interior optimum. Only
the magnitudes move, and each option's rank within its issue is preserved, so
`best_for`, monotonicity and the interior peak all survive rescaling. **Every
draw must pass the full case validator before it is emitted**, which makes
`validate.py` the acceptance test: an instance that ships is provably
well-posed, exactly like the authored one. Ten instances drew from 21
attempts, spanning max joint 145–187 and a naive baseline of 68–87%.

Instance is a **blocking factor**: one draw is held fixed across every frame,
model and seat assignment. That preserves the frame-ablation invariant and
makes the design paired — the framing tax is computed *within* each instance
and only then averaged, so instance difficulty cancels rather than inflating
the variance. The report shows mean ± spread across instances.

## The evidence base

The point schedules are **authored, not measured** — see
[`SOURCES.md`](SOURCES.md) for exactly what that does and does not mean. The
*ordinal* structure, though, was tested against primary sources: 43 documents,
4.7 million characters, downloaded and read in full under the retrieval protocol
in [`RESEARCH_PLAN.md`](RESEARCH_PLAN.md) §5A.

| | |
|---|---|
| [`SOURCES.md`](SOURCES.md) | The 12-cell matrix — direction and intensity for each issue on both sides — with quotations, citation locators, evidence tier and per-cell confidence. **9 confirmed, 2 partial, 1 contradicted**, and the case files were then rewritten to follow the record. |
| [`PROPOSAL.md`](PROPOSAL.md) | What the findings imply for the case files, and why no payoff was changed. Includes four retracted claims of my own. |
| [`RESEARCH_PLAN.md`](RESEARCH_PLAN.md) | The method: evidence hierarchy, coding protocol, retrieval protocol, effort tiers, approval gate. |
| [`research/CONCORDANCE.txt`](research/CONCORDANCE.txt) | How far independent sources agree, per cell. 37 judgements, 68% overall. Regenerate with `research/concordance.py`. |
| [`research/MANIFEST.md`](research/MANIFEST.md) | Every source URL, and how to rebuild the corpus. |
| [`research/CORPUS.sha256`](research/CORPUS.sha256) | SHA-256 for all 43 extracted texts. |

**Verifying a quotation.** Rebuild the corpus, then grep it:

```bash
./research/fetch.sh < research/manifest_all.txt
shasum -c research/CORPUS.sha256
tr '\n' ' ' < corpus/nss_2025.txt | grep -o '.\{90\}align their export controls.\{40\}'
```

The `tr` matters. Documents extracted from PDFs wrap mid-sentence, so a plain
`grep` for a quotation that spans a line break returns nothing — which looks
exactly like a fabricated citation. Normalise the whitespace first.

Government documents (US public domain, PRC official texts) are committed here.
Third-party copyrighted extractions are **not redistributed** — the manifest and
checksums make them reproducible without that. See
[`research/MANIFEST.md`](research/MANIFEST.md).

**What this evidence base is not.** One coder, so no second rater and no
Krippendorff's α; the concordance figure measures agreement among *sources*, not
among raters, and is not a substitute. Nomination was adversarial — sources were
sought specifically to break the findings, and succeeded against the strongest
one — but it was not independent.
