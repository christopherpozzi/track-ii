"""Case validator.

Proves the case is a well-posed game and that every planted trap is reachable,
BEFORE any model is called. A benchmark whose payoff structure has not been
verified is a vibe-coded benchmark.

Run:  python -m trackii.validate cases/package_deal.yaml
"""

from __future__ import annotations

import sys
from pathlib import Path

from .case import Case
from .scoring import analyze, score_outcome


class ValidationError(AssertionError):
    pass


def validate(case: Case, verbose: bool = True) -> dict:
    an = analyze(case)
    a, b = case.roles
    checks: list[tuple[str, bool, str]] = []

    def check(name: str, ok: bool, detail: str = "") -> None:
        checks.append((name, bool(ok), detail))

    # 1. The game is well posed.
    check(
        "outcome space enumerable",
        an.n_packages == case.n_packages() and an.n_packages < 100_000,
        f"{an.n_packages} packages",
    )
    check(
        "ZOPA is non-empty",
        an.zopa_size > 0,
        f"{an.zopa_size} individually-rational packages "
        f"({an.zopa_size / an.n_packages:.1%} of space)",
    )
    check(
        "ZOPA is not trivial",
        an.zopa_size < an.n_packages * 0.9,
        "a ZOPA covering everything would make BATNA discipline untestable",
    )
    check(
        "both sides can be pushed below BATNA",
        any(case.payoff(p, a) < case.batnas[a] for p in case.packages())
        and any(case.payoff(p, b) < case.batnas[b] for p in case.packages()),
        "below-BATNA acceptance must be a reachable error",
    )
    check(
        "frontier is non-degenerate",
        len(an.pareto_front) >= 5,
        f"{len(an.pareto_front)} Pareto-optimal payoff pairs",
    )
    check(
        "efficient frontier has a distributive dimension",
        len({p for p in an.pareto_front if sum(p) == an.max_joint}) > 1,
        "there must be several max-joint packages that split value differently, "
        "so value creation and value claiming are separately measurable",
    )

    # 2. Planted structure.
    for iid in an.compatible_issues:
        issue = case.issue(iid)
        check(
            f"compatible issue '{iid}' is genuinely compatible",
            issue.best_for(a) == issue.best_for(b),
            f"both sides peak at {issue.best_for(a)}",
        )

    for iid in an.distributive_issues:
        issue = case.issue(iid)
        totals = {sum(issue.points[o][r] for r in case.roles) for o in issue.option_ids}
        check(
            f"distributive issue '{iid}' is exactly zero-sum",
            len(totals) == 1,
            f"joint value constant at {totals.pop()}",
        )

    lr = an.log_roll_issues
    check("log-roll pair present", len(lr) == 2, f"{lr}")
    if len(lr) == 2:
        i1, i2 = case.issue(lr[0]), case.issue(lr[1])
        w1, w2 = _intense_role(i1, case), _intense_role(i2, case)
        check(
            "log-roll issues have opposed intensity",
            w1 != w2,
            f"{i1.id}: {a}={i1.range_for(a)} {b}={i1.range_for(b)} (→{w1}) | "
            f"{i2.id}: {a}={i2.range_for(a)} {b}={i2.range_for(b)} (→{w2})",
        )
        gain = _log_roll_joint_gain(case, i1, i2)
        check(
            "log-roll strictly creates joint value",
            gain > 0,
            f"wholesale trade beats the best 'split both' settlement by "
            f"{gain} joint points",
        )
        loss, comp = _log_roll_side_payment(case, i1, i2, an)
        check(
            "log-roll surplus is compensable via the distributive issue",
            loss <= 0 or comp >= loss,
            f"the wholesale trade costs one side up to {loss} points; the "
            f"distributive issue can move {comp}. A log-roll that no side "
            f"payment can fund would never be rational to propose, and the "
            f"eval could not distinguish integrative skill from luck.",
        )

    # Side issues carry no structural trap, but they do carry a design claim --
    # that they are minor. Check it, so that every issue in the case is covered
    # by something. Without this, "side_issue" was a way for an issue to be in
    # the case and validated by nothing.
    side = [i for i in case.issues if i.design_role == "side_issue"]
    bargaining = [i for i in case.issues
                  if i.design_role.startswith("log_roll")
                  or i.design_role == "distributive"]
    for issue in side:
        widest = max(max(issue.range_for(r) for r in case.roles) for issue in [issue])
        floor = min(max(b.range_for(r) for r in case.roles) for b in bargaining)
        check(
            f"side issue '{issue.id}' is genuinely minor",
            widest < floor,
            f"widest range {widest} vs the narrowest bargaining issue at {floor}; "
            "a side issue that rivals the issues carrying the structure is not a "
            "side issue",
        )

    nonmono = [
        i.id for i in case.issues
        if any(
            i.points[i.option_ids[k]][r] > max(
                i.points[i.option_ids[0]][r], i.points[i.option_ids[-1]][r]
            )
            for r in case.roles
            for k in range(1, len(i.option_ids) - 1)
        )
    ]
    check(
        "at least one issue has an interior optimum",
        len(nonmono) > 0,
        f"non-monotonic issues: {nonmono}",
    )

    # 3. The naive baseline must leave real headroom, or the eval cannot
    #    discriminate between a good negotiator and a lazy one.
    naive = _midpoint_package(case)
    naive_score = score_outcome(case, an, naive, agreement=True)
    per = naive_score["pareto_efficiency_ratio"]
    check(
        "split-the-difference baseline is meaningfully suboptimal",
        0.60 <= per <= 0.90,
        f"naive midpoint package scores PER={per:.1%} "
        f"(leaves {naive_score['value_left_on_table']} points on the table)",
    )

    # Meta-check: no issue may sit in the case unexamined. This exists because
    # a design_role the analyser does not recognise silently classified as
    # nothing, and the issue was then checked by nothing.
    covered = set(an.log_roll_issues) | set(an.compatible_issues) \
        | set(an.distributive_issues) | set(nonmono) | {i.id for i in side}
    check(
        "every issue is covered by at least one structural check",
        covered >= set(case.issue_ids),
        f"unchecked: {sorted(set(case.issue_ids) - covered) or 'none'}",
    )

    if verbose:
        _report(case, an, checks, naive_score)

    failed = [c for c in checks if not c[1]]
    if failed:
        raise ValidationError(
            f"{len(failed)} validation check(s) failed: "
            + "; ".join(c[0] for c in failed)
        )
    return {"analysis": an, "checks": checks}


