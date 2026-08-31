# Proposal: sourced revisions to the case structure

**Status: IMPLEMENTED.** This began as a proposal and was accepted. The case
files now follow the record; what changed, and the evidence for each change, is
in [`CHANGELOG.md`](CHANGELOG.md). The analysis below is preserved as written —
including the four retractions in §0 and the Tier 3 downgrade in §2A — because
the reasoning is the argument, not just its conclusion. Evidence, locators and
per-cell confidence: [`SOURCES.md`](SOURCES.md). Working extraction log:
[`research/NOTES.md`](research/NOTES.md).

---

## 0. Corrections to my own earlier drafts

**On the method.** Drafts 1–2 reached every source through `WebFetch`, which
returns a small model's *summary*, not the document. That is not reading. Six
primaries have now been pulled down and read locally — including the 91-page
Phase One agreement, which I downloaded during the previous pass and never
opened. Spot-checks found the summaries accurate but lossy: the work-report
passage on the use of force is truncated in the summary and actually ends
"…及其分裂活动，**绝非针对广大台湾同胞**", dropping the qualifier.

**Three substantive retractions.**

| Claim | Draft | Status |
|---|---|---|
| Invert the log-roll, on the $400M aid pause | 1 | Withdrawn — the pause was "in favor of sales instead", followed by $11.11bn in December 2025 |
| "Washington has declined to haggle" over Taiwan arms | 2 | Retracted — Trump on the $14bn package: *"a very good negotiating chip for us, frankly"* |
| Beijing announces "no concrete countermeasures" on arms sales | 2 | **Wrong** — Beijing sanctioned 13 US military firms over the December 2024 package |
| "CFR shows technology restrictions rank fourth — the lowest priority" | pre-1 | **Wrong** — CFR says the opposite: "China's *primary concern* is likely U.S. technology-related export controls". The gloss was mine |

On the third: the ranking survives but the reasoning must change. Sanctioning US
defence firms already barred from the Chinese market is close to costless, where
the gallium and germanium bans cost Chinese exporters real revenue. That is a
difference in the *price* Beijing pays, not in whether it acts at all.

---

## 1. Coverage

Tier 0+ per `RESEARCH_PLAN.md` §9.4 — all 12 cells, direction and intensity,
6 issues × 2 sides.

**Corpus: 43 documents, 4,733,500 characters, checksummed, all downloaded, converted, verified and read** ([`research/CORPUS.md`](research/CORPUS.md)). The retrieval audit required by §5A caught five silent failures — both CRS reports returned a Cloudflare challenge, all three PRC statutes a navigation shell — which earlier passes would have swallowed.

**Including:** USCC 2025 Annual Report (745pp) and its executive
summary (56pp); the Phase One agreement (91pp); Xi's 20th Party Congress work
report (Chinese, 33.8k characters); the 2022 Taiwan white paper 《台湾问题与新时
代中国统一事业》 (Chinese, 14.8k); MOFCOM's October 2025 press conference
(Chinese). **Read via analysis:** the 2025 NSS, the Busan accounting, the arms
sales register, CSIS on quarantine operations and the S&T Agreement, the State
Department STA protocol, MMCA reporting from PRC MND, Xinhua and CGTN.

**Result: 9 of 12 cells confirmed, 2 partial, 1 contradicted.**

---

## 2. Finding 1 — both sides' top-ranked issue is the same one

| | Shipped rank 1 | Sourced rank 1 |
|---|---|---|
| DELTA (US) | `security_commitment` | **`export_controls`** |
| OMEGA (PRC) | `export_controls` | **`export_controls`** |

**DELTA.** The 2025 NSS carries "really only one operational economic policy…
the building of secure supply chains". Five of ten USCC priority
recommendations are technology-restriction items, including moving advanced
chips "from a 'sell' model to a 'rent' model". Across the full 745 pages,
"export control" appears **223** times against **11** for "arms sale", and the
sole Taiwan priority recommendation is a *reporting requirement* under the
Taiwan Relations Act.

