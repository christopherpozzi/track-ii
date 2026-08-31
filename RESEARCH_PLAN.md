# Research plan: sourcing the issue structure

**Status: plan for review. No research executed yet.**

The point schedules are currently authored. What is defensible about them is the
*ordinal* structure — which issue plays which structural role, and which side
cares more about what — and that structure rests on one person's judgment. This
plan replaces that judgment with sourced, citable evidence.

---

## 1. Scope: what gets sourced, and what deliberately does not

Three things need evidence. They are not equally tractable and should not be
treated as one task.

| Output | What it is | Feeds |
|---|---|---|
| **(a) Direction** | For each issue and side, which listed settlement that side prefers | Whether an issue is *compatible* or conflicting |
| **(b) Intensity** | For each issue and side, how much it cares *relative to its own other issues* | Log-roll pairing; which side's range is wider |
| **(c) Option ladders** | The realistic discrete settlement points on each issue | Frame labels; scenario realism |

**What is deliberately NOT sourced: the cardinal magnitudes.** No document tells
you Taiwan arms sales are worth 40 points rather than 38. Sourcing them would be
false precision dressed as rigour. Magnitudes stay synthetic and
instance-sampled — which is exactly what the sampler is for. Sourcing fixes the
*structure*; sampling shows the findings do not depend on the *numbers*.

**A useful property:** sourcing the framing from public documents does not
contaminate the answer key. Models may well have seen the source documents, but
the payoffs remain synthetic, so the computable optimum stays uncontaminated.
Realism improves at no cost to the thing that makes this eval scoreable.

---

## 2. Prior decision: whose preferences does each seat represent?

This has to be settled before any coding, and it is currently unstated.

The United States is not one actor. The executive branch (NSC / State / USTR),
the Department of War / Defense, and Congress (USCC, the House Select Committee)
routinely hold different positions, and Congress is systematically more hawkish
than the negotiating position.

**Proposed convention, to be confirmed:**

- **DELTA = the executive-branch negotiating position.** It is the actor that
  would actually be at the table.
- **Congress enters through the BATNA, not as a second preference vector.** A
  package Congress would reject is worth less because it may not survive — which
  is modelled as a *higher* US reservation value, not as different issue
  intensities. This is both more realistic and simpler than a three-player game.
- **OMEGA = the PRC state position** as expressed through MOFA, MOFCOM, the
  State Council and Politburo output, with an explicit caveat that internal PRC
  preference heterogeneity is far less observable than US heterogeneity.

Any alternative convention is defensible; what is not defensible is leaving it
implicit.

---

## 3. Evidence hierarchy

Sources are not equal evidence for *intensity*. Ranked strongest first:

**Tier A — revealed preference through actual concessions.** What each side has
actually traded away in real episodes: the Phase One agreement (Jan 2020), the
November 2023 Xi–Biden summit (resumed fentanyl cooperation and mil-mil
channels), subsequent tariff and export-control episodes. If a side gave up X to
obtain Y, that is strong evidence it ranks Y above X. This is the gold standard
and should carry the most weight.

**Tier B — explicit linkage statements.** When officials publicly tie two issues
together ("progress on X depends on movement on Y"), that reveals a perceived
exchange rate. This is the most direct available evidence for **log-roll
pairing** specifically, and it is under-used in this kind of work.

**Tier C — declared salience.** Prominence in authoritative top-level documents.
Measures what a side *says* matters. Weaker than revealed preference — but it is
what the counterpart observes, which is not nothing in a negotiation model.

**Tier D — expert assessment.** Think-tank and academic analysis. Best used to
triangulate and to catch what primary sources omit.

**Tier E — journalism.** Strongest for chronology and for insider accounts of
what was actually traded; weakest as a direct intensity claim.

---

## 4. Source register

### US government
- National Security Strategy; National Defense Strategy (Department of War / Defense)
- State Department: bureau fact sheets, Secretary-level meeting readouts
- USTR: Section 301 reports, the Phase One agreement text
- Commerce / BIS: Entity List actions, FDPR rulemaking — the primary source for **export-control option ladders**
- Treasury / OFAC sanctions actions
- **USCC Annual Report to Congress** — the single most comprehensive recurring assessment; high value per unit effort
- House Select Committee on the CCP: reports and hearing transcripts — code as a *distinct congressional actor*, not as executive priority
- Congressional Research Service reports — non-partisan, unusually well-sourced

