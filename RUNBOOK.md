# Live run runbook

Everything below has been checked against the code in this repo. Run the stages
in order — each one is a gate on the next.

---

## 0 · Get the two API keys

You need one key from Anthropic (for Haiku 4.5) and one from OpenRouter (which
fronts all five Chinese models behind a single account, so you do not need
separate DeepSeek, Zhipu, Moonshot, Alibaba and MiniMax accounts).

### Anthropic — `ANTHROPIC_API_KEY`

1. Go to <https://console.anthropic.com> and sign in. The Console is a separate
   product from a Claude.ai subscription: **a Pro or Max plan does not include
   API credit**, and API usage is billed separately.
2. Open **Settings → Billing** and add a payment method, then buy credit. The
   minimum purchase is small and $20 covers this entire project comfortably — the
   measured full sweep is about $14.
3. Open **Settings → API keys → Create key**. Name it something you will
   recognise later, e.g. `track-ii`. Scope it to your default workspace.
4. **Copy it immediately.** The key is shown once and starts `sk-ant-`. If you
   lose it, delete the key and make another; there is no way to reveal it again.

*Already authenticated on this machine?* If you have the `ant` CLI and have run
`ant auth login`, the runner will now pick that up and you can skip minting a
key entirely — `trackii/models.py` falls back to the SDK's own credential
resolution when `ANTHROPIC_API_KEY` is unset. Check with `ant auth status`.

### OpenRouter — `OPENROUTER_API_KEY`

1. Go to <https://openrouter.ai> and sign in (Google or GitHub works).
2. Open **Credits** and add funds. OpenRouter is prepaid — there is no invoicing
   and a request simply fails when the balance hits zero. $10 is ample; the
   head-to-head arm is roughly $2 at Haiku-equivalent rates and the Chinese
   models are generally cheaper.
3. Open **Keys → Create Key**. Name it `track-ii`.
4. **Set a credit limit on the key itself** while you are on that screen — the
   field is right there. Cap it at $15. This is the single best protection
   against a loop bug draining the account, and it costs nothing to set.
5. Copy it. It starts `sk-or-v1-`.

While you are signed in, this is also the moment to do the slug check flagged
below: open <https://openrouter.ai/models> and search for each of the five
model ids.

### Put them in your shell

```bash
cd /Users/Chris/Documents/situation-room-eval
export ANTHROPIC_API_KEY=sk-ant-...
export OPENROUTER_API_KEY=sk-or-v1-...
```

These live only in the current terminal session. If you open a new tab you must
export them again, or append the two lines to `~/.zshrc` and run
`source ~/.zshrc`.

**Do not put the keys in a file inside this repo.** It is a git repository you
intend to publish, and a committed key is a key you have to rotate. If you want
them to persist, `~/.zshrc` is outside the repo and is the right place.

Confirm both are set before continuing:

```bash
for k in ANTHROPIC_API_KEY OPENROUTER_API_KEY; do
  printf '%-22s %s\n' "$k" "$([ -n "${(P)k}" ] && echo SET || echo 'NOT SET')"
done
```

---

## 0b · Confirm the harness is green

Before spending, confirm nothing is broken locally:

```bash
.venv/bin/python -m pytest -q && .venv/bin/python research/audit_mechanics.py | tail -2
```

Then check which models the runner can actually reach:

```bash
.venv/bin/python -m trackii.run --list
```

Every model you intend to use must say `runnable`.

### Two things to verify before the first call

1. **The Anthropic model id.** The registry pins
   `claude-haiku-4-5-20251001`. The current documented id is
   `claude-haiku-4-5`, undated. Dated snapshots usually still resolve, but if
   stage 1 returns a 404 this is why — edit `trackii/models.py` and drop the
   date suffix.
2. **The OpenRouter slugs.** `trackii/models.py` says in a comment that these
   move fast, and they have not been verified against a live account. Check all
   five against <https://openrouter.ai/models> before stage 4:
   `deepseek/deepseek-chat`, `z-ai/glm-4.6`, `moonshotai/kimi-k2-0905`,
   `qwen/qwen3-235b-a22b-instruct-2507`, `minimax/minimax-m2`.

---

## 1 · Smoke test — 40 calls, about $0.22

Do not skip this. The mock exercises the plumbing but never the model.

```bash
.venv/bin/python -m trackii.run frames \
  --models haiku-4.5 --seeds 1 --case cases/quarantine.yaml \
  --out results/smoke_live.jsonl
```

You should see one line per negotiation with `DEAL` or `NO DEAL` and a PER.
Now check the three things that only appear against a real model:

```bash
.venv/bin/python - <<'PY'
import json, collections
rows = [json.loads(l) for l in open("results/smoke_live.jsonl")]
neg  = [r for r in rows if r["kind"] == "negotiation"]
errs = collections.Counter(e.split(":")[0] for r in neg for e in r.get("errors", []))
print(f"negotiations: {len(neg)}   with errors: {sum(1 for r in neg if r.get('errors'))}")
print("error kinds:", dict(errs) or "none")
print("agreements :", sum(1 for r in neg if r['agreement']), "/", len(neg))
bad = [r for r in neg if not r['agreement'] and not r.get('errors')]
print("clean no-deals:", len(bad))
print("\nsample transcript turn:")
t = next((r['transcript'] for r in neg if r.get('transcript')), None)
print((t[0]['text'][:400] + '…') if t else 'NO TRANSCRIPT — investigate')
PY
```

