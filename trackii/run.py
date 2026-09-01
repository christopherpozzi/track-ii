"""Experiment runner.

Three experiments, plus the control battery:

  frames  — self-play across abstract / neutral-real / salient / salient-Mandarin
            framings of the same payoff structure. Measures the framing tax on
            strategic reasoning, and separates prompt language from model origin.
  head    — US-lab models against Chinese-lab models on the salient frame.
  swap    — national labels attached to the opposite structural role. Measures
            what happens when assigned interests conflict with model priors.
  games   — the solved-game control battery, abstract vs salient.

Usage
  python -m trackii.run games   --models haiku-4.5,deepseek-v3 --seeds 3
  python -m trackii.run frames  --models haiku-4.5 --seeds 5 --rounds 4
  python -m trackii.run head    --models haiku-4.5,deepseek-v3 --seeds 5
  python -m trackii.run swap    --models haiku-4.5 --seeds 5
  python -m trackii.run all     --models haiku-4.5,deepseek-v3 --seeds 3
"""

from __future__ import annotations

import argparse
import itertools
import json
import sys
import time
from pathlib import Path

from .case import Case
from .engine import run_negotiation
from .judge import judge_negotiation
from .models import REGISTRY, available_models, build_client
from .scoring import analyze, score_outcome
from .solved_games import Battery, run_game, verify
from .validate import validate

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CASE = ROOT / "cases" / "package_deal.yaml"
DEFAULT_BATTERY = ROOT / "cases" / "solved_games.yaml"


def _run_provenance(models: list[str], temperature: float) -> dict:
    """Stamped onto every record so a result can always be attributed.

    Without this, mock and live records are hard to tell apart once they share
    a file -- and the runner appends, so sharing a file is the easy mistake.
    """
    import platform
    import subprocess
    import uuid
    try:
        commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"],
                                cwd=ROOT, capture_output=True, text=True,
                                timeout=5).stdout.strip() or None
    except Exception:  # noqa: BLE001 -- provenance is best-effort
        commit = None
    return {
        "run_id": uuid.uuid4().hex[:12],
        "run_started": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "harness_commit": commit,
        "live": any(REGISTRY[m].provider != "mock" for m in models),
        "temperature": temperature,
        "python": platform.python_version(),
    }


def _case_digest(case: Case) -> str:
    """Hash of the payoff structure. Results are only comparable within one."""
    import hashlib
    blob = json.dumps(
        {"id": case.id, "batnas": case.batnas,
         "issues": [{"id": i.id, "role": i.design_role,
                     "points": {o: i.points[o] for o in i.option_ids}}
                    for i in case.issues]},
        sort_keys=True)
    return hashlib.sha256(blob.encode()).hexdigest()[:12]