**OMEGA.** Export controls are where Beijing spends costly leverage, and it
frames the instrument as deliberately calibrated and reversible — 中国的出口管制
不是禁止出口，对符合规定的申请将予以许可 — with a licensing ladder (通用许可、
许可豁免) and a standing bilateral dialogue channel used for advance
notification. On Taiwan, its own white paper lists arms sales as item 3 of 7 in
a grievance list organised around 以台制华, and describes Taiwan as a 棋子 — a
chess piece used "把台湾当作遏制中国发展进步…的棋子". In Beijing's own account,
Taiwan pressure is instrumental to blocking China's *development*, which is
where export controls live.

Two institutional details reinforce that this is a bargaining domain rather than
a red line. Beijing notified other governments *before* acting, 通过双边出口管制
对话机制 — through a standing bilateral export-control dialogue channel — and
signals a graduated ladder rather than a switch: 积极考虑适用通用许可、许可豁免
(general licences and licence exemptions under active consideration). It also
grieves the US *de minimis* rule reaching "低至0%". These are the marks of an
issue built to be traded.

**A log-roll requires opposed intensity orderings. These are aligned.**

---

## 2A. Finding 1b — the log-roll exists, but it is mis-seated

The case pairs export controls against Taiwan arms sales. The one documented
instance of these parties actually exchanging concessions pairs export controls
against **each other**:

> "In July 2025, BIS rescinded license requirements for EDA firms **after the PRC
> agreed to resume licensing rare earth magnets for U.S. firms**."
> — CRS R48642 (Tier A)

Two corroborating instruments in the same report: BIS "reportedly withheld export
control actions against China during U.S.-China tariff talks", and the August 2025
approval of Nvidia's H20 and AMD's MI308 "under terms that the U.S. government
would receive 15% of proceeds".

Tier 2 read this as a log-roll and inferred its orientation: each side conceded
the issue it valued less, so DELTA values minerals above semiconductors and OMEGA
the reverse, at Tier A.

**Tier 3's open nomination broke that claim.** Two independent challenges:

**The timing.** The EDA restrictions were imposed in **May 2025** and lifted in
**July 2025** — less than six weeks. The sequence is US escalates → PRC
counter-escalates → both return to the status quo ante. Mutual de-escalation of a
fresh tit-for-tat is not a log-roll: a log-roll creates joint value by trading
across differently-valued issues, whereas undoing reciprocal harm restores a
position both sides already preferred. That is escaping a prisoner's dilemma, not
integrative bargaining.

**The minerals lever is temporary by design.** Resources for the Future models it
as a repeated game, citing Fudenberg and Maskin (1986): permanent restriction
would induce rest-of-world investment in alternatives and destroy China's market
position, so "China exerts temporary leverage while avoiding long-term damage to
its own processing industry." If the restriction was never meant to be permanent,
Beijing relinquishing it says little about how it values minerals against
semiconductors.

**And the two arms are not symmetric.** War on the Rocks scores both choke points
on durability, replaceability, precision, feedback and sustainability and
concludes that "America's semiconductor choke point cuts deeper and endures
longer than China's rare earth ban" — a rare-earth ban "forces China's midstream
manufacturers to absorb much of the shock they intend to impose on foreign
buyers", and "each use of a choke point weakens its impact." RFF calls it a
"one-shot bazooka". US buffers are real: DLA stockpiles run months, automakers
about a year.

| | verdict after open nomination |
|---|---|
| Export controls of both kinds are the live bargaining currency, traded against *each other*, with Taiwan outside the trade | **survives** |
| The shipped log-roll (export controls vs Taiwan arms) is unsupported | **survives** |
| Orientation — minerals > semiconductors for DELTA, reverse for OMEGA | **downgraded to Tier B, moderate confidence**; mutual de-escalation is a live alternative reading |
| A symmetric opposed-intensity pair | **withdrawn** — the arms differ in durability, so a static schedule mis-specifies the minerals side |

Magnitude still holds: China held "over 90 percent of global production of
neodymium (rare earth) magnets in 2024" (IEA via PIIE), and a 2024 US government
survey found 44% of companies did not know whether their chips came from China.

This is the fourth time adding evidence has cost me a conclusion, and the first
time it cost me my strongest one. It is also the clearest argument that the
process is working: the finding was found by looking for what would break it.

