#!/bin/zsh
# RUNBOOK step 1 — smoke test, ~40 calls, about $0.15.
# Run this in the terminal where you exported the keys.
set -e
cd "$(dirname "$0")"

if [ -z "$ANTHROPIC_API_KEY" ]; then
  echo "ANTHROPIC_API_KEY is not set in THIS shell. Export it here, or add it to ~/.zshrc."
  exit 1
fi
echo "key visible: len=${#ANTHROPIC_API_KEY} prefix=${ANTHROPIC_API_KEY:0:7}…"

rm -f results/smoke_live.jsonl
.venv/bin/python -m trackii.run frames \
  --models haiku-4.5 --seeds 1 --case cases/quarantine.yaml \
  --out results/smoke_live.jsonl

echo
echo "===================== GATE ====================="
.venv/bin/python - <<'PY'
import json, collections
rows = [json.loads(l) for l in open("results/smoke_live.jsonl")]
neg  = [r for r in rows if r["kind"] == "negotiation"]
errs = collections.Counter(e.split(":")[0] for r in neg for e in r.get("errors") or [])
tin  = sum(r.get("input_tokens") or 0 for r in neg)
tout = sum(r.get("output_tokens") or 0 for r in neg)
print(f"negotiations   : {len(neg)}")
print(f"with errors    : {sum(1 for r in neg if r.get('errors'))}")
print(f"error kinds    : {dict(errs) or 'none'}")
print(f"parse failures : {sum(r.get('parse_failures') or 0 for r in neg)}")
print(f"agreements     : {sum(1 for r in neg if r['agreement'])}/{len(neg)}")
print(f"below-BATNA    : {sum(1 for r in neg if r['score'].get('any_below_batna'))}")
per = [r['score']['pareto_efficiency_ratio'] for r in neg
       if r['score'].get('pareto_efficiency_ratio') is not None]
print(f"PER range      : {min(per):.0%}-{max(per):.0%}" if per else "PER range      : no deals")
print(f"tokens         : {tin:,} in / {tout:,} out")
print(f"cost so far    : ${tin/1e6*1 + tout/1e6*5:.3f}")
print(f"provenance     : live={neg[0].get('live')} run={neg[0].get('run_id')} "
      f"digest={neg[0].get('case_digest')}")
t = next((r['transcript'] for r in neg if r.get('transcript')), None)
print("\n--- first model turn, verbatim ---")
print((t[0]['text'][:600] + '…') if t else 'NO TRANSCRIPT — investigate')
PY
echo "================================================"
echo "Paste the block above back to Claude."