def _interior_settlements(i1, i2):
    """All 'split both issues' settlements — neither issue at either extreme."""
    for o1 in i1.option_ids[1:-1]:
        for o2 in i2.option_ids[1:-1]:
            yield o1, o2


def _intense_role(issue, case: Case) -> str:
    """Whichever side has more at stake on this issue, by point range."""
    a, b = case.roles
    return a if issue.range_for(a) >= issue.range_for(b) else b


def _wholesale_trade(i1, i2, case: Case) -> tuple[str, str]:
    """Each issue settles the way the side that cares more about it wants.

    Direction is inferred from the point ranges rather than assumed from the
    order the issues appear in the file -- a case is free to declare its
    log-roll pair either way round.
    """
    return (i1.best_for(_intense_role(i1, case)),
            i2.best_for(_intense_role(i2, case)))


def _log_roll_joint_gain(case: Case, i1, i2) -> int:
    """Joint value the wholesale trade adds over the best split-both outcome."""
    a, b = case.roles

    def joint(o1, o2):
        return sum(i1.points[o1][r] + i2.points[o2][r] for r in case.roles)

    t1, t2 = _wholesale_trade(i1, i2, case)
    best_split = max(joint(o1, o2) for o1, o2 in _interior_settlements(i1, i2))
    return joint(t1, t2) - best_split


def _log_roll_side_payment(case: Case, i1, i2, an) -> tuple[int, int]:
    """(worst individual loss from taking the trade, compensation available).

    The wholesale trade raises joint value but need not help both sides on its
    own. Real integrative bargaining resolves this by funding the loser out of
    a distributive issue. We verify that funding actually exists.
    """
    t1, t2 = _wholesale_trade(i1, i2, case)
    worst_loss = 0
    for o1, o2 in _interior_settlements(i1, i2):
        for r in case.roles:
            split_val = i1.points[o1][r] + i2.points[o2][r]
            trade_val = i1.points[t1][r] + i2.points[t2][r]
            worst_loss = max(worst_loss, split_val - trade_val)

    compensation = sum(
        max(case.issue(i).points[o][r] for o in case.issue(i).option_ids)
        - min(case.issue(i).points[o][r] for o in case.issue(i).option_ids)
        for i in an.distributive_issues
        for r in [case.roles[0]]
    )
    return worst_loss, compensation


def _midpoint_package(case: Case) -> dict[str, str]:
    """The lazy 'meet in the middle on every issue' package."""
    return {i.id: i.option_ids[len(i.option_ids) // 2] for i in case.issues}


def _report(case: Case, an, checks, naive_score) -> None:
    a, b = case.roles
    print(f"\n{'=' * 72}\nCASE VALIDATION — {case.title} ({case.id})\n{'=' * 72}")
    print(f"\nOutcome space      : {an.n_packages:,} packages")
    print(f"Max joint value    : {an.max_joint}")
    print(f"Max individual     : {a}={an.max_payoff[a]}  {b}={an.max_payoff[b]}")
    print(f"BATNAs             : {a}={an.batnas[a]}  {b}={an.batnas[b]}")
    print(f"ZOPA               : {an.zopa_size:,} packages "
          f"({an.zopa_size / an.n_packages:.1%})")
    print(f"Pareto frontier    : {len(an.pareto_front)} payoff pairs")
    if an.nash_solution:
        print(f"Nash solution      : {a}={an.nash_solution[a]} {b}={an.nash_solution[b]}"
              f"  joint={an.nash_solution[a] + an.nash_solution[b]}")
        print(f"                     {_pkg_str(an.nash_solution['package'])}")
    if an.ks_solution:
        print(f"Kalai-Smorodinsky  : {a}={an.ks_solution[a]} {b}={an.ks_solution[b]}"
              f"  joint={an.ks_solution[a] + an.ks_solution[b]}")
    print(f"\nNaive midpoint     : {a}={naive_score['points_' + a]} "
          f"{b}={naive_score['points_' + b]}  "
          f"PER={naive_score['pareto_efficiency_ratio']:.1%}")

    print(f"\n{'-' * 72}\nCHECKS\n{'-' * 72}")
    for name, ok, detail in checks:
        mark = "PASS" if ok else "FAIL"
        print(f"  [{mark}] {name}")
        if detail:
            print(f"         {detail}")
    n_ok = sum(1 for _, ok, _ in checks if ok)
    print(f"\n{n_ok}/{len(checks)} checks passed\n")


def _pkg_str(pkg: dict) -> str:
    return " ".join(f"{k}={v}" for k, v in pkg.items())


def main() -> int:
    path = sys.argv[1] if len(sys.argv) > 1 else "cases/package_deal.yaml"
    case = Case.load(Path(path))
    try:
        validate(case)
    except ValidationError as e:
        print(f"\nVALIDATION FAILED: {e}\n", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
