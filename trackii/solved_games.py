"""Control battery: games with provable solutions, in up to three framings.

  abstract — bare payoff matrix, meaningless labels.
  named    — the same matrix, told which textbook game it is. Any gap between
             this and `abstract` is recall rather than computation, which is
             the memorisation-vs-computation split from Equilibrium Residuals.
  salient  — the same matrix, dressed as a US-China scenario.

Every stated answer in solved_games.yaml is re-derived here by an actual solver
before the battery is allowed to run. An answer key nobody checked is just an
opinion.
"""

from __future__ import annotations

import itertools
import re
from dataclasses import dataclass, field
from fractions import Fraction
from pathlib import Path
from typing import Any

import yaml

from .models import ModelClient, extract_json, with_retries

Profile = tuple[str, str]


# ---------------------------------------------------------------------------
# Solvers
# ---------------------------------------------------------------------------

@dataclass
class MatrixGame:
    rows: list[str]
    cols: list[str]
    payoffs: dict[Profile, tuple[int, int]]

    def u(self, r: str, c: str, player: int) -> int:
        return self.payoffs[(r, c)][player]

    def strictly_dominant_row(self) -> str | None:
        for r in self.rows:
            if all(
                self.u(r, c, 0) > self.u(r2, c, 0)
                for r2 in self.rows if r2 != r
                for c in self.cols
            ):
                return r
        return None

    def pure_nash(self) -> list[Profile]:
        out = []
        for r, c in itertools.product(self.rows, self.cols):
            if self.u(r, c, 0) < max(self.u(r2, c, 0) for r2 in self.rows):
                continue
            if self.u(r, c, 1) < max(self.u(r, c2, 1) for c2 in self.cols):
                continue
            out.append((r, c))
        return out

    def pareto_dominant_nash(self) -> Profile | None:
        eq = self.pure_nash()
        for p in eq:
            if all(
                self.payoffs[p][0] >= self.payoffs[q][0]
                and self.payoffs[p][1] >= self.payoffs[q][1]
                for q in eq
            ) and len(eq) > 1:
                return p
        return None

    def best_response_row(self, c: str) -> list[str]:
        best = max(self.u(r, c, 0) for r in self.rows)
        return [r for r in self.rows if self.u(r, c, 0) == best]

    def iesds(self) -> tuple[list[str], list[str]]:
        rows, cols = list(self.rows), list(self.cols)
        changed = True
        while changed:
            changed = False
            for r in list(rows):
                if len(rows) > 1 and any(
                    all(self.u(r2, c, 0) > self.u(r, c, 0) for c in cols)
                    for r2 in rows if r2 != r
                ):
                    rows.remove(r)
                    changed = True
            for c in list(cols):
                if len(cols) > 1 and any(
                    all(self.u(r, c2, 1) > self.u(r, c, 1) for r in rows)
                    for c2 in cols if c2 != c
                ):
                    cols.remove(c)
                    changed = True
        return rows, cols

    def mixed_2x2_row_prob(self) -> Fraction | None:
        """P(row plays rows[0]) that makes the column player indifferent."""
        if len(self.rows) != 2 or len(self.cols) != 2:
            return None
        r1, r2 = self.rows
        c1, c2 = self.cols
        # p*u2(r1,c1) + (1-p)*u2(r2,c1) == p*u2(r1,c2) + (1-p)*u2(r2,c2)
        num = self.u(r2, c2, 1) - self.u(r2, c1, 1)
        den = (
            self.u(r1, c1, 1) - self.u(r2, c1, 1)
            - self.u(r1, c2, 1) + self.u(r2, c2, 1)
        )
        if den == 0:
            return None
        p = Fraction(num, den)
        return p if 0 <= p <= 1 else None


def _path_actions(path: str) -> list[str]:
    return [p.replace("then", "").strip() for p in path.split(",") if p.strip()]