### PRC government and party
- Party Congress work reports (20th Party Congress); NPC work reports
- MOFA press-conference transcripts and readouts
- MOFCOM statements on trade and export controls
- State Council white papers (including the 2022 Taiwan white paper)
- Statutory texts: Export Control Law, Anti-Foreign Sanctions Law

### Think tanks
RAND (force posture, wargaming) · Brookings · CSIS ChinaPower and Futures Lab
(also the CFPD authors) · Carnegie · Stimson · **ChinaTalk** · MERICS ·
Peterson Institute (trade) · Asia Society Policy Institute · CNAS

### Academia
Harvard Belfer (HKS) · Johns Hopkins SAIS · Tufts Fletcher · Stanford
(Hoover / APARC / DigiChina) · UC San Diego 21st Century China Center ·
journals: *International Security*, *Foreign Affairs*, *The China Quarterly*

### News
NYT · WSJ · *The Economist* · FT · Reuters · Bloomberg · Nikkei Asia ·
Caixin (relatively independent PRC business reporting) · SCMP (with ownership
caveat) · Xinhua, *People's Daily*, *Global Times* (state outlets — see below)

---

## 5. Two handling rules that materially affect validity

**State media are Tier C, never Tier A.** Xinhua, *People's Daily* and *Global
Times* are strong evidence of *declared* priority and of what Beijing wants
observed; they are weak evidence of true reservation values. *Global Times* is
more nationalist and less authoritative than *People's Daily* and should be
weighted below it. Coding them as revealed preference would systematically
distort the PRC column.

**Source abundance is not intensity.** US sources are plentiful, adversarial and
public; PRC sources are fewer and centralised. Naive frequency counting would
produce confident US rankings and noisy PRC ones purely as an artifact of
availability. Mitigations: use **matched document classes** (NSS ↔ work report,
State readout ↔ MOFA readout), **cap documents per cell** so abundance cannot
masquerade as intensity, and record per-cell coder confidence so thin PRC cells
are visible rather than hidden.

---

## 5A. Retrieval protocol — mandatory

**For each source, save it as a file, download the entire text document, and read
every line.**

This is not a style preference. It was added after two research passes produced
retracted findings, and it is the single highest-value rule in this plan.

### Why

Summarisation tools — including any fetch tool that answers a prompt against a
page rather than returning the page — interpose a model between the researcher
and the document. That model decides what is relevant *before* the researcher
sees it. Three failure modes were observed directly:

| Failure | Instance |
|---|---|
| **Silent truncation** | The 20th Party Congress passage on the use of force was returned ending at 分裂活动, dropping "，绝非针对广大台湾同胞" — a qualifier that changes the sentence |
| **Frequency distortion** | The USCC executive summary yields "tariff" 9 times; the full 745-page report yields 249. An intensity ranking built on the summary undercoded tariffs by an order of magnitude |
| **Prevalence collapse** | 以台制华 occurs 6 times in the 2022 white paper and is its organising frame; the summary surfaced 1 instance, so the frame was invisible |

A fourth failure is not the tool's fault but is enabled by it: a document can be
downloaded and never opened. The Phase One agreement sat on disk for a full pass
before anyone read it, and it turned out to contain the pass's strongest finding.

### The procedure

1. **Fetch to disk.** `curl -sL -o <corpus>/<slug>.<ext> <url>`. Never analyse a
   document that exists only inside a tool response.
2. **Convert to text and keep the text file.** PDFs via `pypdf` with page
   markers preserved; HTML via tag-stripping. The `.txt` is the artifact of
   record and is what citations resolve against.
3. **Verify the conversion.** Report page and character counts. A 745-page report
   that converts to 40k characters has failed silently.
4. **Read it.** For short documents (< ~40k characters), read end to end. For long
   ones, read structurally: headings, then term frequencies across the *whole*
   file, then every hit in context for each of the twelve cells. Frequency counts
   must be taken over the full text, never a summary or excerpt.
