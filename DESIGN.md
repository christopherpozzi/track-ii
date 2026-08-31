# Evals for the Situation Room — Design Plan

**Contest:** ChinaTalk, $25k. **Deadline: September 1, 2026** (~2 days from 2026-08-30).
**Judges:** John Chen (Arizona / CivBench), Liam Wilkinson (Tony Blair Institute), Tony Stark (WarTalk), Jordan Schneider (ChinaTalk), Kevin Troy (Anthropic).

---

## 1. What the organizers actually said they want

From the two ChinaTalk posts, close-paraphrased:

**The core problem.** For coding and math we have a body of evidence and a working intuition about model reliability. *Strategic decision-making has no equivalent body of evidence and no equivalent intuition.* They want to know what models are useful for today, what they're terrible at, and how to track that over time.

**Stated design principles (from the "explained" post):**

| Principle | Source | Implication for us |
|---|---|---|
| Best evals are explainable in 1–2 sentences | Florian Brand | One-line pitch must land |
| Know precisely what capability you're measuring before you build | John Chen | Pre-register the metric |
| Don't stack artificial constraints (token caps, no tools, timers) to force low scores — that measures the constraint, not the model | — | Give models room; report constraints |
| Beware conflating reasoning vs. alignment vs. instruction-following | — | **Needs an explicit ablation** |
| Consider stripping real-world referents (Taiwan → "Cape Verde") to isolate alignment from reasoning | — | This is a *direct invitation*. Build it in. |
| Prefer dynamic/interactive environments where models *enact* what they advocate, over scripted Q&A with answer keys | — | Head-to-head, not MCQ |
| Test behavior when losing / under pressure / off-distribution | — | Include a losing-position variant |
| Consider evals personalized to specific actors with different values and goals | — | Per-role private preferences |
| Avoid "vibe-coded benches" that don't faithfully represent the concept | — | Formal, computable scoring |

**Their brainstorm list:** head-to-head in Paradox grand strategy games; models in EVE Online doing guild infiltration/recruitment; replaying the Cuban Missile Crisis with the model in EXCOMM; scoring models against declassified NIEs (e.g. predicting the Sino-Soviet split).

**Prior art they cite:** Lily's TaiwanBench ("an example of what one person can accomplish" — this is the bar), Good Start Labs' Diplomacy work, CSIS/Scale's Critical Foreign Policy Decisions (CFPD) Benchmark, WarAgent, CivBench.

**Submission bar:** *"The best submissions will not just be 'concepts of a plan,' but would actually have at least some of the concrete material to be used in the evals."* No AI experience required.

---

## 2. The gap I want to attack

Every existing entrant in this space hits the same wall, and they all say so out loud:

- **CFPD (CSIS/Scale)** — 400 scenarios, 2–3 choice MCQ, actor-swapped into 66,473 observations. They explicitly abandon correctness: foreign policy has no single right answer, so they measure *tendencies* (aggression vs. restraint, intervention vs. diplomacy). Rich descriptive data, **no performance axis**. You cannot say a model is *good* at this — only what it *prefers*.
- **CivBench / Civ V (John Chen)** — real outcomes (victory/defeat), genuinely dynamic. But as the post concedes, games give you the outcome without telling you *why*, and Civ V is a thick, idiosyncratic simulation whose strategic content is entangled with knowing Civ V.
- **NIE scoring** — real ground truth, but static, single-shot, and badly contaminated: every frontier model already knows the Sino-Soviet split happened.

**So the gap is: no one has a foreign-policy eval that is simultaneously (a) interactive, (b) objectively scored against a computable optimum, and (c) uncontaminated.**

### The unlock

That exact problem — score negotiation quality when there is no "right answer" — was solved decades ago by the negotiation-teaching literature. **Kellogg DRRC and Harvard PON multi-issue cases ship with private point schedules for each side.** Once every player has a private cardinal utility function over a discrete issue space, you get for free:

- an enumerable outcome space,
- a computable **Pareto frontier**,
- a computable **Nash bargaining solution** and **Kalai–Smorodinsky** point,
- a per-side **BATNA / reservation value**,
- and therefore an *objective, non-judgmental* answer to "how well did this player do," separable into **value claiming** (my share) and **value creation** (was the joint pie maximized).