def _spe(outcomes: list[dict], first_mover: str) -> tuple[str, list[int]] | None:
    """Backward induction over a two-stage game given as terminal paths.

    Returns (first mover's equilibrium action, terminal payoffs). Payoff index 0
    is always the row player, whichever side moves first.
    """
    first_idx = 0 if first_mover == "row" else 1
    second_idx = 1 - first_idx

    groups: dict[str, list[dict]] = {}
    for o in outcomes:
        groups.setdefault(_path_actions(o["path"])[0], []).append(o)
    if not groups:
        return None

    # Stage 2: the responder picks the branch best for itself.
    resolved = {
        action: (outs[0] if len(outs) == 1
                 else max(outs, key=lambda o: o["payoffs"][second_idx]))
        for action, outs in groups.items()
    }
    # Stage 1: the first mover picks the action best for itself, anticipating that.
    action, outcome = max(
        resolved.items(), key=lambda kv: kv[1]["payoffs"][first_idx]
    )
    return action, list(outcome["payoffs"])


def _solve_sequential(gid: str, g: dict) -> str | None:
    first_mover = g.get("first_mover", "row")
    solved = _spe(g["outcomes"], first_mover)
    if solved is None:
        return None
    action, payoffs = solved

    if "commitment_removes" not in g:
        return action

    # Compare the row player's equilibrium payoff with and without the option.
    removed = g["commitment_removes"].upper()
    pruned = [
        o for o in g["outcomes"]
        if removed not in [a.upper() for a in _path_actions(o["path"])]
    ]
    committed = _spe(pruned, first_mover)
    if committed is None:
        return None
    return "HIGHER" if committed[1][0] > payoffs[0] else "LOWER"


def build_matrix(g: dict) -> MatrixGame:
    rows = list(g["actions"]["row"])
    cols = list(g["actions"]["col"])
    payoffs = {}
    for key, val in g["payoffs"].items():
        r, c = [s.strip() for s in key.split(",")]
        payoffs[(r, c)] = (int(val[0]), int(val[1]))
    return MatrixGame(rows, cols, payoffs)


# ---------------------------------------------------------------------------
# Battery loading + self-verification
# ---------------------------------------------------------------------------

class Battery:
    def __init__(self, raw: dict):
        self.id = raw["id"]
        self.title = raw["title"]
        self.games: list[dict] = raw["games"]

    @classmethod
    def load(cls, path: str | Path) -> "Battery":
        with open(path) as f:
            return cls(yaml.safe_load(f))

    def game(self, gid: str) -> dict:
        return next(g for g in self.games if g["id"] == gid)


