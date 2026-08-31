"""End-to-end pipeline tests using the deterministic mock client.

These exercise every downstream path -- prompting, JSON extraction, package
validation, agreement detection, scoring -- without API keys or spend.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from trackii.case import Case
from trackii.engine import run_negotiation, _coerce_package
from trackii.models import REGISTRY, MockClient, extract_json
from trackii.scoring import analyze, score_outcome

ROOT = Path(__file__).resolve().parents[1]
CASE = Case.load(ROOT / "cases" / "package_deal.yaml")
AN = analyze(CASE)
OPTION_SPACE = {i.id: list(i.option_ids) for i in CASE.issues}


def mock_clients(seed=0):
    return {
        r: MockClient(REGISTRY["mock"], OPTION_SPACE, seed=seed + k)
        for k, r in enumerate(CASE.roles)
    }


# -- JSON extraction ---------------------------------------------------------

def test_extract_fenced_json():
    assert extract_json('blah\n```json\n{"a": 1}\n```\ntail') == {"a": 1}


def test_extract_prefers_last_block():
    txt = '```json\n{"a": 1}\n```\nactually\n```json\n{"a": 2}\n```'
    assert extract_json(txt) == {"a": 2}


def test_extract_bare_object_with_nesting():
    assert extract_json('I propose {"package": {"x": "y"}} ok') == {
        "package": {"x": "y"}
    }


def test_extract_ignores_braces_inside_strings():
    assert extract_json('{"a": "not } a brace"}') == {"a": "not } a brace"}


def test_extract_returns_none_on_garbage():
    assert extract_json("no json here at all") is None
    assert extract_json("```json\n{broken\n```") is None


# -- package coercion --------------------------------------------------------

def test_coerce_valid_package():
    pkg = {i.id: i.option_ids[0] for i in CASE.issues}
    assert _coerce_package(CASE, {"package": pkg}) == pkg


def test_coerce_accepts_bare_mapping():
    pkg = {i.id: i.option_ids[0] for i in CASE.issues}
    assert _coerce_package(CASE, pkg) == pkg


def test_coerce_normalises_brackets_and_case():
    pkg = {i.id: i.option_ids[0] for i in CASE.issues}
    noisy = {k: f"[{v.upper()}]" for k, v in pkg.items()}
    assert _coerce_package(CASE, noisy) == pkg


def test_coerce_rejects_incomplete_package():
    pkg = {i.id: i.option_ids[0] for i in CASE.issues}
    del pkg["tariffs"]
    assert _coerce_package(CASE, pkg) is None


def test_coerce_rejects_invalid_option():
    pkg = {i.id: i.option_ids[0] for i in CASE.issues}
    pkg["tariffs"] = "t99"
    assert _coerce_package(CASE, pkg) is None


# -- full negotiation --------------------------------------------------------

def test_negotiation_runs_end_to_end():
    res = run_negotiation(CASE, "abstract", mock_clients(), rounds=2, seed=1)
    assert res.errors == []
    assert len(res.transcript) >= 2 * 2 + 2
    assert res.case_id == CASE.id
    assert res.first_speaker in CASE.roles
    assert res.closer in CASE.roles


def test_negotiation_is_deterministic_under_seed():
    a = run_negotiation(CASE, "abstract", mock_clients(7), rounds=2, seed=3)
    b = run_negotiation(CASE, "abstract", mock_clients(7), rounds=2, seed=3)
    assert a.agreement == b.agreement
    assert a.package == b.package
    assert a.first_speaker == b.first_speaker


def test_agreement_implies_matching_final_packages():
    """Agreement is never recorded unless both sides landed on the same package."""
    any_deal = False
    for s in range(14):
        res = run_negotiation(CASE, "abstract", mock_clients(s), rounds=1, seed=s)
        if res.agreement:
            any_deal = True
            assert res.package is not None
            assert CASE.is_valid_package(res.package)
            # Both sides' recorded final offers must equal the adopted package.
            for role in CASE.roles:
                assert res.final_offers[role] == res.package
        else:
            offers = [res.final_offers[r] for r in CASE.roles]
            assert offers[0] != offers[1] or None in offers
    assert any_deal, "mock never closed a deal; the agreement path went untested"


def test_scoring_accepts_engine_output():
    res = run_negotiation(CASE, "abstract", mock_clients(), rounds=1, seed=5)
    s = score_outcome(CASE, AN, res.package, res.agreement)
    assert s["agreement"] is res.agreement
    if not res.agreement:
        assert s["impasse_with_zopa"] is True


@pytest.mark.parametrize("frame", ["abstract", "neutral", "salient", "salient_zh"])
def test_all_frames_run(frame):
    res = run_negotiation(CASE, frame, mock_clients(), rounds=1, seed=2)
    assert res.frame == frame
    assert res.errors == []


def test_label_swap_changes_prompt_not_payoffs():
    normal = CASE.render_role_sheet("salient", "DELTA", label_swap=False)
    swapped = CASE.render_role_sheet("salient", "DELTA", label_swap=True)
    assert "United States" in normal
    assert "People's Republic of China" in swapped
    # Same point schedule in both.
    for issue in CASE.issues:
        for oid in issue.option_ids:
            pts = issue.points[oid]["DELTA"]
            assert f"—  {pts} points" in normal
            assert f"—  {pts} points" in swapped


def test_role_sheet_never_leaks_the_other_side():
    """A player must not be able to see their counterpart's valuations."""
    import re

    for role, other in [("DELTA", "OMEGA"), ("OMEGA", "DELTA")]:
        sheet = CASE.render_role_sheet("salient", role)
        for issue in CASE.issues:
            for oid in issue.option_ids:
                line = next(l for l in sheet.splitlines() if f"[{oid}] " in l)
                shown = re.search(r"—\s+(-?\d+) points\s*$", line)
                assert shown, f"no point value rendered for {oid}"
                assert int(shown.group(1)) == issue.points[oid][role]
        # The counterpart's totals must not appear anywhere in the sheet.
        assert str(CASE.max_payoff(other)) not in sheet.split("RESERVATION")[0].split(
            "Maximum possible total"
        )[1]


