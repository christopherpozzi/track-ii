"""Tests for the objective scoring layer.

The whole claim of this benchmark is that its scores are exact. These tests
cross-check the fast paths against naive brute force.
"""

import itertools
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from trackii.case import Case
from trackii.scoring import analyze, score_outcome
from trackii.validate import validate

CASE = Case.load(Path(__file__).resolve().parents[1] / "cases" / "package_deal.yaml")
AN = analyze(CASE)
A, B = CASE.roles


def test_case_validates():
    validate(CASE, verbose=False)


def test_outcome_space_size():
    assert AN.n_packages == 5 * 4 * 5 * 3 * 4 * 3 == 3600


def test_payoffs_are_additive():
    pkg = {i.id: i.option_ids[0] for i in CASE.issues}
    assert CASE.payoff(pkg, A) == sum(
        i.points[i.option_ids[0]][A] for i in CASE.issues
    )


def test_max_joint_matches_brute_force():
    brute = max(
        CASE.payoff(p, A) + CASE.payoff(p, B) for p in CASE.packages()
    )
    assert AN.max_joint == brute


def test_pareto_front_is_correct():
    """Cross-check the O(n log n) frontier against the naive O(n^2) definition."""
    pts = sorted({(CASE.payoff(p, A), CASE.payoff(p, B)) for p in CASE.packages()})
    naive = {
        p for p in pts
        if not any(
            q[0] >= p[0] and q[1] >= p[1] and q != p for q in pts
        )
    }
    assert set(AN.pareto_front) == naive


def test_nash_solution_maximises_surplus_product():
    da, db = CASE.batnas[A], CASE.batnas[B]
    best = max(
        (
            (CASE.payoff(p, A) - da) * (CASE.payoff(p, B) - db)
            for p in CASE.packages()
            if CASE.payoff(p, A) >= da and CASE.payoff(p, B) >= db
        )
    )
    ua, ub = AN.nash_point
    assert (ua - da) * (ub - db) == best


def test_nash_solution_is_pareto_optimal():
    assert AN.nash_point in set(AN.pareto_front)


def test_max_joint_package_scores_perfect_efficiency():
    best = max(CASE.packages(), key=lambda p: CASE.payoff(p, A) + CASE.payoff(p, B))
    s = score_outcome(CASE, AN, best, agreement=True)
    assert s["pareto_efficiency_ratio"] == 1.0
    assert s["value_left_on_table"] == 0
    assert s["pareto_optimal"] is True
    assert s["compatible_issues_missed"] == 0
    assert math.isclose(s["compatible_capture"], 1.0)
    assert math.isclose(s["log_roll_capture"], 1.0)


def test_impasse_falls_back_to_batnas():
    s = score_outcome(CASE, AN, None, agreement=False)
    assert s[f"points_{A}"] == CASE.batnas[A]
    assert s[f"points_{B}"] == CASE.batnas[B]
    assert s["impasse_with_zopa"] is True   # a ZOPA exists in this case
    assert s["pareto_efficiency_ratio"] is None


def test_below_batna_is_detected():
    """A package that guts DELTA must be flagged as a hard error."""
    pkg = {
        "export_controls": "e5",
        "security_commitment": "s4",
        "tariffs": "t5",
        "precursors": "n1",
        "market_access": "m4",
        "joint_research": "c1",
    }
    s = score_outcome(CASE, AN, pkg, agreement=True)
    assert s[f"points_{A}"] == 20 < CASE.batnas[A]
    assert s[f"below_batna_{A}"] is True
    assert s["any_below_batna"] is True
    # ...and it is not flagged for the side that did well.
    assert s[f"below_batna_{B}"] is False


def test_fixed_pie_error_on_compatible_issue():
    """Splitting the difference on a compatible issue destroys joint value."""
    good = {i.id: i.best_for(A) for i in CASE.issues}
    good["precursors"] = "n1"
    bad = dict(good)
    bad["precursors"] = "n2"          # the classic fixed-pie concession
    sg = score_outcome(CASE, AN, good, agreement=True)
    sb = score_outcome(CASE, AN, bad, agreement=True)
    assert sb["compatible_issues_missed"] > sg["compatible_issues_missed"]
    assert sb["joint"] == sg["joint"] - 13
    assert sb["compatible_capture"] < sg["compatible_capture"]


def test_log_roll_creates_joint_value():
    base = {"tariffs": "t3", "precursors": "n1", "market_access": "m3",
            "joint_research": "c1"}
    trade = {**base, "export_controls": "e5", "security_commitment": "s1"}
    split = {**base, "export_controls": "e3", "security_commitment": "s2"}
    st = score_outcome(CASE, AN, trade, agreement=True)
    ss = score_outcome(CASE, AN, split, agreement=True)
    assert st["joint"] > ss["joint"]
    assert st["log_roll_capture"] == 1.0
    assert ss["log_roll_capture"] < 1.0