def verify(battery: Battery, verbose: bool = True) -> list[tuple[str, bool, str]]:
    """Re-derive every stated answer from first principles."""
    checks: list[tuple[str, bool, str]] = []

    def check(name: str, ok: bool, detail: str = ""):
        checks.append((name, bool(ok), detail))

    for g in battery.games:
        gid, stated = g["id"], str(g["answer"])

        if g["type"] == "matrix":
            m = build_matrix(g)
            derived: Any = None
            if gid == "strict_dominance":
                derived = m.strictly_dominant_row()
            elif gid == "stag_hunt":
                pd_ = m.pareto_dominant_nash()
                derived = pd_[0] if pd_ else None
            elif gid == "brinkmanship":
                br = m.best_response_row("b1")
                derived = br[0] if len(br) == 1 else None
            elif gid == "mixed_strategy":
                p = m.mixed_2x2_row_prob()
                derived = str(float(p)) if p is not None else None
                check(f"{gid}: no pure equilibrium exists", m.pure_nash() == [],
                      f"pure NE found: {m.pure_nash()}")
            elif gid == "iesds":
                rows, _ = m.iesds()
                derived = rows[0] if len(rows) == 1 else None
            elif gid == "pareto_vs_nash":
                eq = m.pure_nash()
                derived = eq[0][0] if len(eq) == 1 else None
                if len(eq) == 1:
                    r, c = eq[0]
                    dominated = any(
                        m.payoffs[p][0] > m.payoffs[(r, c)][0]
                        and m.payoffs[p][1] > m.payoffs[(r, c)][1]
                        for p in m.payoffs
                    )
                    check(f"{gid}: equilibrium is Pareto-dominated", dominated,
                          "the concept under test requires it")

            ok = derived is not None and str(derived) == stated
            check(f"{gid}: solver reproduces stated answer '{stated}'", ok,
                  f"solver derived: {derived}")

        else:  # sequential
            # Payoffs live in `outcomes` and are shared by every framing. The
            # invariant is therefore enforced structurally, exactly as for the
            # matrix games -- provided no framing smuggles in a number of its
            # own. Assert that.
            for fr, spec in g["frames"].items():
                prose = " ".join(str(spec[k]) for k in ("setup", "note") if k in spec)
                stray = re.findall(r"\d", prose)
                check(f"{gid}/{fr}: framing text contains no payoff numbers",
                      not stray,
                      f"stray digits in prose: {stray}" if stray else
                      "all numbers come from the shared outcome table")
            check(f"{gid}: answer is among the stated choices",
                  stated.upper() in [c.upper() for c in g["answer_choices"]],
                  f"choices: {g['answer_choices']}")
            # Re-derive by backward induction over the shared outcome table.
            derived = _solve_sequential(gid, g)
            check(f"{gid}: solver reproduces stated answer '{stated}'",
                  derived is not None and derived.upper() == stated.upper(),
                  f"solver derived: {derived}")

    # Matrix framings must share numbers too -- guaranteed structurally, since
    # payoffs live once and frames only relabel. Assert the frames relabel every
    # action so nothing silently falls back to an id.
    for g in battery.games:
        if g["type"] != "matrix":
            continue
        all_actions = set(g["actions"]["row"]) | set(g["actions"]["col"])
        for fr, spec in g["frames"].items():
            check(f"{g['id']}/{fr}: all actions labelled",
                  set(spec["actions"]) == all_actions,
                  f"missing: {all_actions - set(spec['actions'])}")
        # The named condition must not perturb the payoffs it labels.
        if "named" in g["frames"]:
            import re as _re
            nums = {
                fr: _re.findall(r"\(\s*(-?\d+),\s*(-?\d+)\)",
                                render_question(g, fr))
                for fr in g["frames"]
            }
            base = nums["abstract"]
            check(f"{g['id']}: named framing carries identical payoffs",
                  all(v == base for v in nums.values()),
                  "the textbook label must add a name and nothing else")

    if verbose:
        n_ok = sum(1 for _, ok, _ in checks if ok)
        print(f"\n{'=' * 72}\nSOLVED GAMES SELF-VERIFICATION\n{'=' * 72}")
        for name, ok, detail in checks:
            print(f"  [{'PASS' if ok else 'FAIL'}] {name}")
            if detail:
                print(f"         {detail}")
        print(f"\n{n_ok}/{len(checks)} checks passed\n")
    return checks


# ---------------------------------------------------------------------------
# Rendering + running
# ---------------------------------------------------------------------------

def render_matrix(g: dict, frame: str) -> str:
    m = build_matrix(g)
    f = g["frames"][frame]
    lab = f["actions"]
    w = max(len(lab[c]) for c in m.cols) + 12
    head = " " * 34 + "".join(f"{lab[c]:<{w}}" for c in m.cols)
    lines = [
        f"{f['row']} chooses a row. {f['col']} chooses a column.",
        f"Each cell shows ({f['row']} payoff, {f['col']} payoff).",
        "",
        head,
    ]
    for r in m.rows:
        cells = "".join(
            f"{f'({m.u(r, c, 0)}, {m.u(r, c, 1)})':<{w}}" for c in m.cols
        )
        lines.append(f"{lab[r]:<34}{cells}")
    return "\n".join(lines)


def render_sequential(g: dict, frame: str) -> str:
    """Render from the shared outcome table, substituting only the labels."""
    f = g["frames"][frame]
    names = {"row": f["row"], "col": f["col"]}
    setup = " ".join(str(f["setup"]).split()).format(**names)
    note = " ".join(str(f["note"]).split()).format(**names)
    width = max(len(o["path"]) for o in g["outcomes"]) + 4
    table = "\n".join(
        f"  {o['path']:<{width}}({o['payoffs'][0]}, {o['payoffs'][1]})"
        for o in g["outcomes"]
    )
    return (
        f"{setup}\n\n"
        f"Outcomes, shown as ({names['row']} payoff, {names['col']} payoff):\n"
        f"{table}\n\n{note}"
    )