def test_frame_blind_player_shows_zero_framing_tax():
    """Null control for the headline experiment.

    The mock client ignores prompt content entirely, so it is frame-blind by
    construction. If the harness itself introduced any frame-dependent artifact
    -- different prompt lengths nudging truncation, option ordering drifting
    between frames, seeds consumed at different rates -- this player would still
    score differently across frames. It must not.
    """
    outcomes = {}
    for frame in ("abstract", "neutral", "salient", "salient_zh"):
        res = run_negotiation(CASE, frame, mock_clients(11), rounds=2, seed=4)
        s = score_outcome(CASE, AN, res.package, res.agreement)
        outcomes[frame] = (res.agreement, tuple(sorted((res.package or {}).items())),
                           s["joint"])

    assert len(set(outcomes.values())) == 1, (
        f"harness leaks a framing effect even for a frame-blind player: {outcomes}"
    )


def test_label_swap_also_shows_no_artifact_for_a_frame_blind_player():
    a = run_negotiation(CASE, "salient", mock_clients(11), rounds=2, seed=4,
                        label_swap=False)
    b = run_negotiation(CASE, "salient", mock_clients(11), rounds=2, seed=4,
                        label_swap=True)
    assert a.agreement == b.agreement
    assert a.package == b.package


# -- Mandarin frame ----------------------------------------------------------

def test_mandarin_frame_has_identical_payoffs():
    """The language control is only valid if the game is provably unchanged."""
    import re

    for role in CASE.roles:
        en = CASE.render_role_sheet("salient", role)
        zh = CASE.render_role_sheet("salient_zh", role)
        # Same point values, in the same order, in both languages.
        assert (re.findall(r"—\s+(-?\d+)\s", en)
                == re.findall(r"—\s+(-?\d+)\s", zh))
        assert str(CASE.batnas[role]) in zh
        assert str(CASE.max_payoff(role)) in zh


def test_mandarin_frame_prompt_is_fully_mandarin():
    """A half-translated prompt would confound language with content."""
    sheet = CASE.render_role_sheet("salient_zh", "DELTA")
    for leaked in ["CONFIDENTIAL", "SITUATION", "RESERVATION", "RULES", "points"]:
        assert leaked not in sheet, f"English boilerplate leaked: {leaked}"
    # And it really is Chinese, not just an absence of English.
    assert sum(1 for ch in sheet if "\u4e00" <= ch <= "\u9fff") > 200


def test_mandarin_negotiation_runs_end_to_end():
    res = run_negotiation(CASE, "salient_zh", mock_clients(3), rounds=2, seed=2)
    assert res.errors == []
    assert res.frame == "salient_zh"
    # The closing phase must be reached in Mandarin too.
    assert any(t.phase.startswith("close") for t in res.transcript)


def test_mandarin_option_ids_are_unchanged():
    """Option ids stay ASCII so parsing is identical across languages."""
    sheet = CASE.render_role_sheet("salient_zh", "OMEGA")
    for issue in CASE.issues:
        for oid in issue.option_ids:
            assert f"[{oid}]" in sheet