Nobody has pointed that apparatus at frontier models in a national-security setting. It resolves CFPD's stated dead end — you get tendencies *and* a performance score, from the same run.

**One-sentence pitch:** *Two frontier models negotiate a multi-issue diplomatic package under private point schedules, and we score the deal they reach against the mathematically computable Pareto frontier.*

That is the 1–2 sentence test, passed.

### Why this fits you specifically

Game theory (2x2 Nash) + DRRC/PON negotiation cases + Economics + Chinese + Palantir + a shipped OSINT dashboard. Almost nobody entering this contest can author a *correct* integrative case with a planted compatible issue and a planted log-roll — that's a specific, teachable craft you have and most ML people don't. The judges asked for domain people, not AI people.

---

## 3. Options

### Option A — **Track II**: multi-issue crisis negotiation under private point schedules ⭐ RECOMMENDED

Two models, each given a private role sheet: a set of issues, discrete options per issue, private points per option, and a BATNA. They negotiate free-form for N rounds, then each submits a structured final package. Agreement requires both to submit the same package.

The case is authored (DRRC-style) so the payoff structure contains deliberate traps:
- a **compatible issue** — both sides secretly want the same outcome, but each assumes conflict (tests fixed-pie bias),
- a **log-roll pair** — issue X is worth 3x more to A, issue Y worth 3x more to B (tests integrative trading),
- a **purely distributive issue** — zero-sum (tests value claiming),
- **asymmetric BATNAs** — one side can credibly walk (tests power recognition and below-BATNA discipline).

Scored fully automatically:

| Metric | What it measures | Ground truth |
|---|---|---|
| Own points | Value claiming | Exact |
| Joint points ÷ max joint points = **Pareto Efficiency Ratio** | Value creation | Exact (brute force) |
| Distance to Nash Bargaining Solution | Fairness/efficiency jointly | Exact |
| **Below-BATNA acceptance rate** | Hard error: accepted a deal worse than walking away | Exact |
| **Impasse-with-ZOPA rate** | Hard error: failed to close a deal that existed | Exact |
| Log-roll rate | Did it trade low-value for high-value issues | Exact |
| Fixed-pie error rate | Did it "split the difference" on the compatible issue | Exact |
| Misrepresentation rate | Did it lie about its private sheet | LLM judge, checked against the sheet |
| Coercion / escalation language rate | Tendency (CFPD-comparable) | LLM judge |

Note the two hard-error metrics. *"Model X accepted a deal worse than not dealing at all in 18% of runs"* is a bright-line failure a policymaker understands instantly, with zero subjectivity — the eval equivalent of a jailbreak rate. That's the headline.

**The three experiments that make this a paper, not just a harness:**

1. **Frame ablation** — run the *identical payoff matrix* under three skins:
   (i) abstract (Country A / Country B, Issue 1–6), (ii) neutral-real (Cape Verde / Vanuatu), (iii) live-salient (US / PRC over Taiwan, export controls, fentanyl precursors).
   The drop in Pareto efficiency from (i) to (iii) is a clean measurement of **how much political salience degrades strategic reasoning** — reasoning vs. alignment, disentangled, exactly as the post asked for.
2. **Role-swap symmetry** — same model plays both seats. Does it get systematically better outcomes as Washington than as Beijing on an identical payoff structure? That's national bias with a *number attached*, a strict improvement on CFPD's tendency measurement.
3. **US vs. Chinese models head-to-head** — Claude/GPT/Gemini vs. DeepSeek/Qwen/Kimi on the same case. Maximum ChinaTalk resonance, and a real finding either way.

- Ground truth: **exact and computable**
- Contamination: **none** (novel synthetic payoffs)
- Dynamic/interactive: **yes** — models enact, not opine
- Buildable in 2 days: **yes**
- Novelty: **high** — no one has transplanted the DRRC apparatus here

**Risk:** the case must be authored *correctly*. A badly balanced points schedule produces a degenerate game. Mitigation: a validator that brute-forces the outcome space and asserts the ZOPA is non-empty, the frontier is non-trivial, and the planted traps are actually reachable, before any model is called.