5. **Quote from the file, not from memory or from a tool's paraphrase.** Every
   quotation entering `SOURCES.md` must be recoverable by `grep` against the
   stored `.txt`.
6. **Verify quotations already in hand.** Before citing anything carried over from
   an earlier pass, grep it against the source. Record misses as corrections.
7. **Log the corpus.** Filename, page/character count, retrieval date, URL.

### Consequence for effort estimates

This protocol makes retrieval slower and extraction faster, and it makes the
tiers in §9 *more* achievable rather than less: the expensive step was never
reading, it was re-doing work after a summary-based finding collapsed. Two
retractions in this project cost more than reading the documents would have.

---

## 6. Coding protocol

1. **Fix the issue set** (already defined: six issues for the package deal, five
   for the quarantine).
2. **Build a matched corpus**: target 6–10 documents per issue × side cell,
   balanced across tiers, within a stated window (proposed: January 2023 to
   present — state it, because priorities move).
3. **Code two variables per cell:**
   - *Direction* — which listed option this side would choose absent constraint.
   - *Intensity* — 5-point scale with anchors:

   | | Anchor |
   |---|---|
   | **5** | Named a core or vital interest; costs borne to defend it; described as non-negotiable |
   | **4** | Repeatedly prioritised at top level; concessions sought elsewhere to protect it |
   | **3** | Consistently raised; tradeable |
   | **2** | Raised but low priority; traded away in past episodes |
   | **1** | Rarely raised; conceded readily |

4. **Two independent coders.** Compute Krippendorff's α; adjudicate any cell
   where coders differ by ≥ 2. Treat **α ≥ 0.67** as the threshold for reporting
   conclusions as tentative, and α ≥ 0.80 for reporting them plainly.
5. **Open nomination step.** Coders may nominate issues that *should* have been
   in the set. Without this the exercise can only confirm the existing design,
   never correct it — a circularity worth designing out.

---

## 7. Mapping codes back to structure

- **Compatible issue** — both sides' direction codes point to the *same* option.
- **Log-roll pair** — the two issues whose intensity ranks are most strongly
  opposed across sides; Tier B linkage statements are direct corroboration.
- **Pure distributive issue** — directions opposed, intensities close to equal.
- **Interior optimum** — a side's direction code lands on a middle option.

**The diff against the current authored case is itself a finding.** If the
evidence says fentanyl enforcement is not in fact compatible, or that the
log-roll pair is export controls and tariffs rather than export controls and
arms sales, then the case should change and the change should be reported.
Publishing "the authored design assumed X; sourced evidence indicates Y"
strengthens the work regardless of which way it falls.

---

## 8. Deliverables

| File | Contents |
|---|---|
| `SOURCES.md` | The issue-intensity matrix. Every cell carries ≥ 2 citations, a tier, and a confidence |
| `research/corpus.csv` | Document register: source, tier, actor, date, URL, issue tags |
| `research/coding.csv` | Per-coder direction and intensity codes, plus adjudications |
| `research/diff.md` | Sourced structure vs. the current authored structure |
| Updated `cases/*.yaml` | Revised design roles and option ladders; magnitudes still synthetic |

---

## 9. Effort tiers

| Tier | Effort | Dependencies | What you get |
|---|---|---|---|
| **0 — load-bearing claims only** | **~12 work hours** (one long day) | **None. Solo.** | Targeted validation of the three structural claims the metrics rest on. See §9.1 |
| **0+ — full ordinal structure** | **~20 work hours** (two half days) | **None. Solo.** | All 12 cells — direction *and* intensity for 6 issues × 2 sides — from primary sources only. Thin triangulation. See §9.4 |
| **1 — elicitation** | ~4 work hours *plus turnaround* | Three other people must reply | Independent expert ranking of issues by intensity per side. Converts "the author judged" into "three subject-matter experts concurred." The dependency makes it unreliable inside a 24-hour window |
| **2 — single-coder review** | **~38 work hours** (2.5–3 focused days) | None | ~30 documents chosen for *coverage*, transparent citations, no reliability statistics. Defensible for a blog-post-grade claim. See §9.3 for the decomposition |
| **3 — full protocol** | ~80 person-hours, **~1.5–2 weeks wall clock** (two in parallel) | Second coder | Two coders, reliability statistics, open nomination, published corpus. The version that would survive peer review |