This changes the character of the whole proposal. The previous drafts could only
say what was wrong. **The log-roll is not absent from US–China relations; it is
mis-seated in the case**, and the record names its correct seats along with the
rungs of both ladders.

---

## 3. Finding 2 — the real comprehensive package excluded all of it

Phase One is the only completed comprehensive US–PRC negotiated text, and it is
the closest Tier A analogue to what `package_deal.yaml` models.

| | |
|---|---|
| Chapters | IP · Technology Transfer · Food & Agriculture · Financial Services · Macro & FX · Expanding Trade · Dispute Resolution · Final |
| "China shall" | **92** |
| "United States shall" | **4** |
| Mentions of export control, Taiwan, Entity List, national security, fentanyl | **0** |

The four US obligations are procedural in their entirety — cooperate on
e-commerce counterfeiting, "endeavor, as appropriate" on enforcement
communication, establish a working group, provide monthly updates to a pet food
facility list. **The US's actual consideration, tariff relief, is not in the
text**; "tariff" appears three times, all about tariff-rate quota administration.

**And it is not one document.** The USTR Section 301 report — 215 pages, the
legal foundation of the entire tariff war — shows the same pattern
independently:

| technology transfer | cyber | licensing | joint venture | tariff | export control | **Taiwan** |
|---|---|---|---|---|---|---|
| 227 | 247 | 113 | 78 | 10 | 2 | **1** |

Two foundational US instruments, built a decade apart for different purposes,
both define the negotiable set as trade, IP, technology transfer and market
access — and both exclude Taiwan and export controls almost entirely. One
document could be a quirk of drafting. Two is a pattern.

Two consequences. First, the real package was built from regulatory and
commercial issues — the kind that can be enumerated and verified — while export
controls, Taiwan and fentanyl run through unilateral instruments with informal
cross-linkage. Putting all six on one table is defensible (a package deal needs
issues on one table) but is a **fidelity limitation**. Second, a 23:1 obligation
asymmetry in the one real analogue is worth knowing about a case whose two sides
have near-identical maxima (122 and 123).

---

## 4. Finding 3 — `precursors` falsified, now on three independent sources

1. **USCC:** tariffs were *imposed* over "lack of cooperation on cracking down on
   the shipment of fentanyl precursors to North America".
2. **Busan (Tier A):** the same lever in reverse — fentanyl tariffs halved
   20%→10% against restored precursor cooperation.
3. **Brookings (Tier D):** "transactional compliance disconnected from genuine
   commitment".

Imposed for non-cooperation, relaxed for cooperation. That is a price, not a
shared preference. "Fentanyl" appears twice in 745 pages; every other
"precursor" hit is pharmaceutical API supply chain, a different issue.

---

## 5. What the findings do to the case, measured

Applied to a throwaway copy (`research/probe.py`):

| | As shipped | + US ranks export controls 1st | + fentanyl not compatible |
|---|---|---|---|
| Validator | **PASS** | **FAIL** — "log-roll issues have opposed intensity" | **FAIL** — 4 checks |
| Max joint | 160 | 150 | 138 |
| In-ZOPA joint spread | 85–160 (**75**) | 95–150 (55) | 107–138 (**31**) |
| Pareto frontier | 33 | 36 | 61 |

The case's own validator detects both findings as structural violations. It was
written to catch exactly this, and it did.

**The tension worth naming:** the evidence-faithful version is a *worse eval
instrument*. Integrative range collapses 59% and the frontier nearly doubles —
the negotiation becomes substantially more zero-sum, the very property the design
exists to avoid and the specific criticism levelled at the Abdelnabi et al.
reproductions. Fidelity to the record and usefulness as a negotiation eval pull
against each other here.

That argues for saying plainly what the case is: **a negotiation instrument
calibrated for integrative structure, using US–China issues as a salience frame —
not a model of US–China relations.** The frame ablation is what the eval measures,
and it survives either way.

---

## 6. Finding 4 — the Mandarin arm got stronger, unexpectedly

The USCC documents "a troubling divergence… between China's English-language and
Chinese-language propaganda about Taiwan… Whereas Chinese statements aimed at
international audiences downplay the possibility of an invasion, China's domestic
propaganda has stated that Taiwan's 'provocations' could justify military action
in the near future."

