# Live run runbook

Everything below has been checked against the code in this repo. Run the stages
in order — each one is a gate on the next.

---

## 0 · Before you spend anything

```bash
cd /Users/Chris/Documents/situation-room-eval
export ANTHROPIC_API_KEY=sk-ant-...
export OPENROUTER_API_KEY=sk-or-...
```

Confirm the harness still passes cold:

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

## 1 · Smoke test — 40 calls, about $0.15

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

## 2 · Anthropic sweep — 1,888 calls, about $6

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

## 4 · Chinese models — 600 calls head-to-head, plus each model's own sweep

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

## 5 · Build the final report

```bash
cat results/live_haiku.jsonl results/live_head.jsonl results/smoke_*.jsonl \
  > results/combined.jsonl
.venv/bin/python -m trackii.report results/combined.jsonl
.venv/bin/python research/audit_docs.py | tail -2
open site/index.html
```

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
- **Budget.** About $6 for the full Anthropic sweep, about $2 for the
  head-to-head at Haiku rates. OpenRouter pricing varies by model; check
  <https://openrouter.ai/models> and expect the five Chinese models to land in
  the same order of magnitude.