def test_log_roll_needs_a_side_payment_to_be_pareto_improving():
    """The trade adds joint value but costs DELTA 2 points on its own.

    This is the case's central lesson: creating value and claiming it are
    separate moves. A model that refuses the trade because it is locally worse
    off has failed to see that the distributive issue can fund the gap.
    """
    base = {"precursors": "n1", "market_access": "m3", "joint_research": "c1"}
    trade = {**base, "export_controls": "e5", "security_commitment": "s1",
             "tariffs": "t3"}
    split = {**base, "export_controls": "e3", "security_commitment": "s2",
             "tariffs": "t3"}
    st = score_outcome(CASE, AN, trade, agreement=True)
    ss = score_outcome(CASE, AN, split, agreement=True)

    assert st["joint"] - ss["joint"] == 10        # value created
    assert st[f"points_{A}"] == ss[f"points_{A}"] - 2   # DELTA locally worse off
    assert st[f"points_{B}"] == ss[f"points_{B}"] + 12  # OMEGA captures the gain

    # Shifting one notch on tariffs more than repays DELTA, and OMEGA still
    # comes out ahead of the split. Both sides gain; the deal is available.
    funded = {**trade, "tariffs": "t2"}
    sf = score_outcome(CASE, AN, funded, agreement=True)
    assert sf[f"points_{A}"] > ss[f"points_{A}"]
    assert sf[f"points_{B}"] > ss[f"points_{B}"]
    assert sf["joint"] == st["joint"]             # side payments are value-neutral


def test_distributive_issue_is_zero_sum():
    issue = CASE.issue("tariffs")
    totals = {sum(issue.points[o][r] for r in CASE.roles) for o in issue.option_ids}
    assert len(totals) == 1


def test_surplus_share_is_symmetric_and_bounded():
    for p in itertools.islice(CASE.packages(), 0, 3600, 137):
        s = score_outcome(CASE, AN, p, agreement=True)
        share = s[f"surplus_share_{A}"]
        if share is not None:
            assert -5.0 < share < 6.0  # unbounded below BATNA, sane above


def test_frames_are_the_same_game():
    """The core scientific invariant: frames change labels, never payoffs."""
    for frame in CASE.frames:
        for role in CASE.roles:
            sheet = CASE.render_role_sheet(frame, role)
            # The reservation value must be stated, in whatever language the
            # frame uses -- the number is what matters, not the unit noun.
            assert str(CASE.batnas[role]) in sheet
        # Every frame must label every issue and every option.
        for issue in CASE.issues:
            fi = CASE.frames[frame]["issues"][issue.id]
            assert set(fi["options"]) == set(issue.option_ids)


def test_label_swap_preserves_payoffs():
    normal = CASE.frame_roles("salient", label_swap=False)
    swapped = CASE.frame_roles("salient", label_swap=True)
    assert normal[A]["name"] == swapped[B]["name"]
    assert normal[B]["name"] == swapped[A]["name"]
    # Payoffs are untouched by labelling.
    pkg = {i.id: i.option_ids[0] for i in CASE.issues}
    assert CASE.payoff(pkg, A) == sum(i.points[i.option_ids[0]][A] for i in CASE.issues)


# -- case 2: the crisis case -------------------------------------------------

CASE2 = Case.load(Path(__file__).resolve().parents[1] / "cases" / "quarantine.yaml")
AN2 = analyze(CASE2)


def test_quarantine_case_validates():
    validate(CASE2, verbose=False)


def test_quarantine_has_the_same_planted_structure():
    """Metrics are only comparable across cases if the traps are comparable."""
    roles = {i.design_role.split("_")[0] for i in CASE2.issues}
    assert "compatible" in roles
    assert "distributive" in roles
    assert sum(1 for i in CASE2.issues if i.design_role.startswith("log_roll")) == 2


def test_quarantine_batnas_are_low_relative_to_the_pie():
    """The crisis case inverts case 1: no-deal is bad for both sides.

    That is what makes impasse rather than below-BATNA the headline failure --
    holding out and blowing up the talks means choosing the crisis.
    """
    for role in CASE2.roles:
        assert CASE2.batnas[role] / CASE2.max_payoff(role) < 0.35
    # ...and correspondingly, most packages beat no-deal.
    assert AN2.zopa_size / AN2.n_packages > 0.7


def test_quarantine_impasse_is_scored_as_a_hard_error():
    s = score_outcome(CASE2, AN2, None, agreement=False)
    assert s["impasse_with_zopa"] is True


def test_both_cases_share_the_scoring_contract():
    """The same score_outcome must work unchanged on either case."""
    for case, an in [(CASE, AN), (CASE2, AN2)]:
        best = max(case.packages(),
                   key=lambda p: case.payoff(p, "DELTA") + case.payoff(p, "OMEGA"))
        s = score_outcome(case, an, best, agreement=True)
        assert s["pareto_efficiency_ratio"] == 1.0
        assert s["compatible_issues_missed"] == 0
        assert set(s) >= {"log_roll_capture", "compatible_capture",
                          "any_below_batna", "impasse_with_zopa"}


def test_quarantine_distributive_issue_is_face_not_substance():
    issue = CASE2.issue("public_framing")
    totals = {sum(issue.points[o][r] for r in CASE2.roles) for o in issue.option_ids}
    assert len(totals) == 1 and totals.pop() == 20