`salient_zh` was designed as a language-invariance check. This gives it a
**directional hypothesis**: if models inherit the divergence from their training
corpora, the Mandarin frame should shift them toward escalation and away from
accommodation relative to `salient`. Sharper than the arm was built to make, and
testable in the live runs. This is the one finding that *improves* the eval.

---

## 6A. Tier 2 findings — triangulation

**Cell 1 splits between actors, and Tier 0+ overstated it.** Read in the
original, the 2025 NSS mentions "export control" **once** in 33 pages — and that
once is an offer of favourable treatment to *allies* who align their controls
with ours, not a China restriction. It mentions "critical mineral" five times,
framed as "expanding American access". Since §2 fixes DELTA as the executive
branch, the USCC's 223 mentions are the *congressional* actor. The correction
does not rescue the shipped design; it moves weight onto a seventh issue the case
does not model.

**Tariffs — two facts the earlier passes missed.** The US Supreme Court's
February 2026 ruling struck down many of the 2025 tariffs and forced a strategy
recalibration, with fresh Section 301 investigations in March 2026. And the
standing levels are asymmetric: US average 47.5% against China's 31.9%, both at
100% coverage. The case models tariffs as a symmetric pure transfer.

**The Quarantine walk-away values are directionally right and too narrow.** RAND
RRA1279-1 finds "the PRC has effectively every advantage over Taiwan", that a
counterblockade "is unlikely to be successful", and that US force requirements
"are likely to be heavy". It also finds the asymmetry *worsens dynamically*:
"the PRC's very success in establishing asymmetry may in fact reduce the choices
available to the United States." The case has DELTA 34 against OMEGA 36.

**And RAND specifies the negotiable space**, which the case currently authors:

> "While there may be room to negotiate the movement of **particular kinds of
> commodities**, if the PRC declines to allow free shipment, no amount of
> indirect pressure is likely to result in the PRC abandoning its efforts."

The tradeable object in a quarantine is *which cargoes move*, not whether it ends.

**A human-subject analogue of what this eval measures.** CSIS ran 26 iterations
of a blockade wargame — 19 with escalation levels fixed, 5 free-play. In the
free-play games, identical setups produced divergent outcomes: "In some games,
the teams went to a high level of violence. In other games, they found an offramp
to limit the level of escalation and violence." That is the same quantity this
eval scores, measured on humans. CSIS also locates the quarantine variant exactly
where this case puts it — "The quarantine element falls more in the policy
domain."

**A third party neither case models.** RAND's gray-zone exercise found Taiwan
rating "sovereignty challenges as more threatening" than the US did, and being
"disappointed by the lack of specificity in Blue's promises of support." Both
cases are strictly bilateral.

---

## 6B. Tier 3 — what a single coder can and cannot deliver

**The defining requirement of Tier 3 is a second, independent coder** producing
Krippendorff's α (§6, §9). There is one coder. My re-reading of the same corpus
is correlated with my first reading in precisely the way α exists to detect, so
any α reported here would be a fabricated number. **Not attempted.** What is
legitimately available instead:

**1 · Open nomination, run adversarially.** Rather than nominating sources likely
to extend the findings, I searched for what would break them. It broke the
strongest one (§2A). It also confirmed the most contested: nothing found
rehabilitates fentanyl precursors as a compatible issue.

**2 · Inter-source concordance** — a real statistic, and not a substitute for α.
It measures how far *independent sources* agree about a cell, over 37 source-cell
judgements ([`research/CONCORDANCE.txt`](research/CONCORDANCE.txt), regenerate
with `research/concordance.py`):

| cell | n | concordance | status |
|---|---|---|---|
| `export_controls` · OMEGA | 5 | 100% | uncontested |
| `market_access` · both | 2 each | 100% | uncontested |
| `precursors` · DELTA | 2 | 100% | uncontested |
| `joint_research` · both | **1 each** | 100% | uncontested but **single-sourced** |
| `tariffs` · OMEGA | 4 | 75% | qualified |
| `tariffs` · DELTA | 3 | 67% | qualified |
| `export_controls` · DELTA | 5 | 60% | **contested** — NSS against USCC |
| `security_commitment` · OMEGA | 5 | 60% | **contested** |
| `security_commitment` · DELTA | 4 | **25%** | qualified — the weakest cell |
| `precursors` · OMEGA | 3 | **0%** | **contested — unanimously against** |
| **overall** | **37** | **68%** | 6 uncontested · 3 qualified · 3 contested |