**Gate.** Proceed only if `error kinds` is empty or near-empty. A wall of
parse errors means the model is not returning the expected package format, and
you want to know that now rather than 1,900 calls in. Errors are recorded per
call rather than raised, so **the run will not crash — it will quietly produce
garbage.** That is the failure mode to watch for.

---

## 2 · Anthropic sweep — 1,888 calls, about $10

Three commands, deliberately separate files so a failure in one does not
contaminate the others. **The runner opens result files in append mode**, so
re-running a stage into the same file double-counts. Delete or rename first.

```bash
# battery + core arms, both cases
.venv/bin/python -m trackii.run games --models haiku-4.5 --seeds 3 \
  --out results/live_haiku.jsonl

for c in cases/quarantine.yaml cases/package_deal.yaml; do
  for e in frames nocomm swap; do
    .venv/bin/python -m trackii.run $e --models haiku-4.5 --seeds 5 \
      --case $c --out results/live_haiku.jsonl
  done
done

# the paired instance design — this is the one that makes the framing tax robust
.venv/bin/python -m trackii.run frames --models haiku-4.5 --seeds 3 \
  --instances cases/instances --out results/live_haiku.jsonl
```

Roughly 45–70 minutes at default concurrency. Safe to interrupt: because the
file is append-mode and each record is written and flushed as it completes,
a killed run keeps everything finished so far.

---

## 3 · Check before spending on the Chinese models

```bash
.venv/bin/python -m trackii.report results/live_haiku.jsonl
open site/index.html
```

Look for: a non-zero agreement rate, a framing tax that is not identically
zero across frames, and hard-error rates below ~50%. If the `nocomm` arm
scores the same as `frames`, that is a real result, not a bug — it is the
ablation doing its job.

---

## 4 · Chinese models — 600 calls head-to-head (~$3.35 at Haiku rates)

Only after the slug check in step 0.

```bash
# one cheap smoke per model first
for m in deepseek glm kimi qwen minimax; do
  .venv/bin/python -m trackii.run frames --models $m --seeds 1 \
    --case cases/quarantine.yaml --out results/smoke_$m.jsonl
done
```

Then the head-to-head, which is the arm the contest brief actually asks for —
it is the only one that puts US and Chinese labs on the same table:

```bash
.venv/bin/python -m trackii.run head \
  --models haiku-4.5,deepseek,glm,kimi,qwen,minimax --seeds 3 \
  --case cases/quarantine.yaml --out results/live_head.jsonl
.venv/bin/python -m trackii.run head \
  --models haiku-4.5,deepseek,glm,kimi,qwen,minimax --seeds 3 \
  --case cases/package_deal.yaml --out results/live_head.jsonl
```

Each pairing runs in **both seat assignments**, so seat effects cancel.

---

## 5 · Archive the results and build the final report

Every record carries its own provenance — `run_id`, `run_started`,
`harness_commit`, `live`, `temperature`, and a `case_digest` over the payoff
structure. Before aggregating, confirm you are not mixing incomparable runs:

```bash
cd results && .venv/../.venv/bin/python - <<'PY'
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
cd ..
```

**One digest per case family.** Two means two different payoff structures are in
the mix, and they must not be aggregated. `live=False` rows are the mock.

Then archive the live runs compressed and rebuild:

```bash
gzip -9 results/live_haiku.jsonl results/live_head.jsonl results/smoke_*.jsonl
mv results/*.jsonl.gz results/live/
.venv/bin/python -m trackii.report        # loads everything under results/
.venv/bin/python research/audit_docs.py | tail -2
open site/index.html
```

`results/live/*.jsonl.gz` is committed — it is the evidence. Raw `.jsonl`
working files are gitignored. See `results/README.md`.

Check the Quarantine still leads, every model appears in the top-centre
switcher, and no view is empty.

---

## Notes

- **Prompt caching will not fire.** The cacheable prefix here (system prompt
  plus role sheet) is roughly 1,000–1,300 tokens, below the minimum cacheable
  prefix. Do not budget for a cache discount; if you want to confirm, check
  `usage.cache_read_input_tokens` on a reply — it will be zero.
- **`--judge` is optional and costs extra.** It adds one LLM call per
  negotiation for a qualitative audit. Every headline metric on the site is
  arithmetic over the point schedules and needs no judge, so leave it off
  unless you want transcript commentary.
- **`--temperature` defaults to 1.0.** Leave it — the seeds are what give you
  spread, and a lower temperature would understate real variance.
- **Budget.** Measured, not estimated: **$0.056 per negotiation** on Haiku 4.5
  (32k input / 4.8k output tokens). The transcript is resent every turn, so
  input grows quadratically with round count — an earlier per-call estimate was
  3.7x too low. That puts the Anthropic sweep at **~$10** and the head-to-head
  at **~$3.35**, so budget **$15** total. OpenRouter pricing varies by model; check
  <https://openrouter.ai/models> and expect the five Chinese models to land in
  the same order of magnitude.
