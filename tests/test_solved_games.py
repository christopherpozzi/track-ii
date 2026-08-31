"""Tests for the control battery.

The battery's whole value is that its answer key is provably right, so these
tests check the solvers against textbook games with known solutions -- not just
against the YAML, which would be circular.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from trackii.solved_games import (
    Battery, MatrixGame, build_matrix, grade, render_question, verify, _spe,
)

ROOT = Path(__file__).resolve().parents[1]
BATTERY = Battery.load(ROOT / "cases" / "solved_games.yaml")


def mg(payoffs, rows=("a1", "a2"), cols=("b1", "b2")):
    return MatrixGame(list(rows), list(cols), payoffs)


# -- solvers against textbook games -----------------------------------------

def test_prisoners_dilemma_dominance():
    """Canonical PD: defection strictly dominates and is the unique NE."""
    g = mg({("a1", "b1"): (3, 3), ("a1", "b2"): (0, 5),
            ("a2", "b1"): (5, 0), ("a2", "b2"): (1, 1)})
    assert g.strictly_dominant_row() == "a2"
    assert g.pure_nash() == [("a2", "b2")]


def test_stag_hunt_has_two_equilibria():
    g = mg({("a1", "b1"): (6, 6), ("a1", "b2"): (0, 4),
            ("a2", "b1"): (4, 0), ("a2", "b2"): (3, 3)})
    assert set(g.pure_nash()) == {("a1", "b1"), ("a2", "b2")}
    assert g.pareto_dominant_nash() == ("a1", "b1")
    assert g.strictly_dominant_row() is None   # neither action dominates


def test_matching_pennies_has_no_pure_equilibrium():
    g = mg({("a1", "b1"): (2, -2), ("a1", "b2"): (-2, 2),
            ("a2", "b1"): (-2, 2), ("a2", "b2"): (2, -2)})
    assert g.pure_nash() == []
    assert g.mixed_2x2_row_prob() == pytest.approx(0.5)


def test_asymmetric_mixed_equilibrium():
    """A mix that is not 50/50, to prove the solver is not hardcoding one."""
    g = mg({("a1", "b1"): (0, 0), ("a1", "b2"): (0, 3),
            ("a2", "b1"): (0, 6), ("a2", "b2"): (0, 0)})
    # Column indifferent when 6*(1-p) == 3*p  ->  p = 2/3
    assert float(g.mixed_2x2_row_prob()) == pytest.approx(2 / 3)


def test_chicken_best_response_is_to_yield():
    g = mg({("a1", "b1"): (-10, -10), ("a1", "b2"): (4, -2),
            ("a2", "b1"): (-2, 4), ("a2", "b2"): (0, 0)})
    assert g.best_response_row("b1") == ["a2"]
    assert g.best_response_row("b2") == ["a1"]


def test_iesds_resolves_to_single_action():
    g = build_matrix(BATTERY.game("iesds"))
    rows, cols = g.iesds()
    assert rows == ["a1"]
    assert len(cols) == 1


def test_iesds_leaves_undominated_game_alone():
    g = mg({("a1", "b1"): (2, -2), ("a1", "b2"): (-2, 2),
            ("a2", "b1"): (-2, 2), ("a2", "b2"): (2, -2)})
    rows, cols = g.iesds()
    assert len(rows) == 2 and len(cols) == 2


# -- backward induction ------------------------------------------------------

def test_spe_ignores_non_credible_threat():
    """The announced threat to FIGHT is not carried out, so entry is optimal."""
    outcomes = [
        {"path": "STAY OUT", "payoffs": [0, 10]},
        {"path": "ENTER, then FIGHT", "payoffs": [-3, 1]},
        {"path": "ENTER, then ACCOMMODATE", "payoffs": [4, 5]},
    ]
    assert _spe(outcomes, "row") == ("ENTER", [4, 5])


def test_spe_respects_a_credible_threat():
    """Same tree, but now fighting actually pays -- so staying out is right."""
    outcomes = [
        {"path": "STAY OUT", "payoffs": [0, 10]},
        {"path": "ENTER, then FIGHT", "payoffs": [-3, 8]},
        {"path": "ENTER, then ACCOMMODATE", "payoffs": [4, 5]},
    ]
    assert _spe(outcomes, "row") == ("STAY OUT", [0, 10])


def test_commitment_changes_the_equilibrium():
    g = BATTERY.game("commitment_value")
    full = _spe(g["outcomes"], "col")
    pruned = _spe([o for o in g["outcomes"] if "RETREAT" not in o["path"]], "col")
    assert full == ("PRESS", [1, 7])      # opponent presses; we retreat
    assert pruned == ("CONCEDE", [6, 2])  # retreat gone; opponent backs down
    assert pruned[1][0] > full[1][0]      # committing raises our payoff


# -- battery integrity -------------------------------------------------------

def test_battery_self_verifies():
    failures = [c for c in verify(BATTERY, verbose=False) if not c[1]]
    assert failures == [], f"answer key failed self-verification: {failures}"


@pytest.mark.parametrize("game", [g["id"] for g in BATTERY.games])
@pytest.mark.parametrize("frame", ["abstract", "salient"])  # named tested below
def test_every_game_renders_in_every_frame(game, frame):
    q = render_question(BATTERY.game(game), frame)
    assert "{" in q and "QUESTION" in q
    assert "{row}" not in q and "{col}" not in q   # no unsubstituted placeholders


def test_matrix_framings_render_identical_numbers():
    """The core invariant: relabelling must not move a single payoff."""
    import re

    for g in BATTERY.games:
        if g["type"] != "matrix":
            continue
        nums = {
            fr: re.findall(r"\(\s*(-?\d+),\s*(-?\d+)\)", render_question(g, fr))
            for fr in ("abstract", "salient")
        }
        assert nums["abstract"] == nums["salient"], g["id"]
        assert len(nums["abstract"]) == len(g["payoffs"])


def test_sequential_framings_render_identical_numbers():
    import re

    for g in BATTERY.games:
        if g["type"] == "matrix":
            continue
        nums = {
            fr: re.findall(r"-?\d+", render_question(g, fr))
            for fr in ("abstract", "salient")
        }
        assert nums["abstract"] == nums["salient"], g["id"]


# -- grading -----------------------------------------------------------------

def test_grade_exact_and_normalised():
    g = BATTERY.game("strict_dominance")
    assert grade(g, "a2")
    assert grade(g, " A2 ")
    assert grade(g, "[a2]")
    assert not grade(g, "a1")
    assert not grade(g, None)


def test_grade_numeric_accepts_equivalent_notations():
    """A correct answer must not be marked wrong for its notation."""
    g = BATTERY.game("mixed_strategy")
    for form in ["0.5", ".5", "50%", "1/2", "p = 0.5", "0.50"]:
        assert grade(g, form), form


def test_grade_numeric_rejects_out_of_tolerance():
    g = BATTERY.game("mixed_strategy")
    assert not grade(g, "0.6")
    assert not grade(g, "0.7")
    assert not grade(g, "60%")
    assert not grade(g, "2/3")
    assert grade(g, "0.51")     # inside the stated 0.02 tolerance


def test_parse_number_forms():
    from trackii.solved_games import parse_number

    assert parse_number("0.5") == pytest.approx(0.5)
    assert parse_number("50%") == pytest.approx(0.5)
    assert parse_number("2/3") == pytest.approx(2 / 3)
    assert parse_number("p=0.25") == pytest.approx(0.25)
    assert parse_number("nonsense") is None


# -- named-textbook-game condition -------------------------------------------

from trackii.solved_games import frames_for  # noqa: E402


def test_named_condition_exists_for_canonical_games():
    named = {g["id"] for g in BATTERY.games if "named" in frames_for(g)}
    assert {"strict_dominance", "stag_hunt", "brinkmanship",
            "mixed_strategy", "pareto_vs_nash"} <= named


def test_named_condition_states_the_textbook_name():
    q = render_question(BATTERY.game("strict_dominance"), "named")
    assert "Prisoner's Dilemma" in q
    assert "COOPERATE" in q and "DEFECT" in q


def test_named_condition_does_not_perturb_payoffs():
    """The label must add a name and nothing else."""
    import re

    for g in BATTERY.games:
        if "named" not in frames_for(g):
            continue
        nums = {
            fr: re.findall(r"\(\s*(-?\d+),\s*(-?\d+)\)", render_question(g, fr))
            for fr in frames_for(g)
        }
        base = nums["abstract"]
        assert all(v == base for v in nums.values()), g["id"]


def test_abstract_condition_never_names_the_game():
    """The whole point of the abstract condition is that recall can't help."""
    for g in BATTERY.games:
        q = render_question(g, "abstract")
        for name in ["Prisoner", "Stag Hunt", "Chicken", "Hawk", "Matching Pennies"]:
            assert name not in q, f"{g['id']} leaks '{name}' into the abstract frame"


def test_frames_for_is_ordered_by_salience():
    for g in BATTERY.games:
        fr = frames_for(g)
        assert fr[0] == "abstract"
        assert fr[-1] == "salient"
        assert fr == [f for f in ["abstract", "named", "salient"] if f in fr]