Three things this surfaces that prose had hidden. `joint_research` rests on a
**single source on both sides** — below Tier 2's own standard of three to five
per cell, and it should not be described as confirmed. `security_commitment` ·
DELTA scores 25% because three of its four sources only *qualify*; it is the
least secure cell in the design and I had been treating it as settled.
`precursors` · OMEGA scores 0% — every source contradicts the shipped coding,
which is the firmest result in the whole exercise.

**3 · A published, reproducible corpus.** 43 documents, 4,733,500 characters,
SHA-256 checksummed ([`research/CORPUS.sha256`](research/CORPUS.sha256)) with a
rebuild manifest ([`research/MANIFEST.md`](research/MANIFEST.md)) and the
retrieval script. Every quotation in `SOURCES.md` and in the site appendix is
`grep`-able against a file whose hash is published.

**What remains genuinely absent:** a second coder, α, and any independent
nomination — the sources here were nominated by me, including the adversarial
ones, which is not the same as an outside party choosing what I should have to
answer.

---

## 7. Recommendation

### 7.1 Change no payoffs before Tuesday
The contested and contradicted cells sit in the load-bearing structure. Fixing
them means a new option ladder across four framings, re-tuned magnitudes,
re-drawn instances and full re-validation — on one coder's evidence, with
inter-source concordance at 68% and no inter-rater reliability available at all.
The strongest candidate replacement had its orientation downgraded from Tier A to
Tier B by this very research pass (§2A), which is itself an argument for not
building on it under deadline.

### 7.2 Free changes — documentation only, no re-validation
1. **Lead with the Quarantine.** Better evidenced throughout, and now sharper:
   the PLA could impose a blockade "in a matter of hours"; Strait Thunder
   (April 2025) practised blockade manoeuvres and simulated strikes on Taiwan's
   energy and port facilities.
2. **Upgrade `deconfliction_channel` to fully compatible.** The MMCA working
   groups of November 2025 and May 2026 are publicised approvingly by both
   militaries' own outlets.
3. **Rewrite the `salient_zh` arm around the documented divergence** (§6) — it
   now predicts a direction.
4. **Re-ladder `quarantine_scope` around commodity classes.** RAND locates the
   negotiable object precisely — "room to negotiate the movement of particular
   kinds of commodities", not whether the quarantine ends. This replaces an
   authored ladder with a sourced one and touches no payoffs.
5. **Make the evidence base findable, and stop redistributing other people's
   text.** "Ship `SOURCES.md`" was a gesture, not an action — the file existed
   and nothing linked to it, so a judge landing on the README would never have
   seen it. Concretely:
   - an **evidence-base section in `README.md`** linking `SOURCES.md`,
     `PROPOSAL.md`, `RESEARCH_PLAN.md`, `CONCORDANCE.txt`, `MANIFEST.md` and
     `CORPUS.sha256`, with a three-line recipe for verifying any quotation;
   - a section in `WRITEUP.md` stating what the research found *against* the
     design, since a reader of the argument should not have to open another file
     to learn that two of its structural claims are contradicted;
   - **untrack the 24 third-party copyrighted extractions** (629 KB from
     Brookings, CSIS, RAND, PIIE, Foreign Affairs, War on the Rocks and others,
     one of them paywalled) and all raw `.html`/`.pdf` downloads. Checksums
     still cover all 43 documents, so `fetch.sh` + `shasum -c` reproduces and
     verifies the corpus without redistributing it. Only the 19 government
     documents stay committed.

### 7.3 Add to Appendix · Limitations

The list has grown across three tiers and the earlier version of this section was
already out of date. In full:

**On the evidence**
- Nine of twelve cells confirmed, two partial, one contradicted — but
  inter-source concordance is **68%**, with 3 cells contested and 3 qualified.