def _writer(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    f = open(path, "a")

    def write(rec: dict) -> None:
        f.write(json.dumps(rec, default=str) + "\n")
        f.flush()

    return write, f


def _clients(case: Case, keys: dict[str, str], seed: int, temperature: float):
    option_space = {i.id: list(i.option_ids) for i in case.issues}
    return {
        role: build_client(keys[role], option_space, seed=seed + k,
                           temperature=temperature)
        for k, role in enumerate(case.roles)
    }


def run_negotiations(
    case: Case,
    jobs: list[dict],
    out: Path,
    rounds: int,
    temperature: float,
    judge_key: str | None,
    verbose: bool = True,
    prov: dict | None = None,
) -> None:
    an = analyze(case)
    prov = dict(prov or {}, case_digest=_case_digest(case))
    write, fh = _writer(out)
    judge_client = None
    if judge_key:
        judge_client = build_client(
            judge_key, {i.id: list(i.option_ids) for i in case.issues}
        )

    try:
        for n, job in enumerate(jobs, 1):
            t0 = time.time()
            clients = _clients(case, job["models"], job["seed"], temperature)
            res = run_negotiation(
                case, job["frame"], clients,
                rounds=job.get("rounds", rounds), seed=job["seed"],
                label_swap=job.get("label_swap", False),
            )
            score = score_outcome(case, an, res.package, res.agreement)

            rec = {
                "kind": "negotiation",
                **prov,
                "experiment": job["experiment"],
                "case_family": case.family,
                **res.to_dict(),
                "score": score,
                "elapsed_s": round(time.time() - t0, 1),
            }
            if judge_client and res.transcript:
                rec["judge"] = judge_negotiation(case, res, judge_client)
            write(rec)

            if verbose:
                a, b = case.roles
                tag = (
                    f"[{n}/{len(jobs)}] {job['experiment']:6s} {job['frame']:9s} "
                    f"{job['models'][a]:>13s} vs {job['models'][b]:<13s} seed={job['seed']}"
                )
                if res.agreement:
                    print(f"{tag}  DEAL  {a}={score['points_' + a]:3d} "
                          f"{b}={score['points_' + b]:3d}  "
                          f"PER={score['pareto_efficiency_ratio']:.0%}"
                          f"{'  BELOW-BATNA' if score['any_below_batna'] else ''}")
                else:
                    print(f"{tag}  NO DEAL"
                          f"{'  (ZOPA existed)' if score['impasse_with_zopa'] else ''}")
                if res.errors:
                    print(f"        errors: {res.errors[:2]}")
    finally:
        fh.close()


def run_battery(
    battery: Battery, models: list[str], seeds: int, out: Path, temperature: float,
    verbose: bool = True, prov: dict | None = None,
) -> None:
    write, fh = _writer(out)
    try:
        jobs = list(itertools.product(
            models, [g["id"] for g in battery.games], ["abstract", "salient"],
            range(seeds)
        ))
        for n, (mkey, gid, frame, s) in enumerate(jobs, 1):
            client = build_client(mkey, seed=s, temperature=temperature)
            rec = run_game(battery, gid, frame, client)
            rec.update({"kind": "solved_game", "seed": s, **(prov or {})})
            write(rec)
            if verbose:
                mark = "OK  " if rec["correct"] else "MISS"
                print(f"[{n}/{len(jobs)}] {mark} {mkey:>13s} {gid:22s} "
                      f"{frame:9s} seed={s}  "
                      f"expected={rec['answer_expected']:>8s} "
                      f"got={str(rec['answer_given'])[:16]:>16s}")
    finally:
        fh.close()


FRAME_ORDER = ["abstract", "neutral", "salient", "salient_zh"]


def case_frames(case: Case) -> list[str]:
    """Framings this case actually declares, in increasing salience.

    Cases are free to omit frames -- the crisis case ships without a Mandarin
    rendering, for instance -- so the runner asks the case rather than assuming.
    """
    return [f for f in FRAME_ORDER if f in case.frames]


def build_jobs(case: Case, experiment: str, models: list[str], seeds: int) -> list[dict]:
    a, b = case.roles
    jobs: list[dict] = []

    if experiment == "frames":
        for m, frame, s in itertools.product(
            models, case_frames(case), range(seeds)
        ):
            jobs.append({"experiment": "frames", "frame": frame, "seed": s,
                         "models": {a: m, b: m}})

    elif experiment == "head":
        us = [m for m in models if REGISTRY[m].origin == "US"]
        cn = [m for m in models if REGISTRY[m].origin == "CN"]
        if not us or not cn:
            us = cn = models          # fall back to a full round robin
        for m1, m2, s in itertools.product(us, cn, range(seeds)):
            if m1 == m2:
                continue
            # Run each pairing in both seat assignments so the result is not an
            # artifact of which side of the table a model happened to sit on.
            jobs.append({"experiment": "head", "frame": "salient", "seed": s,
                         "models": {a: m1, b: m2}})
            jobs.append({"experiment": "head", "frame": "salient", "seed": s,
                         "models": {a: m2, b: m1}})

    elif experiment == "nocomm":
        # Ablation demanded by the reproduction studies of Abdelnabi et al.:
        # if models that never talk score as well as models that negotiate, the
        # benchmark is not measuring negotiation. Run at rounds=0, so only the
        # take-it-or-leave-it close happens, with no dialogue at all.
        for m, frame, s in itertools.product(
            models, [f for f in case_frames(case) if f in ("abstract", "salient")],
            range(seeds)
        ):
            jobs.append({"experiment": "nocomm", "frame": frame, "seed": s,
                         "models": {a: m, b: m}, "rounds": 0})

    elif experiment == "swap":
        for m, swap, s in itertools.product(models, [False, True], range(seeds)):
            jobs.append({"experiment": "swap", "frame": "salient", "seed": s,
                         "label_swap": swap, "models": {a: m, b: m}})

    else:
        raise ValueError(f"unknown experiment {experiment}")
    return jobs


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Track II experiment runner")
    # nargs="?" so `--list` works without naming an experiment -- it only
    # prints the registry and exits.
    p.add_argument("experiment", nargs="?",
                   choices=["frames", "head", "swap", "nocomm", "games", "all",
                            "validate"])
    p.add_argument("--models", default="mock",
                   help="comma-separated registry keys (see --list)")
    p.add_argument("--seeds", type=int, default=3)
    p.add_argument("--rounds", type=int, default=4)
    p.add_argument("--temperature", type=float, default=1.0)
    p.add_argument("--judge", default=None,
                   help="registry key for the audit judge (optional)")
    p.add_argument("--case", default=str(DEFAULT_CASE))
    p.add_argument("--instances", default=None, metavar="DIR",
                   help="run every sampled instance in DIR instead of --case, "
                        "holding each instance fixed across frames and models")
    p.add_argument("--battery", default=str(DEFAULT_BATTERY))
    p.add_argument("--out", default=str(ROOT / "results" / "results.jsonl"))
    p.add_argument("--list", action="store_true", help="list runnable models and exit")
    args = p.parse_args(argv)

    if args.experiment is None and not args.list:
        p.error("an experiment is required (or use --list)")

    if args.list:
        print("Registry:")
        for k, spec in REGISTRY.items():
            ok = "runnable" if k in available_models() else "no API key"
            print(f"  {k:<14} {spec.lab:<10} {spec.origin:<3} {spec.model_id:<34} [{ok}]")
        return 0

    if args.instances:
        paths = sorted(Path(args.instances).glob("*.yaml"))
        if not paths:
            print(f"no instances in {args.instances}", file=sys.stderr)
            return 1
        cases = [Case.load(q) for q in paths]
    else:
        cases = [Case.load(args.case)]
    case = cases[0]
    battery = Battery.load(args.battery)

    # Every artifact must pass self-verification before any spend.
    for c in cases:
        validate(c, verbose=(args.experiment == "validate" and c is case))
    failures = [c for c in verify(battery, verbose=False) if not c[1]]
    if failures:
        print(f"battery self-verification failed: {failures}", file=sys.stderr)
        return 1
    if args.experiment == "validate":
        verify(battery, verbose=True)
        return 0

    models = [m.strip() for m in args.models.split(",") if m.strip()]
    unknown = [m for m in models if m not in REGISTRY]
    if unknown:
        print(f"unknown model keys: {unknown}. Use --list.", file=sys.stderr)
        return 1
    unavailable = [m for m in models if m not in available_models()]
    if unavailable:
        print(f"no API key for: {unavailable}. Use --list.", file=sys.stderr)
        return 1

    out = Path(args.out)
    prov = _run_provenance(models, args.temperature)
    print(f"run {prov['run_id']}  {'LIVE' if prov['live'] else 'mock'}  "
          f"harness {prov['harness_commit'] or '?'}  -> {out}")
    experiments = (["games", "frames", "nocomm", "head", "swap"]
                   if args.experiment == "all" else [args.experiment])

    for exp in experiments:
        print(f"\n=== {exp} ===")
        if exp == "games":
            run_battery(battery, models, args.seeds, out, args.temperature,
                        prov=prov)
            continue
        for c in cases:
            jobs = build_jobs(c, exp, models, args.seeds)
            if not jobs:
                print("  (no jobs for this configuration)")
                continue
            if len(cases) > 1:
                print(f"  -- {c.id} --")
            run_negotiations(c, jobs, out, args.rounds, args.temperature,
                             args.judge, prov=prov)

    print(f"\nwrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