### 9.1 Tier 0 — the 12–24 hour version

**Do not attempt the full 12-cell matrix in a day.** Attempt instead the three
claims that actually drive the metrics. Everything else is either synthetic by
intention (magnitudes, BATNA levels) or lower stakes (the interior optimum).

| # | Claim under test | Metric it drives | Why it is load-bearing |
|---|---|---|---|
| **1** | The **compatible issue** really is compatible — both sides prefer the *same* settlement on fentanyl enforcement (package deal) / the deconfliction hotline (quarantine) | `compatible_capture`, and the "13 points destroyed for nothing" result | Highest leverage of the three. If the sides do not in fact want the same thing, the fixed-pie finding loses its foundation |
| **2** | The **log-roll pair** is correctly identified *and correctly oriented* — Beijing weights export controls above Taiwan arms sales, Washington the reverse | `log_roll_capture`, and the whole integrative story | Orientation matters as much as membership: reversed intensities invert the trade |
| **3** | The **distributive issue** is the closest thing to a pure transfer | `distributive_share` | Weakest of the three claims and the easiest to check; tariff schedules are well documented |

**Corpus: 12–16 documents, not 60.** Highest yield per hour:

- **USCC Annual Report to Congress** — covers every issue in one place; start here
- National Security Strategy; National Defense Strategy
- 20th Party Congress work report; the 2022 Taiwan white paper
- Phase One agreement text (Tier A: what was actually traded)
- November 2023 Xi–Biden summit readouts, **both sides** — the best available Tier A source for the fentanyl claim, since cooperation was resumed there as part of a package
- 2–4 MOFA / MOFCOM readouts touching export controls
- 2–3 think-tank assessments for triangulation

**Budget:**

| Step | Hours |
|---|---|
| Assemble the corpus | 2 |
| Claim 1 — compatible issue, direction coding both sides | 3 |
| Claim 2 — log-roll orientation (Tier A concessions + Tier B linkage statements) | 3 |
| Claim 3 — distributive issue | 1 |
| Write `SOURCES.md` and `diff.md` | 2 |
| Update YAML if the diff warrants; re-validate; re-sample instances | 1 |
| **Core** | **~12**, with slack to 24 |

**Single coder, so no reliability statistics** — say so plainly and report
per-claim confidence instead. What this buys is not "validated". It is *each
load-bearing structural claim now carries citations, and one was checked
against what the parties actually traded.* That is a real step up from
unsupported judgment, and honest about what it is not.

**If the diff falsifies a claim, that is a result, not a setback.** Report it —
"the authored design assumed fentanyl enforcement was compatible; sourced
evidence indicates otherwise" — and change the case.

### 9.3 Where Tier 2's time actually goes

An earlier draft put Tier 2 at "~1 week" against ~60 documents. That anchored on
*research project* as a unit rather than decomposing the work, and it inflated
both numbers. The corpus is the first thing to cut: you need 3–5 good sources
per cell across 12 cells, but sources overlap heavily — the USCC Annual Report
covers all six issues at once, and so does the work report. **Coverage is the
binding constraint, not volume**, which puts the real corpus nearer 30.

| Step | Hours | Note |
|---|---|---|
| Corpus assembly | 3–4 | Retrieval is fast once you know the source register in §4 |
| ~8 short documents (readouts, statements) | 1.5 | 10–15 min each |
| ~14 medium (think tank, CRS, academic, white papers) | 8 | 30–35 min each |
| ~6 long (USCC, NSS, NDS, work report, Phase One, Taiwan white paper) | 10 | Indexable — chapter TOCs and executive summaries, not cover-to-cover |
| ~4 news pieces for chronology | 0.7 | |
| Coding overhead concurrent with reading | +20% | Logging direction, intensity and citation locators as you go |
| Adjudicating contradictory evidence | 5 | Does **not** parallelise with reading |
| Write-up with citation locators | 4 | Clerical but real: ≥2 citations per cell |
| Diff, YAML update, re-validate, re-sample | 2 | |
| **Total** | **~38** | ≈ 2.5–3 focused days |

