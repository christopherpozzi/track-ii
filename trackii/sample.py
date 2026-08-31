"""Structured instance sampling.

A single hand-authored payoff structure gives you n=many on conversations and
n=1 on games: seeds vary the dialogue, not the problem. Any model difference
could then be an artifact of one draw. This module turns the case into a
*family* of instances so results generalise beyond the instance I happened to
author.

What is randomised, and what is not
-----------------------------------
The design TEMPLATE is fixed: which issue is compatible, which pair carries the
log-roll, which issue is exactly zero-sum, which has an interior optimum. Only
the MAGNITUDES move. Drawing point values freely would mostly produce degenerate
games -- empty ZOPAs, "compatible" issues that aren't, log-rolls with no
integrative potential -- and would destroy the planted structure the metrics
are defined against.

Two invariants make the sampling safe:

  1. Ordinal structure is preserved exactly. Each option's rank within an
     issue (including ties and interior peaks) is carried over from the
     template, so `best_for`, monotonicity, and the non-monotonic issue all
     survive rescaling.

  2. Every instance must pass the full case validator before it is emitted.
     validate.py is the acceptance test -- draw, check, discard on failure. An
     instance that ships is provably well-posed, exactly like the authored one.

Frames are copied verbatim, so an instance keeps the frame invariant: labels
change across frames, payoffs never do.

Usage
  python -m trackii.sample --n 10 --seed 0
  python -m trackii.sample --n 10 --template cases/quarantine.yaml
"""

from __future__ import annotations

import argparse
import random
from pathlib import Path

import yaml

from .case import Case
from .validate import ValidationError, validate

ROOT = Path(__file__).resolve().parents[1]


def _ordinal_levels(vec: list[int]) -> tuple[list[int], int]:
    """Map each position to its rank among distinct values (0 = highest).

    Ties share a rank, so a template with equal options stays equal and one
    with a strict ordering stays strict.
    """
    distinct = sorted(set(vec), reverse=True)
    return [distinct.index(v) for v in vec], len(distinct)


def _redraw_vector(vec: list[int], new_range: int, rng: random.Random) -> list[int]:
    """Redraw an issue's points for one role, preserving ordinal structure.

    The top level becomes `new_range`, the bottom becomes 0, and interior
    levels are drawn strictly between them -- so an interior peak stays a peak
    and a monotone run stays monotone.
    """
    ranks, n_levels = _ordinal_levels(vec)
    if n_levels == 1:
        return [0] * len(vec)
    if n_levels == 2:
        values = [new_range, 0]
    else:
        # Strictly decreasing interior levels, randomly spaced.
        cuts = sorted(rng.uniform(0.12, 0.88) for _ in range(n_levels - 2))
        values = [new_range] + [int(round(new_range * c)) for c in reversed(cuts)] + [0]
        # Repair any collisions the rounding introduced.
        for i in range(1, len(values)):
            if values[i] >= values[i - 1]:
                values[i] = values[i - 1] - 1
        if values[-1] < 0:                       # not enough room; widen and retry
            return _redraw_vector(vec, new_range + n_levels, rng)
        values[-1] = 0
    return [values[r] for r in ranks]