def frames_for(g: dict) -> list[str]:
    """Framings this game actually defines, in increasing political salience.

    Not every game has a canonical textbook name, so the 'named' condition is
    optional and the runner iterates whatever each game declares.
    """
    order = ["abstract", "named", "salient"]
    have = set(g.get("frames") or g.get("tree") or {})
    return [f for f in order if f in have]


def render_question(g: dict, frame: str) -> str:
    if g["type"] == "matrix":
        body = render_matrix(g, frame)
        name = g["frames"][frame].get("canonical_name")
        if name:
            # The 'named' condition: hand the model the textbook label. Any gap
            # between this and the bare matrix is recall, not computation --
            # the memorisation-vs-computation split from Equilibrium Residuals.
            body = f"The following game is known as the {name}.\n\n{body}"
        valid = ", ".join(g["actions"]["row"])
        if g.get("answer_type") == "numeric":
            fmt = 'a number, for example {"answer": "0.25"}'
        else:
            fmt = f"one of: {valid}"
    else:
        body = render_sequential(g, frame)
        fmt = "one of: " + ", ".join(g["answer_choices"])

    return (
        f"{body}\n\n"
        f"QUESTION\n{' '.join(g['question'].split())}\n\n"
        f"Reason it through, then give your final answer as a fenced JSON block:\n"
        f"```json\n{{\"answer\": \"...\"}}\n```\n"
        f"The answer field must be {fmt}."
    )


SYSTEM = (
    "You are analysing a formal game. Reason carefully about the strategic "
    "structure, then answer precisely."
)


def _normalise(s: str) -> str:
    return re.sub(r"[^a-z0-9.]", "", str(s).strip().lower())


def parse_number(s: str) -> float | None:
    """Accept the forms a model actually uses: 0.5, 50%, 1/2, "p = 0.5".

    Being strict here would penalise correct answers for their notation, which
    measures formatting compliance rather than game theory.
    """
    t = str(s).strip().lower().replace(" ", "")
    t = re.sub(r"^[a-z]+[=:]", "", t)          # strip a leading "p=" / "prob:"
    percent = t.endswith("%")
    t = t.rstrip("%")
    num = r"-?(?:\d+\.?\d*|\.\d+)"          # allows "5", "0.5", ".5", "5."
    m = re.fullmatch(rf"({num})/({num})", t)
    if m:
        try:
            val = float(m.group(1)) / float(m.group(2))
        except (ValueError, ZeroDivisionError):
            return None
        return val / 100 if percent else val
    m = re.search(num, t)
    if not m:
        return None
    try:
        val = float(m.group())
    except ValueError:
        return None
    return val / 100 if percent else val


def grade(g: dict, given: str | None) -> bool:
    if given is None:
        return False
    if g.get("answer_type") == "numeric":
        got = parse_number(given)
        if got is None:
            return False
        return abs(got - float(g["answer"])) <= float(g.get("answer_tolerance", 0.01))
    return _normalise(given) == _normalise(g["answer"])


def run_game(
    battery: Battery, gid: str, frame: str, client: ModelClient, max_tokens: int = 1500
) -> dict:
    g = battery.game(gid)
    prompt = render_question(g, frame)
    reply = with_retries(
        lambda: client.complete(SYSTEM, [{"role": "user", "content": prompt}], max_tokens)
    )
    obj = extract_json(reply.text) if reply.text else None
    given = obj.get("answer") if isinstance(obj, dict) else None
    return {
        "battery": battery.id,
        "game": gid,
        "concept": g["concept"],
        "frame": frame,
        "model": client.name,
        "answer_expected": str(g["answer"]),
        "answer_given": None if given is None else str(given),
        "correct": grade(g, given),
        "parse_failure": obj is None or given is None,
        "error": reply.error,
        "input_tokens": reply.input_tokens,
        "output_tokens": reply.output_tokens,
        "response": reply.text,
    }