**What compresses:** the reading. Targeted extraction against a fixed rubric is
far faster than comprehension reading, and the long documents are indexable.

**What does not:**

- **The PRC column.** Fewer documents, less indexable, signal more indirect,
  and translation checking on top. It plausibly takes as long as the US column
  despite half the sources.
- **Adjudication.** When the USCC and a Carnegie assessment disagree, resolving
  it takes thought and cannot be done while reading.
- **Citation logging.** Every cell needs locators a reader can check.

**Tier 3 was inflated the same way.** Two coders doubles *person*-hours, not
wall clock, if they work in parallel. Adding reliability statistics, the
adjudication round and open nomination puts it at ~1.5–2 weeks elapsed, not
3–4.

**Practical consequence:** at 2.5–3 days, Tier 2 is a realistic post-submission
target rather than a someday item — the natural thing to do if the contest
generates follow-up interest.

### 9.4 Tier 0+ — why more coverage is cheap

Tier 0 and Tier 2 barely differ in *documents*. They differ in **extraction
depth**. The expensive part of any tier is the six long primary documents —
USCC Annual Report, NSS, NDS, the work report, the Taiwan white paper, the
Phase One text — roughly 10 of Tier 2's 38 hours. **Tier 0's corpus already
contains all of them.** What Tier 0 saves is not reading; it is that it asks
three questions of those documents where Tier 2 asks twelve.

That makes the marginal cost of coverage low. Once the USCC report is open and
you are searching it for fentanyl enforcement, coding export controls and
tariffs on the same pass is nearly free. So Tier 0 can be widened from three
claims to the full 12-cell matrix without going back for new sources:

| | Tier 0 | Tier 0+ | Delta |
|---|---|---|---|
| Corpus assembly | 2 | 2 | — |
| Extraction from the same documents | 7 | 10 | +3 (deeper passes, not more sources) |
| Adjudicating contradictions | (folded in) | 3 | +3 (12 cells produce more conflicts than 3 claims) |
| Write-up with citation locators | 2 | 4 | +2 (≈24 citations vs ≈8) |
| Diff, YAML update, re-validate, re-sample | 1 | 1 | — |
| **Total work hours** | **~12** | **~20** | **+8** |

**What Tier 0+ gets you over Tier 0:** direction *and* intensity for every
issue on both sides — the complete ordinal structure, which is the whole
sourceable object. Enough to reassign structural roles with citations rather
than only to confirm or falsify three of them.

**What it still lacks against Tier 2:** the ~14 medium analytic sources (think
tank, CRS, academic — 8 hours). That layer is what provides *triangulation*, so
Tier 0+ carries lower confidence on any cell where the primary sources are
quiet or contradict one another. Report per-cell confidence and the gap is
honest rather than hidden.

**Calendar caution.** ~20 work hours is two half days, not one 24-hour window;
nobody does 20 productive hours in a day. The tier table above is now stated in
*work hours* precisely because my earlier "12–24h" conflated a work budget with
a calendar window — the same conflation that inflated Tier 2 to "a week."

### 9.2 Sequencing

Today is Sunday 30 August; submissions are due Tuesday 1 September. Roughly two
days, and **the live runs are not yet done**.

Tier 0 is therefore not the first call on that time. The runs are what convert
this from a method into a finding; the research improves the provenance of a
case design whose limitations are already documented in the appendix and the
case files. The runs cost ~$10–25 and under an hour of wall clock.

**Recommended order: live runs → writeup → Tier 0 with whatever remains.** A
submission with results and an honest limitations section beats one with
better-sourced assumptions and no numbers.

## 10. Risks and limitations

- **Circularity.** Designing the issue set and then sourcing it means the
  sourcing can validate but not discover. The open-nomination step in §6.5 is
  the mitigation; it should not be dropped for speed.
- **Recency bias.** Priorities move. A stated window is required, and the
  finding is bounded by it.
- **PRC opacity.** Even done well, the PRC column will carry lower confidence
  than the US column. Report the asymmetry rather than smoothing it over.
- **Selection bias.** Source choice is itself a judgment. The corpus register
  exists so a reader can audit and disagree.
- **Ceiling on what this buys.** Even flawless sourcing yields ordinal
  structure, not cardinal values. It removes one of the two soft spots in the
  case design; instance sampling handles the other.