def _draw_raw(template: Case, rng: random.Random, idx: int,
              scale: tuple[float, float], batna_scale: tuple[float, float]) -> dict:
    """One candidate instance. May be degenerate -- the caller validates."""
    raw = {
        "id": f"{template.id.rsplit('_v', 1)[0]}_i{idx:02d}",
        "family": template.raw.get("family", template.id),
        "title": template.title,
        "instance": idx,
        "roles": list(template.roles),
        "batnas": {},
        "issues": [],
        # Labels are copied verbatim: only magnitudes move, so the frame
        # invariant (same payoffs under every framing) is untouched.
        "frames": template.raw["frames"],
    }

    for issue in template.issues:
        opts = list(issue.option_ids)
        entry: dict = {"id": issue.id, "design_role": issue.design_role, "options": []}

        if issue.design_role == "distributive":
            # Must stay exactly zero-sum, so draw one total and split it.
            base = max(issue.points[o][template.roles[0]] for o in opts)
            total = max(6, int(round(base * rng.uniform(*scale))))
            total -= total % (len(opts) - 1)          # divisible, so splits are integral
            step = total // (len(opts) - 1)
            a_vec = [total - step * k for k in range(len(opts))]
            # Orient to match the template's direction.
            if issue.points[opts[0]][template.roles[0]] < issue.points[opts[-1]][template.roles[0]]:
                a_vec = a_vec[::-1]
            vecs = {template.roles[0]: a_vec,
                    template.roles[1]: [total - v for v in a_vec]}
        else:
            vecs = {}
            for role in template.roles:
                cur = [issue.points[o][role] for o in opts]
                rng_span = max(cur) - min(cur)
                new_span = max(4, int(round(rng_span * rng.uniform(*scale))))
                vecs[role] = _redraw_vector(cur, new_span, rng)

        for k, oid in enumerate(opts):
            entry["options"].append(
                {"id": oid, "points": {r: int(vecs[r][k]) for r in template.roles}}
            )
        raw["issues"].append(entry)

    # BATNAs track the template's share of each side's maximum, jittered.
    probe = Case(raw)
    for role in template.roles:
        frac = template.batnas[role] / template.max_payoff(role)
        raw["batnas"][role] = max(
            1, int(round(probe.max_payoff(role) * frac * rng.uniform(*batna_scale)))
        )
    return raw


def sample(template: Case, n: int, seed: int = 0,
           scale: tuple[float, float] = (0.72, 1.34),
           batna_scale: tuple[float, float] = (0.86, 1.16),
           max_tries: int = 400) -> tuple[list[Case], int]:
    """Draw `n` validated instances. Returns (instances, rejected_count)."""
    rng = random.Random(seed)
    out: list[Case] = []
    rejected = 0
    tries = 0
    while len(out) < n and tries < max_tries:
        tries += 1
        cand = Case(_draw_raw(template, rng, len(out), scale, batna_scale))
        try:
            validate(cand, verbose=False)
        except ValidationError:
            rejected += 1
            continue
        out.append(cand)
    if len(out) < n:
        raise RuntimeError(
            f"only drew {len(out)}/{n} valid instances in {tries} tries — "
            "loosen `scale` or inspect the template"
        )
    return out, rejected


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Sample validated case instances")
    ap.add_argument("--template", default=str(ROOT / "cases" / "package_deal.yaml"))
    ap.add_argument("--n", type=int, default=10)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--out", default=str(ROOT / "cases" / "instances"))
    args = ap.parse_args(argv)

    template = Case.load(args.template)
    validate(template, verbose=False)          # the template itself must be sound
    instances, rejected = sample(template, args.n, args.seed)

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    for inst in instances:
        (out / f"{inst.id}.yaml").write_text(
            yaml.safe_dump(inst.raw, sort_keys=False, allow_unicode=True)
        )

    from .scoring import analyze
    a, b = template.roles
    print(f"\ndrew {len(instances)} validated instances from {template.title} "
          f"({rejected} rejected)\n")
    print(f"{'instance':<20}{'max joint':>10}{'ZOPA':>8}{'front':>7}"
          f"{'  BATNA':>9}{'naive PER':>11}")
    for inst in instances:
        an = analyze(inst)
        naive = {i.id: i.option_ids[len(i.option_ids) // 2] for i in inst.issues}
        per = (inst.payoff(naive, a) + inst.payoff(naive, b)) / an.max_joint
        print(f"{inst.id:<20}{an.max_joint:>10}{an.zopa_size / an.n_packages:>7.0%}"
              f"{len(an.pareto_front):>7}"
              f"{inst.batnas[a]:>5}/{inst.batnas[b]:<4}{per:>10.1%}")
    print(f"\nwrote {out}/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