---

### Option B — **Solved Game**: equilibrium battery with narrative skins

Models face 2x2 and small extensive-form games with a unique, provable solution (Nash / subgame-perfect / dominant strategy), presented either as a bare payoff matrix or dressed as a strategic narrative (Taiwan quarantine, chip export controls, escalation ladder). Measure equilibrium-identification accuracy, and the *accuracy gap* between the bare matrix and the narrative skin.

- Ground truth: **perfect** — it's a solved-game solver
- Buildable: **very fast** (~half a day)
- Novelty: **medium**. It is scripted Q&A with an answer key, which the judges explicitly said they find less interesting than dynamic environments.

**Verdict: don't ship alone — ship as Option A's control layer.** It gives you the baseline claim *"the model can solve this structure in the abstract, and still fails it when you call one player China"* — which is what makes the Option A frame-ablation result causally interpretable rather than just suggestive. Cheap to add, disproportionately strengthens A.

---

### Option C — Sequential escalation ladder / EXCOMM replay

Formal crisis-bargaining game tree (brinkmanship, incomplete information about resolve), models as EXCOMM. Measures escalation discipline, off-ramp construction, first-use thresholds.

- Ground truth: medium — equilibria exist but are sensitive to assumed beliefs, so scoring gets contestable
- Overlaps heavily with WarAgent and the judges' own Civ V nuclear findings — you'd be confirming John Chen's result on his turf
- Buildable: medium
- **Verdict: strongest *third* case inside the Option A harness later, not the spine.**

---

### Option D — Declassified NIE forecasting

Score models against declassified National Intelligence Estimates on historical questions.

- Ground truth: real, but **badly contaminated** — models know the answers
- Effort: dominated by archival data collection, not modeling
- **Verdict: not in 2 days, and contamination is close to fatal without heavy counterfactual construction.**

---

## 4. Recommendation

**Ship Option A as the spine, with Option B as an embedded control condition.**

Branding: **Track II** — the actual diplomatic term for unofficial back-channel negotiation, and a pun on the eval being a second track alongside capability benchmarks.

Deliverable: public GitHub repo + a TaiwanBench-style microsite (reuse your Vercel/Next.js setup from `nuke-osint-dashboard`) + a ~1,500-word writeup with the three headline findings.

---

## 5. Prototype architecture

```
situation-room-eval/
  cases/
    taiwan_package.yaml       # 6 issues, 3 frame variants, private schedules
    validate.py               # brute-force: ZOPA non-empty, traps reachable
  trackii/
    engine.py                 # alternating dialogue, N rounds, structured final offer
    scoring.py                # Pareto frontier, Nash/KS solutions, all hard metrics
    judge.py                  # LLM judge — ONLY for misrepresentation & coercion
    models.py                 # Anthropic + OpenAI + OpenRouter (DeepSeek/Qwen) adapters
    run.py                    # matrix runner -> results.jsonl
    report.py                 # -> static HTML + charts
  results/
  site/                       # microsite
```

Design notes:
- Issue space stays small enough to enumerate exactly (6 issues x ~4 options ≈ 4,096 packages) — the frontier is brute-forced, never approximated. No "vibe-coded bench."
- Final offers are extracted via structured output / tool use, not regex over prose. Free-form talk, structured commitment.
- **The objective metrics never touch an LLM judge.** The judge is quarantined to the two genuinely subjective measures, and its verdicts are checkable against the private sheets.
- Every run logs the full transcript, so "why" is auditable — the thing the post says games *don't* give you.
- Temperature and round budget fixed and reported; no artificial constraint-stacking.

**Scope for 2 days:** one case authored to full DRRC quality x 3 frame variants x 4–6 models x ~10 seeds, plus the harness generalized so cases 2 and 3 are just YAML.

---

## 6. Open decisions

1. Which models to include (cost vs. the China angle).
2. Whether to author the flagship case as US–PRC directly, or as an abstract case *with* a US–PRC skin (the latter is required for the frame ablation, so: the latter).
3. Whether to build the microsite or ship repo + writeup only, if time runs short.
