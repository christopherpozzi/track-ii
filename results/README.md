# Results

## Layout

| Path | Committed | What it is |
|---|---|---|
| `mock.jsonl` | yes | Deterministic offline mock. Lets the site build and the harness be exercised with **no API keys and no spend**. Regenerate any time; nothing depends on its exact contents. |
| `live/*.jsonl.gz` | yes | Live model runs. **This is the evidence.** Committed compressed because transcripts are large and natural-language. |
| `*.jsonl` (anything else) | no | Working files from a run in progress. Gitignored. Compress into `live/` when a run completes. |

`python -m trackii.report` with no argument loads **every** `.jsonl` and
`.jsonl.gz` in this directory, so the site reflects whatever is here.

## Every record carries its own provenance

Added because the runner appends, which makes mixing runs the easy mistake:

| Field | Why it matters |
|---|---|
| `run_id` | Groups records from one invocation |
| `run_started` | UTC timestamp |
| `harness_commit` | Which version of the code produced this |
| `live` | **`false` for mock, `true` for a real model.** The one field that stops a demo being mistaken for a finding |
| `temperature` | Sampling setting in force |
| `case_digest` | SHA-256 prefix over the payoff structure — ids, BATNAs, design roles, every point |

`case_digest` is the important one. The case files were rewritten once already
when the sourced research contradicted them, and results from before that
rewrite are **not comparable** to results after it. The digest makes that
checkable rather than a matter of memory:

```bash
python - <<'PY'
import json, collections, pathlib, gzip
c = collections.Counter()
for p in pathlib.Path(".").glob("**/*.jsonl*"):
    o = gzip.open if p.suffix == ".gz" else open
    for line in o(p, "rt"):
        r = json.loads(line)
        if r.get("kind") == "negotiation":
            c[(r.get("case_family"), r.get("case_digest"), r.get("live"))] += 1
for k, v in sorted(c.items()):
    print(f"{v:5d}  family={k[0]}  digest={k[1]}  live={k[2]}")
PY
```

Reading this correctly matters, and an earlier version of this note got it
backwards:

- **Several digests under one family is normal and intended** for sampled
  instances. They share a family *so that* they pool, and they differ in digest
  because each is an independently drawn magnitude set satisfying the same
  structural spec. The framing tax is computed *within* an instance and then
  averaged, which is what makes the design paired.
- **What you must not do** is mix records whose digest reflects a different
  *structure* — a case file that was edited between runs. The authored
  `package_deal_v2` has one digest; if you see two, one of them predates an
  edit.

## Archiving a completed run

```bash
gzip -9 results/live_haiku.jsonl
mv results/live_haiku.jsonl.gz results/live/
python -m trackii.report          # rebuilds from everything in results/
```

## Size

A negotiation record is roughly 6.5 KB, most of it transcript. A full
single-model sweep is about 1,900 records, so ~12 MB raw. Natural-language
transcripts compress to roughly a fifth of that, so expect ~2–3 MB per model in
`live/`.

The transcripts are kept rather than trimmed to scores. Every headline number on
the site is arithmetic over the point schedules, so the scores stand on their
own — but a reader who wants to know *why* a model accepted a package below its
own stated walk-away value can only find that in what the model actually said.