---

## 11. Approval gate — propose before applying

**No research finding is applied to a case without explicit sign-off.** The
research produces a *proposal*, not an edit. This is a hard gate, not a
courtesy: the schedules are the answer key, and silently changing them would
invalidate every result already collected against them.

### 11.1 What gets presented

Before touching any file, produce a proposal containing:

1. **A claim-by-claim verdict.** For each structural claim tested: upheld,
   falsified, or inconclusive — with the citations behind it and a stated
   confidence.
2. **A structural diff.** Which issue changes structural role, and to what:

   | Issue | Current role | Proposed role | Evidence | Confidence |
   |---|---|---|---|---|

3. **A point-schedule diff.** The concrete before/after per issue and side.
   Because magnitudes stay synthetic, most of this should be *re-ordering* and
   *re-ranging*, not re-pricing. Flag loudly if any change is not derivable
   from an ordinal finding — that would mean sourcing has crept into territory
   §1 explicitly excludes.
4. **Blast radius.** What the change invalidates:
   - Which already-collected runs become non-comparable
   - Whether the sampled instances must be re-drawn (they must, if the template
     changes)
   - Whether any published number in the writeup or microsite moves
5. **A recommendation**, including the option to change nothing. "The evidence
   is weaker than the current design assumes, but not strong enough to
   overturn it" is a legitimate and reportable outcome.

### 11.2 What the user decides

Approve, reject, or amend **per change**, not as a block. A finding on the
compatible issue can be accepted while a finding on the log-roll pair is held
for more evidence.

---

## 12. Update scope on approval

Once changes are approved, they propagate to three places. Missing any one of
them leaves the artifact internally inconsistent.

**1. The point schedules and role instructions.** `cases/*.yaml` — the `points`
blocks, the `design_role` tags, and the frame labels that render into the
DELTA and OMEGA role sheets. Then:

- re-run the case validator; a re-roled case may now fail a structural check
  and must be re-tuned until it passes
- **re-draw the sampled instances** — they inherit the template, so a changed
  template invalidates every existing draw
- re-run the null control to confirm the harness still shows zero framing tax

**2. The Appendix: Methodology view.** `trackii/report.py` — the case table, the
provenance section (which currently says the schedules rest on author judgment,
and would become partly sourced), and the Limitations section per §12.1.

**3. The narrative documents.** `README.md`, `WRITEUP.md`, and this plan's
status line.

### 12.2 Evidence standard for the Appendix · Methodology

Updates to the Appendix must be **evidence-bearing, not assertive**. Every
structural claim carries its evidence with it, in the artifact the reader sees —
not in a separate file they are trusted to consult.

Required, per claim:

1. **A direct quotation** from a primary source, in the original language, with a
   translation where the original is not English. Quotations are lifted from the
   stored `.txt` under §5A, never paraphrased from a summary.
2. **An inline citation** naming the issuing body, the document, and the date,
   locating the quote precisely enough to be checked — a section number for a
   structured document (三(四)), a page for a paginated one.
3. **An evidence tier** from §3 (A–E), so a reader can see at a glance whether a
   claim rests on a revealed concession or on a journalist's characterisation.
4. **A confidence level**, since a single coder produces no reliability
   statistics and §6's α is unavailable.

And once, for the whole appendix:

5. **A bibliography.** Every source consulted, whether or not it survived into a
   finding — including sources that *falsified* a hypothesis, which are the most
   informative entries and the easiest to quietly drop. Each entry: issuing body,
   title, date, URL, and the local corpus filename it was read from.

A claim that cannot meet 1–4 is not omitted; it is **marked as authored
judgement** and says so. The distinction between "sourced" and "the designers
decided" is the appendix's main job, and blurring it is worse than admitting the
gap.

---

### 12.1 The Limitations section is not optional

The Appendix carries a standing **Limitations** section, last in the view after
the evaluation glossary. Any limitation that research resolves must be struck
from it, and any limitation that research *reveals* must be added to it.

The section exists so the honest weaknesses are stated in the artifact a reader
actually sees, rather than living only in a design document. A limitation that
is known but unlisted is worse than one that was never noticed, because the
omission looks like a claim.