- **`joint_research` rests on a single source on each side**, below the standard
  the plan sets for itself. It should not be called confirmed.
- **`security_commitment` · DELTA scores 25%** — three of four sources only
  qualify. It is the least secure cell in the design and was being treated as
  settled.
- **No second coder, so no Krippendorff's α.** Concordance measures agreement
  among sources, not among raters, and is not a substitute.
- Nomination was adversarial but not independent — I chose the sources that
  attack my own findings.

**On the design**
- Both sides in fact rank export controls first, so the shipped log-roll lacks
  opposed intensity; `precursors` is bought rather than shared; Taiwan arms sit
  below the Anti-Secession Law's stated triggers.
- **DELTA is one seat but two actors.** The USCC mentions export controls 223
  times; the executive's own NSS mentions them once, and that once is an offer to
  allies. §2 routes Congress through the BATNA, which this exposes as a real
  simplification.
- **Tariffs are modelled as a symmetric transfer** where standing levels are
  47.5% against 31.9%, and where the Supreme Court struck down many of the 2025
  tariffs in February 2026.
- **The Quarantine's walk-away gap is too narrow**, and static: RAND finds the
  asymmetry worsens as the quarantine runs.
- **Both cases are bilateral**; the record documents a third party, Taiwan,
  rating sovereignty challenges as more threatening than Washington does.
- **Real packages exclude these issues.** Two foundational US instruments, Phase
  One and the Section 301 report, both leave out Taiwan and export controls.
- **Fidelity and instrument quality pull apart** (§5): the evidence-faithful case
  is more zero-sum and so a worse vehicle for measuring integrative bargaining.

**On this document**
- **Four retractions**, all in §0, including one claim carried through two drafts
  on a source that said the opposite.

A design whose own validator catches its authors' sourcing errors, and whose
authors' strongest finding was destroyed by their own adversarial search, is the
best available argument that the apparatus works.

### 7.4 Queue for after submission — now a specification, not a wish

1. **Re-seat the log-roll on the pair the record documents.** Split the single
   `export_controls` issue into two, and the structure the case wants appears:

   | | DELTA / US | OMEGA / PRC |
   |---|---|---|
   | `semiconductor_controls` (DELTA concedes) | wants tight — **moderate** | wants lifted — **high** |
   | `critical_minerals` (OMEGA concedes) | wants lifted — **high** | wants tight — **moderate** |

   **Orientation is now Tier B, not Tier A** (§2A) — the July 2025 exchange is
   consistent with mutual de-escalation as well as with a trade, so the intensity
   ordering above should be treated as the better-supported of two readings
   rather than as demonstrated. Before building this, the asymmetry needs
   encoding too: DELTA's minerals interest is *access*, which diversification
   also satisfies, and Beijing's optimal restriction is temporary, so the
   minerals arm's value decays in a way the semiconductor arm's does not. A
   static point schedule cannot express that. Either accept the mis-specification
   explicitly or model the arm at a stated point in time.

   Ladders are documented on both sides: US — Entity List → foreign direct
   product rule → performance thresholds → country-wide → AI Diffusion tiers →
   case-by-case licence. PRC — gallium and germanium bans → rare-earth magnet
   licensing → general licences and exemptions → resumption. Ladder membership is
   Tier A on both arms; only the intensity *ordering* is Tier B. It would restore
   the
   integrative structure §5 shows collapsing.

2. **Widen the Quarantine BATNA gap and re-ladder `quarantine_scope` around
   commodity classes**, per RAND. Both are sourced changes to a case that already
   validates.

3. Reconsider whether `security_commitment` belongs at all, or belongs as a
   low-range side issue. The Anti-Secession Law's three triggers do not include
   arms sales, both foundational US trade instruments exclude Taiwan, and Taiwan
   did not come up at Busan.
2. Re-price `precursors` as a lever Beijing withholds.
3. Rebuild `security_commitment`'s ladder around *increments* — a specific
   package released, deferred or held — not the whole relationship.
4. Consider a "rejected integrative offer" probe. MOFCOM records proposing
   industry cooperation on shipbuilding, which Washington declined — a real
   instance of value left on the table, which is precisely what the eval scores.
