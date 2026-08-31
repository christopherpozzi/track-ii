"""Objective scoring against the computable optimum.

Nothing in this module calls a language model. Every number here is derived by
brute-force enumeration of the outcome space and is exactly reproducible.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, asdict, field

from .case import Case, Package


@dataclass
class CaseAnalysis:
    """Everything knowable about the game before any model is called."""

    n_packages: int
    max_joint: int
    max_payoff: dict[str, int]
    batnas: dict[str, int]
    pareto_front: list[tuple[int, int]]
    zopa_size: int
    nash_solution: dict | None
    nash_point: tuple[int, int] | None
    ks_solution: dict | None
    ks_point: tuple[int, int] | None
    # per-issue structural facts used by the metrics
    log_roll_issues: list[str] = field(default_factory=list)
    compatible_issues: list[str] = field(default_factory=list)
    distributive_issues: list[str] = field(default_factory=list)
    max_joint_on: dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)


def analyze(case: Case) -> CaseAnalysis:
    a, b = case.roles
    da, db = case.batnas[a], case.batnas[b]

    points: list[tuple[int, int, Package]] = []
    for pkg in case.packages():
        points.append((case.payoff(pkg, a), case.payoff(pkg, b), pkg))

    max_joint = max(ua + ub for ua, ub, _ in points)

    # Pareto frontier over the (u_a, u_b) point cloud.
    uniq = sorted({(ua, ub) for ua, ub, _ in points})
    front: list[tuple[int, int]] = []
    best_b = -math.inf
    for ua, ub in sorted(uniq, key=lambda p: (-p[0], -p[1])):
        if ub > best_b:
            front.append((ua, ub))
            best_b = ub
    front.sort()

    # Individually rational set (the ZOPA).
    ir = [(ua, ub, p) for ua, ub, p in points if ua >= da and ub >= db]

    nash = ks = None
    nash_pt = ks_pt = None
    if ir:
        # Nash bargaining solution: maximise the product of surpluses.
        ua, ub, pkg = max(ir, key=lambda t: (t[0] - da) * (t[1] - db))
        nash, nash_pt = {"package": pkg, a: ua, b: ub}, (ua, ub)

        # Discrete Kalai-Smorodinsky: maximise the smaller normalised surplus,
        # breaking ties toward higher joint value.
        ideal_a = max(u for u, _, _ in ir)
        ideal_b = max(u for _, u, _ in ir)

        def ks_key(t):
            ga = (t[0] - da) / (ideal_a - da) if ideal_a > da else 0.0
            gb = (t[1] - db) / (ideal_b - db) if ideal_b > db else 0.0
            return (min(ga, gb), t[0] + t[1])

        ua, ub, pkg = max(ir, key=ks_key)
        ks, ks_pt = {"package": pkg, a: ua, b: ub}, (ua, ub)

    by_role = {i.design_role: i for i in case.issues}
    return CaseAnalysis(
        n_packages=len(points),
        max_joint=max_joint,
        max_payoff={r: case.max_payoff(r) for r in case.roles},
        batnas=dict(case.batnas),
        pareto_front=front,
        zopa_size=len(ir),
        nash_solution=nash,
        nash_point=nash_pt,
        ks_solution=ks,
        ks_point=ks_pt,
        log_roll_issues=[i.id for i in case.issues if i.design_role.startswith("log_roll")],
        compatible_issues=[i.id for i in case.issues if i.design_role.startswith("compatible")],
        distributive_issues=[i.id for i in case.issues if i.design_role == "distributive"],
        max_joint_on={
            i.id: max(sum(i.points[o][r] for r in case.roles) for o in i.option_ids)
            for i in case.issues
        },
    )


def _joint_on(case: Case, package: Package, issue_ids: list[str]) -> int:
    return sum(
        sum(case.issue(iid).points[package[iid]][r] for r in case.roles)
        for iid in issue_ids
    )


def score_outcome(
    case: Case,
    an: CaseAnalysis,
    package: Package | None,
    agreement: bool,
) -> dict:
    """Score one completed negotiation. `package` is None on impasse."""
    a, b = case.roles
    da, db = case.batnas[a], case.batnas[b]
    zopa_exists = an.zopa_size > 0

    out: dict = {
        "agreement": agreement,
        "zopa_exists": zopa_exists,
        # HARD ERROR: a deal existed that beat both BATNAs, and they missed it.
        "impasse_with_zopa": (not agreement) and zopa_exists,
    }

    if not agreement or package is None:
        out.update(
            {
                f"points_{a}": da,
                f"points_{b}": db,
                "joint": da + db,
                "pareto_efficiency_ratio": None,
                "pareto_optimal": False,
                "value_left_on_table": None,
                f"below_batna_{a}": False,
                f"below_batna_{b}": False,
                "any_below_batna": False,
                "surplus_share_" + a: None,
                "nash_distance": None,
                "log_roll_capture": None,
                "compatible_capture": None,
                "compatible_issues_missed": None,
                "distributive_share_" + a: None,
                "package": None,
            }
        )
        return out

    ua, ub = case.payoff(package, a), case.payoff(package, b)
    joint = ua + ub

    below_a, below_b = ua < da, ub < db
    surplus_total = (ua - da) + (ub - db)

    nash_dist = None
    if an.nash_point is not None:
        span = math.hypot(an.max_payoff[a], an.max_payoff[b]) or 1.0
        nash_dist = math.dist((ua, ub), an.nash_point) / span

    lr_max = sum(an.max_joint_on[i] for i in an.log_roll_issues) or 1
    cp_max = sum(an.max_joint_on[i] for i in an.compatible_issues) or 1
    dist_pts = sum(
        case.issue(i).points[package[i]][a] for i in an.distributive_issues
    )
    dist_max = sum(
        max(case.issue(i).points[o][a] for o in case.issue(i).option_ids)
        for i in an.distributive_issues
    ) or 1

    out.update(
        {
            f"points_{a}": ua,
            f"points_{b}": ub,
            "joint": joint,
            # VALUE CREATION
            "pareto_efficiency_ratio": joint / an.max_joint,
            "pareto_optimal": (ua, ub) in set(an.pareto_front),
            "value_left_on_table": an.max_joint - joint,
            "log_roll_capture": _joint_on(case, package, an.log_roll_issues) / lr_max,
            "compatible_capture": _joint_on(case, package, an.compatible_issues) / cp_max,
            "compatible_issues_missed": sum(
                1 for i in an.compatible_issues
                if package[i] != case.issue(i).best_for(a)
            ),
            # VALUE CLAIMING
            "surplus_share_" + a: ((ua - da) / surplus_total) if surplus_total > 0 else None,
            "distributive_share_" + a: dist_pts / dist_max,
            "nash_distance": nash_dist,
            # HARD ERRORS
            f"below_batna_{a}": below_a,
            f"below_batna_{b}": below_b,
            "any_below_batna": below_a or below_b,
            "package": dict(package),
        }
    )
    return out
