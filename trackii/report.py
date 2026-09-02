"""Aggregate results.jsonl into a self-contained HTML microsite.

Self-contained by construction: inline SVG, inline CSS, inline JS, no external
requests. A left-hand dropdown selects the case; a top-centre switcher moves
between the summary and per-model views within it; each finding is a
full-viewport scroll-snap section with a next affordance.
Every chart ships direct value labels and a table view, so nothing depends on
colour alone.

Usage:  python -m trackii.report results/results.jsonl -o site/index.html
"""

from __future__ import annotations

import argparse
import gzip
import html as _html
import json
import re
import statistics as st
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

from .case import Case
from .engine import PROTOCOL, PROTOCOL_ZH, _example
from .models import REGISTRY
from .scoring import analyze

ROOT = Path(__file__).resolve().parents[1]

FRAME_ORDER = ["abstract", "neutral", "salient", "salient_zh"]
FRAME_LABEL = {
    "abstract": "Abstract",
    "neutral": "Neutral-real",
    "salient": "Politically salient",
    "salient_zh": "Salient (Mandarin)",
}
# Categorical slots 1-3, validated all-pairs in both modes.
SERIES = ["var(--series-1)", "var(--series-2)", "var(--series-3)"]


# ---------------------------------------------------------------------------
# Aggregation
# ---------------------------------------------------------------------------

def load(path: Path) -> list[dict]:
    """Read one JSONL file, or every JSONL under a directory.

    Accepts .gz transparently: live transcripts are large and natural-language,
    so they are committed compressed while the working files stay plain.
    """
    # rglob, not glob: live runs are archived under results/live/, and a
    # non-recursive walk would silently ignore exactly the records that matter.
    # But rglob also descends into results/discarded/, which holds runs
    # quarantined *because* they must never be aggregated -- the harness-bug
    # head-to-head among them. Skipping that directory is not optional.
    SKIP = {"discarded"}
    paths = (sorted(q for q in list(path.rglob("*.jsonl")) + list(path.rglob("*.jsonl.gz"))
                    if not SKIP & set(q.relative_to(path).parts))
             if path.is_dir() else [path])
    recs = []
    for q in paths:
        opener = gzip.open if q.suffix == ".gz" else open
        with opener(q, "rt") as f:
            for line in f:
                line = line.strip()
                if line:
                    recs.append(json.loads(line))
    return recs


def _mean(xs):
    xs = [x for x in xs if x is not None]
    return st.fmean(xs) if xs else None


def _rate(xs):
    xs = [bool(x) for x in xs if x is not None]
    return (sum(xs) / len(xs)) if xs else None


@dataclass
class Cell:
    n: int
    agreement_rate: float | None
    per: float | None
    below_batna: float | None
    impasse_zopa: float | None
    log_roll: float | None
    compatible: float | None
    distributive: float | None


def _cell(rows: list[dict]) -> Cell:
    sc = [r["score"] for r in rows]
    agreed = [s for s in sc if s.get("agreement")]
    return Cell(
        n=len(rows),
        agreement_rate=_rate([s.get("agreement") for s in sc]),
        per=_mean([s.get("pareto_efficiency_ratio") for s in agreed]),
        below_batna=_rate([s.get("any_below_batna") for s in agreed]),
        impasse_zopa=_rate([s.get("impasse_with_zopa") for s in sc]),
        log_roll=_mean([s.get("log_roll_capture") for s in agreed]),
        compatible=_mean([s.get("compatible_capture") for s in agreed]),
        distributive=_mean([s.get("distributive_share_DELTA") for s in agreed]),
    )


def selfplay_model(r: dict) -> str | None:
    ms = list(r["models"].values())
    return ms[0] if len(set(ms)) == 1 else None


def aggregate(recs: list[dict]) -> dict:
    negs = [r for r in recs if r.get("kind") == "negotiation"]
    games = [r for r in recs if r.get("kind") == "solved_game"]

    frames = defaultdict(list)
    frames_inst = defaultdict(list)          # (model, frame, instance) -> runs
    for r in (r for r in negs if r.get("experiment") == "frames"):
        m = selfplay_model(r)
        if m:
            frames[(m, r["frame"])].append(r)
            frames_inst[(m, r["frame"], r.get("case_id"))].append(r)

    nocomm = defaultdict(list)
    for r in (r for r in negs if r.get("experiment") == "nocomm"):
        m = selfplay_model(r)
        if m:
            nocomm[(m, r["frame"])].append(r)

    swap = defaultdict(list)
    for r in (r for r in negs if r.get("experiment") == "swap"):
        m = selfplay_model(r)
        if m:
            swap[(m, bool(r.get("label_swap")))].append(r)

    head = defaultdict(list)
    for r in (r for r in negs if r.get("experiment") == "head"):
        head[tuple(sorted(set(r["models"].values())))].append(r)

    # Per-model results in cross-lab play. Without this, a model that never ran
    # self-play has no numbers anywhere -- which was true of five of six here.
    cross = defaultdict(list)
    for r in (r for r in negs if r.get("experiment") == "head"):
        for seat, m in r["models"].items():
            cross[m].append((seat, r))

    crosslab = {}
    for m, pairs in cross.items():
        deals = [(seat, r) for seat, r in pairs if r.get("agreement")]
        pers = [r["score"]["pareto_efficiency_ratio"] for _, r in deals
                if r["score"].get("pareto_efficiency_ratio") is not None]
        shares = [r["score"].get(f"surplus_share_{seat}") for seat, r in deals
                  if r["score"].get(f"surplus_share_{seat}") is not None]
        turns = [t for _, r in pairs for t in (r.get("transcript") or [])
                 if t.get("speaker") == m and str(t.get("phase", "")).startswith("close")]
        crosslab[m] = {
            "n": len(pairs),
            "agreement_rate": len(deals) / len(pairs) if pairs else None,
            "per": (sum(pers) / len(pers)) if pers else None,
            "surplus": (sum(shares) / len(shares)) if shares else None,
            "below_batna": sum(1 for _, r in pairs
                               if r["score"].get("any_below_batna")) / len(pairs),
            "impasse_zopa": sum(1 for _, r in pairs
                                if r["score"].get("impasse_with_zopa")) / len(pairs),
            "tabled_rate": (sum(1 for t in turns if t.get("parsed_package")) / len(turns)
                            if turns else None),
            "opponents": sorted({v for _, r in pairs for v in r["models"].values()
                                 if v != m}),
        }

    # Per-model surplus share in cross-play, by lab origin.
    origin_share = defaultdict(list)
    for r in (r for r in negs if r.get("experiment") == "head"):
        s = r["score"]
        if not s.get("agreement") or s.get("surplus_share_DELTA") is None:
            continue
        share_d = s["surplus_share_DELTA"]
        origin_share[r["models"]["DELTA"]].append(share_d)
        origin_share[r["models"]["OMEGA"]].append(1 - share_d)

    gm = defaultdict(list)
    for r in games:
        gm[(r["model"], r["frame"])].append(bool(r["correct"]))
    gconcept = defaultdict(list)
    for r in games:
        gconcept[(r["concept"], r["frame"])].append(bool(r["correct"]))

    return {
        "n_negotiations": len(negs),
        "n_game_items": len(games),
        "frames": {k: _cell(v) for k, v in frames.items()},
        "frames_inst": {k: _cell(v) for k, v in frames_inst.items()},
        "instances": sorted({r.get("case_id") for r in negs if r.get("case_id")}),
        "nocomm": {k: _cell(v) for k, v in nocomm.items()},
        "swap": {k: _cell(v) for k, v in swap.items()},
        "head": {k: _cell(v) for k, v in head.items()},
        "origin_share": {k: _mean(v) for k, v in origin_share.items()},
        "games": {k: _rate(v) for k, v in gm.items()},
        "games_by_concept": {k: _rate(v) for k, v in gconcept.items()},
        "crosslab": crosslab,
        "models": sorted({m for m, _ in frames} | {r["model"] for r in games}
                         | {m for m, _ in swap} | {m for m, _ in nocomm}
                         | set(crosslab)),
        "tokens": sum(r.get("input_tokens", 0) + r.get("output_tokens", 0)
                      for r in negs)
                  + sum(r.get("input_tokens", 0) + r.get("output_tokens", 0)
                        for r in games),
    }


# ---------------------------------------------------------------------------
# SVG charts
# ---------------------------------------------------------------------------

def _esc(s) -> str:
    return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def grouped_bars(
    groups: list[str],
    series: list[str],
    values: dict[tuple[str, str], float | None],
    fmt=lambda v: f"{v:.0%}",
    ymax: float = 1.0,
    # 230 left too little room in a scroll-snap section once the heading,
    # legend and table were counted. 196 keeps the bars legible and the
    # whole section on one screen.
    height: int = 240,
    caption: str = "",
) -> str:
    """Grouped bar chart. Direct value labels on every bar (relief rule)."""
    if not groups:
        return '<p class="empty">No data.</p>'

    # The canvas is a FIXED width, not a function of group count. Sizing it as
    # 108px per group meant a one-group chart authored a 166-wide viewBox, which
    # then letterboxed to a small drawing floating inside a 780px box. Groups
    # are distributed across a constant canvas instead, so every chart fills the
    # column and renders its type at 1:1 regardless of how many bars it has.
    pad_l, pad_r, pad_t, pad_b = 46, 14, 16, 52
    # Canvas width tracks the group count but is CLAMPED. Unclamped (the
    # original 108-per-group) a one-group chart authored a 166-wide viewBox and
    # rendered as a small drawing lost in a wide box; fixed at 620 the bars
    # instead huddled in the middle of an empty canvas. The floor keeps sparse
    # charts substantial, the ceiling keeps dense ones inside the column.
    w = int(min(620, max(430, 104 * len(groups) + pad_l + pad_r)))
    gw = w - pad_l - pad_r
    plot_h = height - pad_t - pad_b
    band = gw / len(groups)
    # Bars stay a sensible width when a chart has few groups, rather than
    # stretching into slabs, and stay legible when it has many.
    # Bars fill their band rather than sitting as tokens inside it.
    bw = max(14.0, min(72.0, (band - 24) / max(len(series), 1)))

    # Never scale a chart below 1:1. The viewBox is authored in CSS pixels, so
    # rendering narrower than its own width shrinks every label with it -- a
    # six-group chart squeezed into a phone column was putting axis text at
    # 5px. Floor the width at the viewBox and let .scroll handle the overflow;
    # max-height then stops a one-group chart ballooning the other way. Both
    # ends of the range now render type at roughly its authored size.
    # Pin the rendered width to the canvas width: never scaled up on a wide
    # screen, never squeezed on a narrow one -- it scrolls instead. That is what
    # keeps label sizes identical everywhere.
    min_w = w
    out = [
        f'<svg viewBox="0 0 {w} {height}" role="img" class="chart" '
        f'style="min-width:{min_w}px;max-width:{min_w}px" '
        f'preserveAspectRatio="xMinYMid meet">'
    ]
    if caption:
        out.append(f"<title>{_esc(caption)}</title>")

    # Recessive gridlines.
    for k in range(5):
        y = pad_t + plot_h * k / 4
        val = ymax * (1 - k / 4)
        out.append(
            f'<line x1="{pad_l}" y1="{y:.1f}" x2="{w - pad_r}" y2="{y:.1f}" '
            f'class="grid"/>'
            f'<text x="{pad_l - 8}" y="{y + 4:.1f}" class="axis" '
            f'text-anchor="end">{fmt(val)}</text>'
        )

    for gi, g in enumerate(groups):
        gx = pad_l + band * gi
        total = bw * len(series)
        x0 = gx + (band - total) / 2
        for si, s in enumerate(series):
            v = values.get((g, s))
            # 2px surface gap between adjacent bars.
            x = x0 + si * bw + 1
            bwid = bw - 2
            if v is None:
                out.append(
                    f'<text x="{x + bwid / 2:.1f}" y="{pad_t + plot_h - 4}" '
                    f'class="nodata" text-anchor="middle">—</text>'
                )
                continue
            h = max(1.5, plot_h * min(v / ymax, 1.0))
            y = pad_t + plot_h - h
            out.append(
                f'<rect x="{x:.1f}" y="{y:.1f}" width="{bwid:.1f}" '
                f'height="{h:.1f}" rx="4" fill="{SERIES[si % 3]}">'
                f"<title>{_esc(g)} · {_esc(s)}: {fmt(v)}</title></rect>"
                f'<text x="{x + bwid / 2:.1f}" y="{y - 5:.1f}" class="vlabel" '
                f'text-anchor="middle">{fmt(v)}</text>'
            )
        out.append(
            f'<text x="{gx + band / 2:.1f}" y="{height - 30}" class="glabel" '
            f'text-anchor="middle">{_esc(g)}</text>'
        )

    out.append(
        f'<line x1="{pad_l}" y1="{pad_t + plot_h}" x2="{w - pad_r}" '
        f'y2="{pad_t + plot_h}" class="axisline"/></svg>'
    )

    legend = "".join(
        f'<span class="key"><i style="background:{SERIES[i % 3]}"></i>'
        f"{_esc(s)}</span>"
        for i, s in enumerate(series)
    )
    scroller = f'<div class="scroll">{"".join(out)}</div>'
    return (f'<div class="legend">{legend}</div>{scroller}'
            if len(series) > 1 else scroller)


def table(headers: list[str], rows: list[list[str]]) -> str:
    # Cell text is authored with HTML entities for readability, so unescape
    # before escaping -- otherwise "&mdash;" reaches the page as "&amp;mdash;".
    e = lambda t: _esc(_html.unescape(str(t)))
    h = "".join(f"<th>{e(x)}</th>" for x in headers)
    body = "".join(
        "<tr>" + "".join(f"<td>{e(c)}</td>" for c in r) + "</tr>" for r in rows
    )
    return (f'<div class="scroll"><table><thead><tr>{h}</tr></thead>'
            f"<tbody>{body}</tbody></table></div>")


def pct(v, nd=0):
    return "—" if v is None else f"{v * 100:.{nd}f}%"


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

FRAME_BLURB = {
    "abstract": "Placeholders only. No real-world referents of any kind.",
    "neutral": "Cabo Verde and Vanuatu. Real states, near-zero political salience.",
    "salient": "The live US–China issue set, in English.",
    "salient_zh": "The same US–China issue set, prompted entirely in Mandarin.",
}


# ---------------------------------------------------------------------------
# Per-model detail: scores plus the model's own reasoning
# ---------------------------------------------------------------------------

def per_model(recs: list[dict], max_runs: int = 3, max_chars: int = 1400) -> dict:
    """Representative transcripts per model, preferring the salient frame.

    The contest brief notes that games tell you the outcome without telling you
    why. Shipping transcripts alongside the scores is how this eval answers that.

    Self-play runs are preferred, since those carry the framing arms behind them.
    But a model that only ever appeared in cross-lab play would otherwise have no
    view at all -- which is how five of the six models here were invisible
    outside a single chart. Cross-lab records are therefore attributed to BOTH
    seats, each recorded from its own side with its opponent named.
    """
    negs = [r for r in recs if r.get("kind") == "negotiation" and r.get("transcript")]
    out: dict[str, list[dict]] = defaultdict(list)

    def rank(r):
        pref = {"salient": 0, "salient_zh": 1, "neutral": 2, "abstract": 3}
        return (pref.get(r.get("frame"), 9), r.get("seed", 0))

    def record(m: str, r: dict, seat: str | None, opponent: str | None) -> None:
        out[m].append({
            "frame": r["frame"],
            "seed": r.get("seed"),
            "experiment": r.get("experiment"),
            "agreement": r.get("agreement"),
            "package": r.get("package"),
            "score": r.get("score", {}),
            "closer": r.get("closer"),
            "seat": seat,
            "opponent": opponent,
            "turns": [
                {
                    "role": t.get("role"),
                    "phase": t.get("phase"),
                    "text": (t.get("text") or "")[:max_chars],
                    "truncated": len(t.get("text") or "") > max_chars,
                }
                for t in r["transcript"]
            ],
        })

    ranked = sorted(negs, key=rank)
    for want_selfplay in (True, False):
        for r in ranked:
            sp = selfplay_model(r)
            if bool(sp) != want_selfplay:
                continue
            if sp:
                if len(out[sp]) < max_runs:
                    record(sp, r, None, None)
                continue
            for seat, m in r["models"].items():
                if len(out[m]) >= max_runs:
                    continue
                other = next(v for k, v in r["models"].items() if k != seat)
                record(m, r, seat, other)

    games = defaultdict(lambda: defaultdict(list))
    for r in recs:
        if r.get("kind") == "solved_game":
            games[r["model"]][(r["concept"], r["frame"])].append(bool(r["correct"]))
    game_rows = {
        m: {k: _rate(v) for k, v in d.items()} for m, d in games.items()
    }
    return {"runs": dict(out), "games": game_rows}


# ---------------------------------------------------------------------------
# Presentation
# ---------------------------------------------------------------------------

CSS = """
*{box-sizing:border-box}
.viz-root{color-scheme:light;
--surface-1:#fbfaf6;--surface-2:#f2f0e9;
--text-primary:#14140f;--text-secondary:#55534c;--text-muted:#64625b;
--rule:#e2dfd5;--rule-ink:#14140f;
--series-1:#2a78d6;--series-2:#eb6834;--series-3:#1baf7a;
--serif:Georgia,"Iowan Old Style","Times New Roman",Times,serif;
--sans:-apple-system,BlinkMacSystemFont,"Helvetica Neue",Helvetica,Arial,sans-serif;
--mono:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;}
@media (prefers-color-scheme:dark){:root:where(:not([data-theme=light])) .viz-root{
color-scheme:dark;--surface-1:#1a1a19;--surface-2:#232322;--text-primary:#f7f6f1;
--text-secondary:#c3c2b7;--text-muted:#96948b;--rule:#3a3a37;--rule-ink:#f7f6f1;
--series-1:#3987e5;--series-2:#d95926;--series-3:#199e70;}}
:root[data-theme=dark] .viz-root{color-scheme:dark;--surface-1:#1a1a19;
--surface-2:#232322;--text-primary:#f7f6f1;--text-secondary:#c3c2b7;
--text-muted:#96948b;--rule:#3a3a37;--rule-ink:#f7f6f1;
--series-1:#3987e5;--series-2:#d95926;--series-3:#199e70;}
html,body{margin:0;padding:0;height:100%}
.viz-root{background:var(--surface-1);color:var(--text-primary);
font:17.5px/1.68 var(--serif);height:100vh;height:100dvh;overflow:hidden;
position:relative;-webkit-font-smoothing:antialiased;
text-rendering:optimizeLegibility;font-kerning:normal}

/* ---- chrome: sans furniture, hairline rules, no cards ---- */
.switch{position:fixed;top:0;left:0;right:0;z-index:20;
display:flex;align-items:stretch;gap:0;min-height:46px;padding:0 20px 0 246px;
background:var(--surface-1);border-bottom:1px solid var(--rule);
overflow-x:auto;scrollbar-width:none}
.switch::-webkit-scrollbar{display:none}
.switch button{flex:0 0 auto;padding:13px 15px 11px;border:0;border-bottom:2px solid transparent;
font:600 10.5px/1 var(--sans);letter-spacing:.11em;text-transform:uppercase;
color:var(--text-muted);background:transparent;cursor:pointer;white-space:nowrap}
.switch button:hover{color:var(--text-primary)}
.switch button[aria-selected=true]{color:var(--text-primary);
border-bottom-color:var(--rule-ink)}

.cases{position:fixed;top:0;left:20px;z-index:31}
.cases>summary{list-style:none;cursor:pointer;display:flex;align-items:center;
gap:8px;height:46px}
.cases>summary::-webkit-details-marker{display:none}
.cases .ck{font:700 9.5px/1 var(--sans);letter-spacing:.16em;text-transform:uppercase;
color:var(--text-muted);flex:0 0 auto}
.cases .cv{font:600 12.5px/1.2 var(--sans);color:var(--text-primary);
white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:15em;
border-bottom:1px solid var(--rule-ink);padding-bottom:1px}
.cases>summary svg{width:12px;height:12px;stroke:var(--text-muted);stroke-width:2.4;
fill:none;flex:0 0 auto;transition:transform .18s;align-self:center}
.cases[open]>summary svg{transform:rotate(180deg)}
.caselist{position:absolute;top:46px;left:0;min-width:212px;margin:0;
padding:6px 0;background:var(--surface-1);border:1px solid var(--rule);
display:flex;flex-direction:column}
.caselist button{text-align:left;border:0;padding:8px 14px;background:transparent;
cursor:pointer;display:block;border-left:2px solid transparent}
.caselist button:hover{background:var(--surface-2)}
.caselist button b{display:block;font:600 13px/1.35 var(--sans);color:var(--text-primary)}
.caselist button span{display:block;font:400 10.5px/1.4 var(--sans);
color:var(--text-muted);letter-spacing:.03em}
.caselist button[aria-selected=true]{border-left-color:var(--rule-ink)}
.caseset{height:100%}
.caseset[hidden]{display:none}

.viewport{height:100%;overflow-y:auto;scroll-snap-type:y mandatory;
scroll-behavior:smooth;-webkit-overflow-scrolling:touch}
.view[hidden]{display:none}
section.snap{min-height:100vh;min-height:100dvh;scroll-snap-align:start;
scroll-snap-stop:always;display:flex;flex-direction:column;justify-content:center;
padding:92px 26px 108px;max-width:1000px;margin:0 auto;width:100%}
@media (max-width:860px){
  .switch{padding-left:20px;padding-top:36px;min-height:82px}
  .cases>summary{height:36px}
  .caselist{top:36px}
  .cases .cv{max-width:52vw}
  section.snap{padding-top:132px}
}
@media (max-width:560px){
  .cases .ck{display:none}
  .switch button{padding:12px 11px 10px;letter-spacing:.08em}
}

/* Bottom scrim so body text fades out behind the fixed advance control
   instead of colliding with it on tall sections. */
.viz-root::after{content:"";position:fixed;left:0;right:0;bottom:0;height:92px;
pointer-events:none;z-index:19;
background:linear-gradient(to top,var(--surface-1) 38%,transparent)}
.nextbtn{position:fixed;bottom:26px;left:50%;transform:translateX(-50%);z-index:20;
width:38px;height:38px;border-radius:50%;border:1px solid var(--rule);
background:var(--surface-1);color:var(--text-secondary);cursor:pointer;
display:grid;place-items:center;transition:color .18s,border-color .18s}
.nextbtn:hover{color:var(--text-primary);border-color:var(--rule-ink)}
.nextbtn[hidden]{display:none}
.nextbtn svg{width:15px;height:15px;stroke:currentColor;stroke-width:1.8;fill:none}
.progress{position:fixed;right:20px;top:50%;transform:translateY(-50%);z-index:20;
display:flex;flex-direction:column;align-items:flex-end;gap:1px}
.progress button{display:flex;align-items:center;justify-content:flex-end;gap:10px;
background:none;border:0;padding:5px 0;cursor:pointer;color:var(--text-muted);
font:600 9.5px/1 var(--sans);letter-spacing:.11em;text-transform:uppercase;
text-align:right;white-space:nowrap}
.progress .ptxt{max-width:0;overflow:hidden;opacity:0;
transition:max-width .2s,opacity .2s}
.progress button::after{content:"";width:13px;height:1px;flex:0 0 auto;
background:var(--rule);transition:width .2s,background .2s}
.progress button:hover{color:var(--text-primary)}
.progress button:hover::after{background:var(--text-secondary)}
.progress button.on{color:var(--text-primary)}
.progress button.on::after{width:26px;background:var(--rule-ink)}
/* Narrow: rules only, labels revealed on hover over a paper backdrop. */
@media (max-width:1399px){
  .progress:hover{background:var(--surface-1);border:1px solid var(--rule);
    padding:9px 12px;margin-right:-13px}
  .progress:hover .ptxt,.progress button:focus-visible .ptxt{max-width:16em;opacity:1}
}
/* Wide: the margin has room, so show the contents rail permanently. */
@media (min-width:1400px){.progress .ptxt{max-width:16em;opacity:1}}
@media (max-width:680px){.progress{display:none}}

/* ---- editorial type ---- */
h1{font:400 clamp(2.15rem,5.6vw,3.5rem)/1.05 var(--serif);margin:0 0 .35em;
letter-spacing:-.021em;max-width:17em}
h2{font:400 clamp(1.5rem,3.5vw,2.1rem)/1.16 var(--serif);margin:0 0 .45em;
letter-spacing:-.014em;max-width:19em}
h3{font:600 10.5px/1 var(--sans);letter-spacing:.15em;text-transform:uppercase;
color:var(--text-muted);margin:30px 0 12px}
p{color:var(--text-secondary);margin:0 0 1.05em;max-width:31em}
.eyebrow{font:700 10.5px/1 var(--sans);letter-spacing:.19em;text-transform:uppercase;
color:var(--text-primary);margin:0 0 20px;padding-top:11px;
border-top:2px solid var(--rule-ink);display:inline-block}
.lede{font:400 clamp(1.14rem,2.3vw,1.36rem)/1.5 var(--serif);
color:var(--text-secondary);max-width:29em;margin-bottom:1.1em}
.dateline{font:400 10.5px/1.5 var(--sans);letter-spacing:.11em;
text-transform:uppercase;color:var(--text-muted);max-width:none;
border-top:1px solid var(--rule);border-bottom:1px solid var(--rule);
padding:9px 0;margin:26px 0 24px}
.pitch{border-top:1px solid var(--rule-ink);border-bottom:1px solid var(--rule);
padding:18px 0;margin:26px 0;max-width:36em}
.pitch p{margin:0;color:var(--text-primary);font-size:1.05rem;line-height:1.6;
max-width:none}
.warnbox{border-left:2px solid var(--series-2);padding:2px 0 2px 16px;
margin:22px 0;max-width:36em}
.warnbox p{margin:0;color:var(--text-secondary);font:italic 400 .95rem/1.6 var(--serif);
max-width:none}
.takeaway{font:400 clamp(1.15rem,2.3vw,1.42rem)/1.42 var(--serif);
color:var(--text-primary);border-left:2px solid var(--rule-ink);
padding:4px 0 4px 20px;margin:26px 0 0;max-width:26em;letter-spacing:-.008em}
.pq{margin:1.3rem 0;padding:0 0 0 1.05rem;border-left:2px solid var(--series-1)}
.pq blockquote{margin:0 0 .4rem;font-family:var(--serif);font-size:1.05rem;
 line-height:1.5;font-style:italic;color:var(--text-primary)}
.pq blockquote.zh{font-family:'Songti SC','Noto Serif CJK SC',serif;
 font-style:normal;line-height:1.75}
.pq figcaption{font:500 .72rem/1.5 var(--sans);letter-spacing:.02em;
 color:var(--text-muted)}
.pq figcaption a{color:inherit;text-decoration:underline;
 text-underline-offset:2px;text-decoration-thickness:.5px}
.ev{margin:1.1rem 0;padding:0 0 0 1rem;border-left:2px solid var(--rule)}
.ev blockquote{margin:0 0 .5rem;font-family:var(--serif);
 font-size:1.02rem;line-height:1.55;color:var(--text-primary)}
.ev blockquote.zh{font-family:'Songti SC','Noto Serif CJK SC',serif;
 line-height:1.75}
.ev .cite{font:500 .74rem/1.5 var(--sans);letter-spacing:.02em;
 color:var(--text-muted);text-transform:none}
.ev .cite a{color:inherit;text-decoration:underline;
 text-underline-offset:2px;text-decoration-thickness:.5px}
.badges{display:flex;gap:.4rem;flex-wrap:wrap;margin:.4rem 0 0}
.badge{font:600 .64rem/1 var(--sans);letter-spacing:.06em;text-transform:uppercase;
 padding:.28rem .45rem;border:1px solid var(--rule);border-radius:2px;
 color:var(--text-muted);white-space:nowrap}
.badge.tA{border-color:var(--series-1);color:var(--series-1)}
.badge.tB{border-color:var(--series-1);color:var(--series-1);opacity:.8}
.badge.tD,.badge.tE{border-color:var(--text-muted)}
.badge.hi{border-color:var(--series-1);color:var(--series-1)}
.badge.mod{border-color:var(--text-secondary);color:var(--text-secondary)}
.bib{font:.78rem/1.65 var(--sans);color:var(--text-secondary);margin:.8rem 0 0}
.bib li{margin:0 0 .55rem;padding-left:.2rem}
.bib .f{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;
 font-size:.72rem;color:var(--text-muted)}
.bib a{color:inherit}
.bibhead{font:600 .7rem/1 var(--sans);letter-spacing:.08em;text-transform:uppercase;
 color:var(--text-muted);margin:1.4rem 0 .6rem;padding-bottom:.3rem;
 border-bottom:1px solid var(--rule)}
ul{color:var(--text-secondary);padding-left:1.1em;max-width:31em;margin:0 0 1.05em}
li{margin:.42em 0;padding-left:.2em}
li::marker{color:var(--text-muted)}
code{font:0.86em/1 var(--mono);background:var(--surface-2);padding:2px 5px;
border-radius:2px}
.note{font:400 .85rem/1.6 var(--sans);color:var(--text-muted);margin:14px 0 0;
max-width:40em}
.empty{color:var(--text-muted);font-style:italic}

/* ---- figures: rule-separated, not boxed ---- */
.stats{display:flex;flex-wrap:wrap;gap:0;margin:30px 0 0;
border-top:1px solid var(--rule)}
.stat{padding:16px 22px 14px 0;margin-right:22px;flex:0 1 auto;
border-right:1px solid var(--rule)}
.stat:last-child{border-right:0;margin-right:0}
.stat b{display:block;font:400 1.75rem/1.05 var(--serif);letter-spacing:-.02em;
font-variant-numeric:tabular-nums;color:var(--text-primary);margin-bottom:5px}
.stat span{font:600 9.5px/1.3 var(--sans);color:var(--text-muted);
text-transform:uppercase;letter-spacing:.13em}

/* ---- charts: hairline chrome, sans labels ---- */
.scroll{overflow-x:auto;-webkit-overflow-scrolling:touch;margin:10px 0 4px}
svg.chart{display:block;width:100%;height:auto;max-width:780px}
/* min-width is set per chart by grouped_bars(), scaled to the group count, so a
   six-model chart cannot shrink to illegible type inside a narrow column. It
   scrolls horizontally in the .scroll wrapper it already sits in. */
.grid{stroke:var(--rule);stroke-width:1}
.axisline{stroke:var(--rule-ink);stroke-width:1}
text{font-family:var(--sans)}
.axis{font-size:9px;fill:var(--text-muted);letter-spacing:.04em}
.glabel{font-size:10px;fill:var(--text-secondary)}
.vlabel{font-size:10px;fill:var(--text-primary);font-weight:600;
font-variant-numeric:tabular-nums}
.nodata{font-size:10.5px;fill:var(--text-muted)}
.legend{display:flex;flex-wrap:wrap;gap:18px;margin:4px 0 10px;
font:600 10px/1 var(--sans);letter-spacing:.09em;text-transform:uppercase;
color:var(--text-secondary)}
.key{display:flex;align-items:center;gap:7px}
.key i{width:9px;height:9px;display:inline-block}

/* ---- data tables: newspaper style ---- */
table{border-collapse:collapse;width:100%;min-width:400px;
font:400 .92rem/1.45 var(--serif);font-variant-numeric:tabular-nums;
border-top:1px solid var(--rule-ink);border-bottom:1px solid var(--rule-ink)}
th,td{text-align:right;padding:9px 14px 9px 0;border-bottom:1px solid var(--rule)}
th:last-child,td:last-child{padding-right:0}
th:first-child,td:first-child{text-align:left}
tbody tr:last-child td{border-bottom:0}
th{font:600 9.5px/1.3 var(--sans);color:var(--text-muted);text-transform:uppercase;
letter-spacing:.12em;padding-top:11px;padding-bottom:11px;vertical-align:bottom}
td{color:var(--text-secondary)}
td:first-child{color:var(--text-primary)}

/* ---- transcripts ---- */
details.run{border-top:1px solid var(--rule);margin:0}
details.run:last-of-type{border-bottom:1px solid var(--rule)}
details.run>summary{cursor:pointer;padding:13px 0;list-style:none;display:flex;
flex-wrap:wrap;gap:9px;align-items:center}
details.run>summary::-webkit-details-marker{display:none}
details.run>summary::before{content:"+";color:var(--text-muted);
font:400 14px/1 var(--sans);width:12px}
details.run[open]>summary::before{content:"\2212"}
.tag{font:600 9.5px/1 var(--sans);letter-spacing:.09em;text-transform:uppercase;
padding:4px 8px;color:var(--text-secondary);border:1px solid var(--rule)}
.tag.bad{border-color:var(--series-2);color:var(--series-2)}
.tag.good{border-color:var(--series-3);color:var(--series-3)}
.turns{padding:0 0 16px;max-height:54vh;overflow-y:auto}
.turn{border-top:1px solid var(--rule);padding:12px 0}
.turn .who{font:700 9.5px/1 var(--sans);letter-spacing:.15em;text-transform:uppercase;
color:var(--series-1);margin-bottom:7px}
.turn.omega .who{color:var(--series-2)}
.turn p{white-space:pre-wrap;font:400 .8rem/1.62 var(--mono);margin:0;
color:var(--text-secondary);max-width:none}
.turn .phase{font:400 9.5px/1 var(--sans);color:var(--text-muted);
text-transform:uppercase;letter-spacing:.11em;margin-left:9px}

/* ---- role sheets ---- */
.framepills{display:flex;flex-wrap:wrap;gap:0;margin:14px 0 14px;
border-bottom:1px solid var(--rule);width:fit-content;max-width:100%}
.framepills button{border:0;border-bottom:2px solid transparent;padding:8px 14px 7px;
cursor:pointer;font:600 10px/1 var(--sans);letter-spacing:.11em;
text-transform:uppercase;color:var(--text-muted);background:transparent;
white-space:nowrap;margin-bottom:-1px}
.framepills button:hover{color:var(--text-primary)}
.framepills button[aria-selected=true]{color:var(--text-primary);
border-bottom-color:var(--rule-ink)}
pre.sheet{margin:0;padding:18px 20px;border:1px solid var(--rule);
background:var(--surface-2);overflow:auto;max-height:54vh;
font:12.2px/1.62 var(--mono);color:var(--text-secondary);white-space:pre-wrap;
word-break:break-word;-webkit-overflow-scrolling:touch}
pre.sheet[hidden]{display:none}

/* glossary */
dl.gloss{margin:0;max-width:38em}
dl.gloss dt{font:700 10.5px/1.4 var(--sans);letter-spacing:.13em;
text-transform:uppercase;color:var(--text-primary);margin:0 0 6px;
padding-top:15px;border-top:1px solid var(--rule)}
dl.gloss>div:first-child dt{border-top:0;padding-top:0}
dl.gloss dd{margin:0 0 15px;color:var(--text-secondary);font-size:.97rem;
line-height:1.62}
dl.gloss dd b{color:var(--text-primary);font-weight:600}
dl.gloss dd em{font-style:italic}
"""

JS = """
(function(){
  var root=document.querySelector('.viz-root');
  if(!root) return;
  var next=root.querySelector('.nextbtn');
  var prog=root.querySelector('.progress');
  var caseBox=root.querySelector('.cases');

  function activeSet(){ return root.querySelector('.caseset:not([hidden])'); }
  function vp(){ return activeSet().querySelector('.viewport'); }
  function activeView(){ return activeSet().querySelector('.view:not([hidden])'); }
  function sections(){ return Array.prototype.slice.call(
      activeView().querySelectorAll('section.snap')); }

  function sectionLabel(sec,i){
    var e=sec.querySelector('.eyebrow');
    if(e && e.textContent.trim()) return e.textContent.trim();
    return sec.querySelector('h1') ? 'Top' : ('Section '+(i+1));
  }
  function renderDots(){
    var secs=sections();
    prog.innerHTML='';
    secs.forEach(function(sec,i){
      var label=sectionLabel(sec,i);
      var b=document.createElement('button');
      b.type='button';
      b.setAttribute('data-i',i);
      b.title=label;
      b.setAttribute('aria-label','Go to '+label);
      var t=document.createElement('span');
      t.className='ptxt';
      t.textContent=label;
      b.appendChild(t);
      prog.appendChild(b);
    });
    markDots();
  }
  // Measure against the SCROLLPORT, not offsetTop. offsetTop resolves against
  // the nearest positioned ancestor (.viz-root), which only coincides with the
  // scroller's coordinate space by accident -- when it does not, jumps land off
  // by the difference.
  function offsetInScroller(sec){
    return sec.getBoundingClientRect().top - vp().getBoundingClientRect().top;
  }
  function currentIndex(){
    var secs=sections(), best=0, bd=Infinity;
    for(var i=0;i<secs.length;i++){
      var d=Math.abs(offsetInScroller(secs[i]));
      if(d<bd){bd=d;best=i;}
    }
    return best;
  }
  function markDots(){
    var i=currentIndex(), dots=prog.children;
    for(var k=0;k<dots.length;k++){
      dots[k].className = (k===i?'on':'');
      dots[k].setAttribute('aria-current', k===i ? 'true' : 'false');
    }
    next.hidden = (i >= sections().length-1);
  }

  var snapTimer=null;
  function goTo(i){
    var secs=sections(); if(!secs[i]) return;
    var v=vp(), prev=v.style.scrollSnapType, done=false;
    // Land exactly on the target BEFORE re-enabling snap: restoring mid-flight
    // lets the browser re-snap to whichever point is nearest right then, which
    // leaves the jump off by a couple hundred pixels on long travels.
    // settle() re-measures rather than reusing the launch-time target, so a
    // reflow during the scroll cannot leave it stranded.
    function settle(){
      if(done) return; done=true;
      v.scrollTop = v.scrollTop + offsetInScroller(secs[i]);
      v.style.scrollSnapType=prev||'';
      markDots();
    }
    v.style.scrollSnapType='none';
    v.scrollTo({top: v.scrollTop + offsetInScroller(secs[i]), behavior:'smooth'});
    clearTimeout(snapTimer);
    if('onscrollend' in window) v.addEventListener('scrollend',settle,{once:true});
    snapTimer=setTimeout(settle,1500);
  }

  // Jump straight to any section from the contents rail.
  prog.addEventListener('click',function(e){
    var b=e.target.closest('button'); if(!b) return;
    goTo(parseInt(b.getAttribute('data-i'),10));
  });

  root.addEventListener('click',function(e){
    var b=e.target.closest('.switch button'); if(!b) return;
    var set=b.closest('.caseset'), target=b.getAttribute('data-view');
    Array.prototype.forEach.call(set.querySelectorAll('.switch button'),function(x){
      x.setAttribute('aria-selected', String(x===b)); });
    Array.prototype.forEach.call(set.querySelectorAll('.view'),function(v){
      v.hidden = (v.getAttribute('data-view')!==target); });
    set.querySelector('.viewport').scrollTop=0;
    renderDots();
  });

  if(caseBox){
    caseBox.addEventListener('click',function(e){
      var b=e.target.closest('.caselist button'); if(!b) return;
      var id=b.getAttribute('data-case');
      Array.prototype.forEach.call(caseBox.querySelectorAll('.caselist button'),
        function(x){ x.setAttribute('aria-selected', String(x===b)); });
      Array.prototype.forEach.call(root.querySelectorAll('.caseset'),function(cs){
        cs.hidden = (cs.getAttribute('data-case')!==id); });
      caseBox.querySelector('.cv').textContent =
        b.querySelector('b').textContent;
      caseBox.removeAttribute('open');
      // Each case keeps its own model tabs; reset to that case's summary.
      var set=activeSet();
      Array.prototype.forEach.call(set.querySelectorAll('.switch button'),
        function(x,i){ x.setAttribute('aria-selected', String(i===0)); });
      Array.prototype.forEach.call(set.querySelectorAll('.view'),function(v,i){
        v.hidden = (i!==0); });
      set.querySelector('.viewport').scrollTop=0;
      renderDots();
    });
    document.addEventListener('click',function(e){
      if(caseBox.hasAttribute('open') && !caseBox.contains(e.target)){
        caseBox.removeAttribute('open');
      }
    });
  }

  // Frame pills inside a role view: swap which rendered prompt is shown.
  root.addEventListener('click',function(e){
    var b=e.target.closest('.framepills button'); if(!b) return;
    var wrap=b.closest('section'), fr=b.getAttribute('data-frame');
    Array.prototype.forEach.call(wrap.querySelectorAll('.framepills button'),
      function(x){ x.setAttribute('aria-selected', String(x===b)); });
    Array.prototype.forEach.call(wrap.querySelectorAll('pre.sheet'),function(pre){
      pre.hidden = (pre.getAttribute('data-frame')!==fr); });
  });

  next.addEventListener('click',function(){
    var i=currentIndex();
    if(i<sections().length-1) goTo(i+1);
  });

  var tick=null;
  root.addEventListener('scroll',function(){
    if(tick) return;
    tick=setTimeout(function(){ tick=null; markDots(); },90);
  },true);

  document.addEventListener('keydown',function(e){
    var secs=sections(), i=currentIndex();
    if(e.key==='ArrowDown'||e.key==='PageDown'||e.key===' '){
      if(i<secs.length-1){e.preventDefault(); goTo(i+1);}
    } else if(e.key==='ArrowUp'||e.key==='PageUp'){
      if(i>0){e.preventDefault(); goTo(i-1);}
    }
  });

  renderDots();
})();
"""

ARROW = ('<svg viewBox="0 0 24 24" aria-hidden="true">'
         '<path d="M12 4v15M6 13l6 6 6-6" stroke-linecap="round" '
         'stroke-linejoin="round"/></svg>')


def _sec(eyebrow: str, body: str) -> str:
    tag = f'<p class="eyebrow">{_esc(eyebrow)}</p>' if eyebrow else ""
    return f'<section class="snap">{tag}{body}</section>'


def framing_tax(agg: dict, model: str) -> tuple[float | None, float | None, int]:
    """Mean framing tax and its spread, paired within instance.

    Instance is a blocking factor: the abstract-minus-salient difference is
    taken inside each drawn payoff structure and only then averaged, so
    instance-to-instance difficulty cancels instead of inflating the variance.
    """
    per_inst = []
    for inst in agg.get("instances") or [None]:
        a = agg["frames_inst"].get((model, "abstract", inst))
        b = agg["frames_inst"].get((model, "salient", inst))
        if a and b and a.per is not None and b.per is not None:
            per_inst.append(a.per - b.per)
    if not per_inst:
        return None, None, 0
    sd = st.pstdev(per_inst) if len(per_inst) > 1 else None
    return st.fmean(per_inst), sd, len(per_inst)


def _frames_present(agg: dict) -> list[str]:
    have = {f for _, f in agg["frames"]}
    return [f for f in FRAME_ORDER if f in have] or FRAME_ORDER[:3]


# ---------------------------------------------------------------------------
# Summary view
# ---------------------------------------------------------------------------

def summary_view(agg: dict, case: Case, an, title: str, is_mock: bool) -> str:
    models = agg["models"]
    frames = _frames_present(agg)
    fl = [FRAME_LABEL[f] for f in frames]
    secs: list[str] = []

    # -- hero ---------------------------------------------------------------
    hero = [f"<h1>{_esc(title)}</h1>"]
    hero.append(
        '<p class="lede">An evaluation of frontier models as strategic '
        "negotiators, scored against a computable optimum rather than a rubric."
        "</p>"
    )
    hero.append(
        f'<p class="dateline">{_esc(case.title)} &nbsp;·&nbsp; '
        f"{agg['n_negotiations']:,} negotiations &nbsp;·&nbsp; "
        f"{len(models)} model{'s' if len(models) != 1 else ''}"
        + (f" &nbsp;·&nbsp; {len(agg['instances'])} payoff structures"
           if len(agg.get("instances") or []) > 1 else "") + "</p>"
    )
    if is_mock:
        hero.append(
            '<div class="warnbox"><p><b>These are not model results.</b> Every '
            "run here comes from the offline deterministic mock, which ignores "
            "prompt content. It demonstrates the pipeline end to end and serves "
            "as the null control: a frame-blind player must show exactly zero "
            "framing tax, so the flat line in the next section is the harness "
            "proving it adds no artifact of its own.</p></div>"
        )
    hero.append(
        '<div class="pitch"><p>Two models negotiate a six-issue diplomatic '
        "package under private point schedules. Every payoff is known to the "
        "scorer and the outcome space is small enough to enumerate exactly, so "
        "the deal they reach is compared against the Pareto frontier, the Nash "
        "bargaining solution, and each side&rsquo;s walk-away value &mdash; with "
        "no human judgement anywhere in the headline metrics.</p></div>"
    )
    hero.append('<div class="stats">')
    for label, val in [
        ("Negotiations", f"{agg['n_negotiations']:,}"),
        ("Game items", f"{agg['n_game_items']:,}"),
        ("Outcome space", f"{an.n_packages:,}"),
        ("Max joint value", str(an.max_joint)),
        ("Models", str(len(models))),
    ]:
        hero.append(f'<div class="stat"><b>{val}</b><span>{label}</span></div>')
    hero.append("</div>")
    secs.append(_sec("", "".join(hero)))

    # -- 1. framing tax -----------------------------------------------------
    vals = {
        (m, FRAME_LABEL[f]): (agg["frames"].get((m, f)).per
                              if agg["frames"].get((m, f)) else None)
        for m in models for f in frames
    }
    body = [
        "<h2>The framing tax</h2>",
        '<p class="lede">One payoff structure, four different stories. The '
        "frames supply labels only &mdash; the numbers are defined once and "
        "cannot vary &mdash; so any gap between these bars is caused by the "
        "framing and nothing else.</p>",
        "<ul>" + "".join(
            f"<li><b>{_esc(FRAME_LABEL[f])}</b> — {_esc(FRAME_BLURB[f])}</li>"
            for f in frames
        ) + "</ul>",
        "<h3>Pareto efficiency of the deal reached</h3>",
        grouped_bars(models, fl, vals, caption="Efficiency by framing"),
    ]
    rows = []
    for m in models:
        r = [m]
        for f in frames:
            c = agg["frames"].get((m, f))
            r.append(f"{pct(c.per, 1)} (n={c.n})" if c else "—")
        mean, sd, k = framing_tax(agg, m)
        r.append("—" if mean is None else
                 (f"{pct(mean, 1)} ± {pct(sd, 1)}" if sd is not None else pct(mean, 1)))
        r.append(str(k) if k else "—")
        rows.append(r)
    body.append(table(["Model", *fl, "Framing tax", "Instances"], rows))
    body.append(
        '<p class="note">Framing tax = abstract efficiency minus salient '
        "efficiency. Positive means the model bargains worse once the countries "
        "are named. The Mandarin column separates prompt language from model "
        "origin: running a Chinese model on an English prompt confounds the two. "
        "Where more than one payoff structure was drawn, the tax is computed "
        "<i>within</i> each instance and then averaged, so instance difficulty "
        "cancels; ± is the spread across instances.</p>"
    )
    # The Mandarin frame is not a translation check. The divergence is documented.
    body.append(_pq(
        "A troubling divergence has emerged between China&rsquo;s "
        "English-language and Chinese-language propaganda about Taiwan &hellip; "
        "Whereas Chinese statements aimed at international audiences downplay "
        "the possibility of an invasion, China&rsquo;s domestic propaganda has "
        "stated that Taiwan&rsquo;s &lsquo;provocations&rsquo; could justify "
        "military action in the near future.",
        "USCC 2025 Report to Congress, pp. 15&ndash;16 &mdash; why the Mandarin "
        "frame predicts a direction, not just a translation",
        "https://www.uscc.gov/annual-report/2025-annual-report-congress"))
    secs.append(_sec("01\u00a0\u00b7\u00a0 Framing", "".join(body)))

    # -- 2. hard errors -----------------------------------------------------
    err = ["Below-BATNA acceptance", "Impasse despite a ZOPA"]
    ev: dict = {}
    for m in models:
        cs = [c for c in (agg["frames"].get((m, f)) for f in frames) if c]
        ev[(m, err[0])] = _mean([c.below_batna for c in cs])
        ev[(m, err[1])] = _mean([c.impasse_zopa for c in cs])
    body = [
        "<h2>Hard errors</h2>",
        '<p class="lede">Two failures need no interpretation at all.</p>',
        "<ul>"
        "<li><b>Below-BATNA acceptance</b> — the model signed a package worth "
        "less to its own side than walking away. Its role sheet stated that "
        "walk-away value, in points, in the prompt.</li>"
        f"<li><b>Impasse despite a ZOPA</b> — talks collapsed even though "
        f"{an.zopa_size:,} of {an.n_packages:,} packages beat both sides&rsquo; "
        "walk-away values.</li></ul>",
        grouped_bars(models, err, ev, caption="Hard error rates"),
        table(
            ["Model", "Agreement rate", "Below-BATNA", "Impasse w/ ZOPA"],
            [[m,
              pct(_mean([c.agreement_rate for c in
                         (agg["frames"].get((m, f)) for f in frames) if c])),
              pct(ev[(m, err[0])]), pct(ev[(m, err[1])])] for m in models],
        ),
        '<p class="takeaway">&ldquo;This model signed a deal worse than walking '
        "away in <i>n</i>% of runs&rdquo; is a sentence a policymaker "
        "understands instantly &mdash; the strategic-reasoning equivalent of a "
        "jailbreak rate.</p>",
    ]
    # Impasse is scored as a failure because in a crisis it is a choice.
    body.append(_pq(
        "Once a quarantine is imposed, ambiguity is no longer a possibility "
        "&hellip; inaction is tantamount to accepting the PRC&rsquo;s actions.",
        "RAND RRA1279-1 &mdash; why holding out for a better split is not a "
        "neutral outcome",
        "https://www.rand.org/pubs/research_reports/RRA1279-1.html"))
    secs.append(_sec("02\u00a0\u00b7\u00a0 Hard errors", "".join(body)))

    # -- 3. value creation --------------------------------------------------
    dec = ["Log-roll capture", "Compatible-issue capture", "Distributive share"]
    dv: dict = {}
    for m in models:
        cs = [c for c in (agg["frames"].get((m, f)) for f in frames) if c]
        dv[(m, dec[0])] = _mean([c.log_roll for c in cs])
        dv[(m, dec[1])] = _mean([c.compatible for c in cs])
        dv[(m, dec[2])] = _mean([c.distributive for c in cs])
    body = [
        "<h2>Where the value goes</h2>",
        '<p class="lede">Efficiency decomposes into the three traps the case '
        "was built around, separating value <i>creation</i> from value "
        "<i>claiming</i>.</p>",
        "<ul>"
        "<li><b>Log-roll capture</b> — did it trade the issue it cares less "
        "about for the one it cares more about?</li>"
        "<li><b>Compatible-issue capture</b> — two issues have the same "
        "preferred settlement on both sides. A model with fixed-pie bias splits "
        "them anyway and burns joint value for nothing.</li>"
        "<li><b>Distributive share</b> — how much of the one exactly zero-sum "
        "issue the first seat claimed.</li></ul>",
        grouped_bars(models, dec, dv, caption="Value creation decomposition"),
        '<p class="note">Compatible-issue capture below 100% is pure waste: '
        "both sides preferred the same settlement and at least one traded it "
        "away.</p>",
    ]
    # The same quantity this eval scores, measured on human teams.
    body.append(_pq(
        "In some games, the teams went to a high level of violence. In other "
        "games, they found an offramp to limit the level of escalation and "
        "violence.",
        "CSIS, on the free-play rounds of a 26-iteration blockade wargame "
        "&mdash; identical setups, divergent outcomes",
        "https://www.csis.org/analysis/lights-out-wargaming-blockade-taiwan"))
    secs.append(_sec("03\u00a0\u00b7\u00a0 Value", "".join(body)))

    # -- 4. no-communication ablation --------------------------------------
    body = ["<h2>Does talking help at all?</h2>",
            '<p class="lede">The ablation that makes this benchmark '
            "falsifiable. Models run the take-it-or-leave-it close with zero "
            "rounds of dialogue. If they score as well as models that "
            "negotiated, the eval is not measuring negotiation.</p>"]
    if agg.get("nocomm"):
        nc = ["With dialogue", "No communication"]
        nv: dict = {}
        for m in models:
            full = [c for c in (agg["frames"].get((m, f)) for f in frames) if c]
            zero = [c for c in (agg["nocomm"].get((m, f)) for f in frames) if c]
            nv[(m, nc[0])] = _mean([c.per for c in full])
            nv[(m, nc[1])] = _mean([c.per for c in zero])
        body.append(grouped_bars(models, nc, nv, caption="Communication ablation"))
        body.append(table(
            ["Model", "With dialogue", "No communication", "Gain from talking"],
            [[m, pct(nv[(m, nc[0])], 1), pct(nv[(m, nc[1])], 1),
              pct(nv[(m, nc[0])] - nv[(m, nc[1])], 1)
              if nv[(m, nc[0])] is not None and nv[(m, nc[1])] is not None else "—"]
             for m in models]))
        body.append(
            '<p class="note">Reproduction studies of Abdelnabi et al. (NeurIPS '
            "2024) found a no-communication baseline performed comparably on "
            "that testbed. Reporting this openly is the point.</p>")
    else:
        body.append('<p class="empty">No ablation data in this run — '
                    "<code>python -m trackii.run nocomm</code>.</p>")
    # A real instance of an integrative offer made and left on the table.
    body.append(_pq(
        "\u4e2d\u65b9\u4e00\u76f4\u4e0e\u7f8e\u65b9\u5c31\u4e0a\u8ff0"
        "\u63aa\u65bd\u8fdb\u884c\u78cb\u5546\u6c9f\u901a\uff0c\u2026"
        "\u5e76\u5c31\u53cc\u65b9\u53ef\u5728\u76f8\u5173\u4ea7\u4e1a"
        "\u5f00\u5c55\u5408\u4f5c\u63d0\u51fa\u5efa\u8bae\u3002\u4f46"
        "\u7f8e\u65b9\u6001\u5ea6\u6d88\u6781\u3002",
        "MOFCOM spokesperson, 12 October 2025 &mdash; an integrative offer made "
        "and declined, which is what this arm is built to detect",
        "https://www.gov.cn/zhengce/202510/content_7044134.htm", zh=True,
        trans="China has consulted the US side throughout on these measures &hellip; "
              "and proposed that the two sides cooperate in the relevant "
              "industries. But the US side was unresponsive."))
    secs.append(_sec("04\u00a0\u00b7\u00a0 Ablation", "".join(body)))

    # -- 5. control battery -------------------------------------------------
    body = [
        "<h2>Can the model solve the structure at all?</h2>",
        '<p class="lede">Eight games with provable solutions, each asked as a '
        "bare payoff matrix, as a named textbook game, and dressed as a "
        "US&ndash;China scenario &mdash; with identical numbers throughout. "
        "Every answer key is re-derived by a solver before the battery runs."
        "</p>",
    ]
    if agg["games"]:
        gframes = [f for f in ["abstract", "named", "salient"]
                   if any(k[1] == f for k in agg["games"])]
        glab = {"abstract": "Bare matrix", "named": "Named game",
                "salient": "US–China framing"}
        gs = [glab[f] for f in gframes]
        gv = {(m, glab[f]): agg["games"].get((m, f))
              for m in models for f in gframes}
        body.append(grouped_bars(models, gs, gv, caption="Solved-game accuracy"))
        concepts = sorted({c for c, _ in agg["games_by_concept"]})
        body.append(table(
            ["Concept", *gs],
            [[c] + [pct(agg["games_by_concept"].get((c, f))) for f in gframes]
             for c in concepts]))
        body.append(
            '<p class="note">This is the control, not a headline. Its job is to '
            "establish whether a model can solve a structure in the abstract; "
            "only then does failure on the same structure under political "
            "framing say something about framing rather than about capability. "
            "The named condition isolates recall from computation.</p>")
    else:
        body.append('<p class="empty">No control-battery data in this run.</p>')
    secs.append(_sec("Control condition", "".join(body)))

    # -- 6. head to head ----------------------------------------------------
    body = ["<h2>Head to head</h2>"]
    if agg["origin_share"]:
        body.append(
            '<p class="lede">Cross-lab pairings on the salient frame. Share of '
            "bargaining surplus is normalised by each side&rsquo;s walk-away "
            "value, so it is comparable across seats; 50% is an even split. "
            "Every pairing runs in both seat assignments.</p>")
        hm = sorted(agg["origin_share"])
        body.append(grouped_bars(
            hm, ["Share of bargaining surplus"],
            {(m, "Share of bargaining surplus"): agg["origin_share"][m] for m in hm},
            caption="Surplus share in cross-lab play"))
        # Surplus share alone says how the pie was split but not whether there
        # was a pie. Deal rate, efficiency and the hard errors belong beside it.
        xl = agg.get("crosslab") or {}
        body.append(table(
            ["Model", "Lab", "Origin", "n", "Deals", "Efficiency",
             "Surplus share", "Below-BATNA", "Impasse w/ ZOPA", "Tabled a package"],
            [[m,
              REGISTRY[m].lab if m in REGISTRY else "—",
              REGISTRY[m].origin if m in REGISTRY else "—",
              str(xl.get(m, {}).get("n", "—")),
              pct(xl.get(m, {}).get("agreement_rate")),
              pct(xl.get(m, {}).get("per"), 1),
              pct(agg["origin_share"][m], 1),
              pct(xl.get(m, {}).get("below_batna")),
              pct(xl.get(m, {}).get("impasse_zopa")),
              pct(xl.get(m, {}).get("tabled_rate"))] for m in hm]))
        body.append(
            '<p class="note">Efficiency is computed over deals reached, so it '
            "says how good a package was when one was found, not how often one "
            "was. <b>Tabled a package</b> is the share of closing turns that "
            "produced a parseable settlement &mdash; a harness-level check, "
            "included because an earlier run of this arm was invalidated when a "
            "token limit silently truncated the reasoning models to empty "
            "replies and recorded it as a model failure.</p>")
        body.append(
            '<p class="note">The contest brief notes that none of the three '
            "projects it links evaluated Chinese models. This section and the "
            "Mandarin frame exist to close that gap.</p>")
    else:
        body.append('<p class="empty">No cross-lab data in this run.</p>')
    body.append(_pq(
        "China&rsquo;s primary concern is likely U.S. technology-related export "
        "controls, particularly those targeting semiconductors and equipment "
        "needed to make the most advanced chips.",
        "Council on Foreign Relations, December 2024 &mdash; the issue this "
        "case now seats its log-roll on",
        "https://www.cfr.org/articles/unpacking-chinas-four-red-lines-and-its-warning-trump"))
    secs.append(_sec("05\u00a0\u00b7\u00a0 Head to head", "".join(body)))

    # -- 7. label swap ------------------------------------------------------
    body = ["<h2>Whose interests are these?</h2>"]
    if agg["swap"]:
        body.append(
            '<p class="lede">The same private point schedule with national '
            "labels attached to the opposite structural role, so the model must "
            "advance interests that cut against its priors about that actor. "
            "Payoffs untouched.</p>")
        ss = ["Labels as authored", "Labels swapped"]
        sv = {(m, ss[0]): (agg["swap"].get((m, False)).per
                           if agg["swap"].get((m, False)) else None)
              for m in models}
        sv |= {(m, ss[1]): (agg["swap"].get((m, True)).per
                            if agg["swap"].get((m, True)) else None)
               for m in models}
        body.append(grouped_bars(models, ss, sv, caption="Efficiency under label swap"))
    else:
        body.append('<p class="empty">No label-swap data in this run.</p>')
    # What the swap probes: a model's priors about who these actors are.
    body.append(_pq(
        "\u5916\u90e8\u52bf\u529b\u6253\u201c\u53f0\u6e7e\u724c\u201d"
        "\uff0c\u662f\u628a\u53f0\u6e7e\u5f53\u4f5c\u904f\u5236\u4e2d"
        "\u56fd\u53d1\u5c55\u8fdb\u6b65\u3001\u963b\u6320\u4e2d\u534e"
        "\u6c11\u65cf\u4f1f\u5927\u590d\u5174\u7684\u68cb\u5b50",
        "\u300a\u53f0\u6e7e\u95ee\u9898\u4e0e\u65b0\u65f6\u4ee3\u4e2d"
        "\u56fd\u7edf\u4e00\u4e8b\u4e1a\u300b white paper, 2022, "
        "\u4e09(\u56db) &mdash; each side arrives with priors about what the "
        "other is really doing",
        "https://bw.china-embassy.gov.cn/sgxw/202208/t20220810_10740353.htm",
        zh=True,
        trans="External forces playing the &lsquo;Taiwan card&rsquo; are "
              "treating Taiwan as a chess piece to contain China&rsquo;s "
              "development and obstruct the rejuvenation of the Chinese nation."))
    secs.append(_sec("06\u00a0\u00b7\u00a0 Label swap", "".join(body)))

    # -- 8. the case --------------------------------------------------------
    body = [
        "<h2>The case</h2>",
        '<p class="lede">A six-issue US&ndash;PRC package, authored in the '
        "Kellogg DRRC / Harvard PON tradition. Structural checks prove "
        "every planted trap is reachable before any model is called.</p>",
        table(["Issue", "Role in the design", "Range to DELTA", "Range to OMEGA"],
              [[i.id.replace("_", " "), i.design_role.replace("_", " "),
                str(i.range_for("DELTA")), str(i.range_for("OMEGA"))]
               for i in case.issues]),
        table(["Quantity", "Value"],
              [["Packages in the outcome space", f"{an.n_packages:,}"],
               ["Maximum joint value", str(an.max_joint)],
               ["Pareto-optimal payoff pairs", str(len(an.pareto_front))],
               ["Packages beating both walk-away values", f"{an.zopa_size:,}"],
               ["DELTA walk-away value", str(an.batnas["DELTA"])],
               ["OMEGA walk-away value", str(an.batnas["OMEGA"])],
               ["Nash bargaining solution",
                f"DELTA {an.nash_solution['DELTA']} / OMEGA "
                f"{an.nash_solution['OMEGA']}" if an.nash_solution else "—"],
               ["Split-the-difference baseline", "78.8% of maximum joint value"]]),
        '<p class="note">Every number here is reproducible from '
        "<code>results.jsonl</code> via <code>python -m trackii.report</code>. "
        "The headline metrics are arithmetic on the private point schedules; no "
        "language model grades them.</p>",
    ]
    secs.append(_sec("Methodology", "".join(body)))

    return "".join(secs)


# ---------------------------------------------------------------------------
# Per-model view
# ---------------------------------------------------------------------------

def model_view(model: str, agg: dict, detail: dict, an) -> str:
    frames = _frames_present(agg)
    fl = [FRAME_LABEL[f] for f in frames]
    secs: list[str] = []
    spec = REGISTRY.get(model)

    cells = [c for c in (agg["frames"].get((model, f)) for f in frames) if c]
    xl = (agg.get("crosslab") or {}).get(model)
    # A model that only ran cross-lab has no self-play cells, so its headline
    # numbers come from the head-to-head instead -- labelled, because the two
    # are not the same measurement.
    selfplay = bool(cells)
    if selfplay:
        per = _mean([c.per for c in cells])
        agree = _mean([c.agreement_rate for c in cells])
        bad = _mean([c.below_batna for c in cells])
        imp = _mean([c.impasse_zopa for c in cells])
    else:
        per, agree = (xl or {}).get("per"), (xl or {}).get("agreement_rate")
        bad, imp = (xl or {}).get("below_batna"), (xl or {}).get("impasse_zopa")

    head = [f"<h1>{_esc(model)}</h1>"]
    if spec:
        head.append(
            f'<p class="lede">{_esc(spec.lab)} · {_esc(spec.origin)} · '
            f"<code>{_esc(spec.model_id)}</code></p>")
    if selfplay:
        provenance = ("Self-play across every framing, plus any cross-lab "
                      "pairings this model appeared in.")
    else:
        opp = _esc(", ".join((xl or {}).get("opponents") or []))
        provenance = (
            "<b>Cross-lab pairings only.</b> This model was not run in "
            "self-play, so the framing, ablation and label-swap arms have no "
            f"data for it. Everything here is head-to-head play against {opp}, "
            "in both seat assignments.")
    head.append(f'<p class="note">{provenance}</p>')
    head.append('<div class="stats">')
    for label, val in [
        ("Mean efficiency", pct(per, 1)),
        ("Agreement rate", pct(agree)),
        ("Below-BATNA", pct(bad)),
        ("Impasse w/ ZOPA", pct(imp)),
        ("Runs", str(sum(c.n for c in cells))),
    ]:
        head.append(f'<div class="stat"><b>{val}</b><span>{label}</span></div>')
    head.append("</div>")
    secs.append(_sec("Model", "".join(head)))

    # framing tax for this model alone
    body = ["<h2>Framing tax</h2>",
            '<p class="lede">This model across the four framings of one '
            "payoff structure.</p>",
            grouped_bars([FRAME_LABEL[f] for f in frames],
                         ["Pareto efficiency"],
                         {(FRAME_LABEL[f], "Pareto efficiency"):
                          (agg["frames"].get((model, f)).per
                           if agg["frames"].get((model, f)) else None)
                          for f in frames},
                         caption=f"{model} efficiency by framing"),
            table(["Framing", "Efficiency", "Agreement", "Below-BATNA", "n"],
                  [[FRAME_LABEL[f],
                    pct(agg["frames"][(model, f)].per, 1)
                    if (model, f) in agg["frames"] else "—",
                    pct(agg["frames"][(model, f)].agreement_rate)
                    if (model, f) in agg["frames"] else "—",
                    pct(agg["frames"][(model, f)].below_batna)
                    if (model, f) in agg["frames"] else "—",
                    str(agg["frames"][(model, f)].n)
                    if (model, f) in agg["frames"] else "0"]
                   for f in frames])]
    secs.append(_sec("Scores", "".join(body)))

    # control battery by concept
    gm = detail["games"].get(model, {})
    body = ["<h2>Control battery</h2>"]
    if gm:
        gframes = [f for f in ["abstract", "named", "salient"]
                   if any(k[1] == f for k in gm)]
        glab = {"abstract": "Bare matrix", "named": "Named game",
                "salient": "US–China"}
        concepts = sorted({c for c, _ in gm})
        body.append(table(
            ["Concept", *[glab[f] for f in gframes]],
            [[c] + [pct(gm.get((c, f))) for f in gframes] for c in concepts]))
        body.append('<p class="note">Whether this model can solve each '
                    "structure in the abstract, when told which game it is, and "
                    "when the same numbers wear a US–China story.</p>")
    else:
        body.append('<p class="empty">No control-battery data for this model.</p>')
    secs.append(_sec("Control condition", "".join(body)))

    # transcripts
    runs = detail["runs"].get(model, [])
    body = ["<h2>How it reasoned</h2>",
            '<p class="lede">Full transcripts. The contest brief notes that '
            "games tell you the outcome without telling you why &mdash; these "
            "are the why, and they are logged for every run.</p>"]
    if not runs:
        body.append('<p class="empty">No transcripts recorded for this model.</p>')
    for r in runs:
        sc = r.get("score") or {}
        tags = [f'<span class="tag">{_esc(FRAME_LABEL.get(r["frame"], r["frame"]))}'
                f"</span>",
                f'<span class="tag">seed {r.get("seed")}</span>']
        # A cross-lab transcript is unreadable without knowing which seat this
        # model held and who it was arguing with.
        if r.get("opponent"):
            tags.append(f'<span class="tag">as {_esc(r.get("seat") or "?")} '
                        f'vs {_esc(r["opponent"])}</span>')
        if r.get("agreement"):
            tags.append(f'<span class="tag good">deal · '
                        f'PER {pct(sc.get("pareto_efficiency_ratio"))}</span>')
        else:
            tags.append('<span class="tag bad">no deal</span>')
        if sc.get("any_below_batna"):
            tags.append('<span class="tag bad">below BATNA</span>')
        turns = "".join(
            f'<div class="turn {"omega" if t["role"] == "OMEGA" else ""}">'
            f'<div class="who">{_esc(t["role"])}'
            f'<span class="phase">{_esc(t["phase"])}</span></div>'
            f'<p>{_esc(t["text"])}{"…" if t["truncated"] else ""}</p></div>'
            for t in r["turns"] if (t["text"] or "").strip()
        )
        pkg = r.get("package")
        pkg_line = ("<div class=\"turn\"><div class=\"who\">Adopted package</div>"
                    f"<p>{_esc(' · '.join(f'{k}={v}' for k, v in pkg.items()))}"
                    "</p></div>") if pkg else ""
        body.append(
            f'<details class="run"><summary>{"".join(tags)}</summary>'
            f'<div class="turns">{turns}{pkg_line}</div></details>')
    secs.append(_sec("Transcripts", "".join(body)))
    return "".join(secs)


# ---------------------------------------------------------------------------
# Page assembly
# ---------------------------------------------------------------------------

def role_label(case: Case, role: str) -> str:
    """What to call this seat in the tab bar: its most recognisable identity."""
    for frame in ("salient", "neutral", "abstract"):
        if frame in case.frames:
            ident = case.frames[frame]["roles"][role]
            return ident.get("short") or ident["name"]
    return role


def role_view(case: Case, role: str, an) -> str:
    """The confidential role sheet, made public for the reader.

    This is the answer key. Publishing it is the point: a benchmark whose
    scoring you cannot inspect is a benchmark you have to take on trust.
    """
    other = case.roles[1] if role == case.roles[0] else case.roles[0]
    frames = [f for f in FRAME_ORDER if f in case.frames]
    label = role_label(case, role)
    secs: list[str] = []

    # -- who this is -------------------------------------------------------
    head = [f'<h1>{_esc(label)}</h1>',
            f'<p class="lede">The confidential instructions and private point '
            f"schedule handed to the <code>{_esc(role)}</code> seat. Its "
            f"counterpart holds a different schedule and never sees this one."
            "</p>",
            '<div class="stats">']
    for lbl, val in [
        ("Structural role", role),
        ("Max possible", str(case.max_payoff(role))),
        ("Walk-away value", str(case.batnas[role])),
        ("Counterpart", role_label(case, other)),
    ]:
        head.append(f'<div class="stat"><b>{_esc(val)}</b><span>{_esc(lbl)}</span></div>')
    head.append("</div>")
    head.append(
        f'<p class="takeaway">A package worth less than '
        f"<b>{case.batnas[role]}</b> points to this side is worse than no deal "
        f"at all. Signing one is a hard error, and it is stated in the prompt "
        f"in exactly those terms.</p>")
    # A quote grounding what this seat's real-world counterpart actually says.
    # The schedules are synthetic; the ordinal structure is not, and this is
    # where a reader most needs reminding which is which.
    grounding = {
        "DELTA": _pq(
            "&hellip;more favorable treatment on commercial matters, technology "
            "sharing, and defense procurement &mdash; those counties [sic] that "
            "willingly take more responsibility for security in their "
            "neighborhoods and align their export controls with ours.",
            "The White House, National Security Strategy, November 2025 &mdash; "
            "in 33 pages this is the <i>only</i> mention of export controls, and "
            "it is an offer to allies rather than a restriction on Beijing",
            "https://www.whitehouse.gov/wp-content/uploads/2025/12/2025-National-Security-Strategy.pdf"),
        "OMEGA": _pq(
            "\u4e2d\u56fd\u7684\u51fa\u53e3\u7ba1\u5236\u4e0d\u662f"
            "\u7981\u6b62\u51fa\u53e3\uff0c\u5bf9\u7b26\u5408\u89c4"
            "\u5b9a\u7684\u7533\u8bf7\u5c06\u4e88\u4ee5\u8bb8\u53ef"
            "\u3002\u2026\u7f8e\u65b9\u7ba1\u5236\u6e05\u5355\u7269"
            "\u9879\u8d85\u8fc73000\u9879\uff0c\u800c\u4e2d\u65b9"
            "\u51fa\u53e3\u7ba1\u5236\u6e05\u5355\u7269\u9879\u4ec5"
            "900\u4f59\u9879\u3002",
            "\u5546\u52a1\u90e8 MOFCOM spokesperson, 12 October 2025 &mdash; "
            "Beijing frames its own controls as reversible licensing, and counts "
            "them against Washington&rsquo;s",
            "https://www.gov.cn/zhengce/202510/content_7044134.htm", zh=True,
            trans="China&rsquo;s export controls are not an export ban; "
                  "applications meeting the requirements will be licensed. "
                  "&hellip; The US control list runs to over 3,000 items; "
                  "China&rsquo;s to just over 900."),
    }
    if role in grounding:
        head.append(grounding[role])
    secs.append(_sec("Role sheet", "".join(head)))

    # -- the point schedule ------------------------------------------------
    ref = "salient" if "salient" in case.frames else frames[0]
    f = case.frames[ref]
    rows = []
    for issue in case.issues:
        fi = f["issues"][issue.id]
        best = issue.best_for(role)
        for k, oid in enumerate(issue.option_ids):
            pts = issue.points[oid][role]
            mark = " ◄ best" if oid == best else ""
            rows.append([
                fi["name"] if k == 0 else "",
                f"[{oid}] {fi['options'][oid]}",
                f"{pts}{mark}",
                issue.design_role.replace("_", " ") if k == 0 else "",
            ])
    body = [
        "<h2>Private point schedule</h2>",
        '<p class="lede">The numbers are defined once in the case file and are '
        "identical in every framing. Only the labels below change &mdash; which "
        "is what makes the framing ablation airtight by construction rather "
        "than by care.</p>",
        table(["Issue", "Settlement option", f"Points to {label}",
               "Role in the design"], rows),
        f'<p class="note">Range per issue tells you where this side\'s leverage '
        f"is: "
        + ", ".join(
            f"<b>{_esc(i.id.replace('_', ' '))}</b> {i.range_for(role)}"
            for i in case.issues)
        + ".</p>",
    ]
    secs.append(_sec("Points", "".join(body)))

    # -- the verbatim prompt, per frame ------------------------------------
    pills = "".join(
        f'<button data-frame="{fr}" aria-selected="{"true" if i == 0 else "false"}">'
        f"{_esc(FRAME_LABEL[fr])}</button>"
        for i, fr in enumerate(frames))
    blocks = []
    for i, fr in enumerate(frames):
        sheet = case.render_role_sheet(fr, role)
        proto = (PROTOCOL_ZH if case.frame_lang(fr) == "zh" else PROTOCOL).format(
            rounds=4, example=_example(case))
        blocks.append(
            f'<pre class="sheet" data-frame="{fr}"{"" if i == 0 else " hidden"}>'
            f"{_esc(sheet)}\n\n{_esc(proto)}</pre>")
    body = [
        "<h2>The prompt it actually receives</h2>",
        '<p class="lede">Verbatim, exactly as sent &mdash; role sheet plus '
        "negotiation protocol. Switch framing to see the same point values "
        "under different labels.</p>",
        f'<div class="framepills">{pills}</div>',
        "".join(blocks),
    ]
    secs.append(_sec("Prompt", "".join(body)))
    return "".join(secs)


def _gloss(items: list[tuple[str, str]]) -> str:
    """Definition list. Terms carry the sans furniture, bodies the serif."""
    # Terms are authored with entities (Kalai&ndash;Smorodinsky), so unescape
    # before escaping. Bodies are trusted HTML and pass through untouched.
    rows = "".join(
        f"<div><dt>{_esc(_html.unescape(t))}</dt><dd>{d}</dd></div>"
        for t, d in items
    )
    return f'<dl class="gloss">{rows}</dl>'


def _pq(quote: str, cite: str, url: str = "", zh: bool = False,
        trans: str = "") -> str:
    """A pull quote for the narrative sections.

    Lighter than _ev: no tier or confidence badge, because these are here to
    ground an argument the reader is already following, not to carry a coded
    cell. The full evidence with locators lives in the appendix.
    """
    e = lambda t: _esc(_html.unescape(t))
    cls = " zh" if zh else ""
    out = [f'<figure class="pq"><blockquote class="{cls.strip()}">&ldquo;'
           f"{e(quote)}&rdquo;</blockquote>"]
    if trans:
        out.append(f"<blockquote>&ldquo;{e(trans)}&rdquo;</blockquote>")
    link = f'<a href="{_esc(url)}">{e(cite)}</a>' if url else e(cite)
    out.append(f"<figcaption>{link}</figcaption></figure>")
    return "".join(out)


def _ev(quote: str, cite: str, url: str, tier: str, conf: str,
        zh: bool = False, trans: str = "") -> str:
    """One evidence block: quotation, citation, evidence tier, confidence.

    Required by RESEARCH_PLAN.md §12.2 -- every structural claim in the appendix
    carries its evidence with it rather than asking the reader to trust it.
    """
    t = {"A": "Tier A · revealed concession", "B": "Tier B · linkage statement",
         "C": "Tier C · declared salience", "D": "Tier D · expert assessment",
         "E": "Tier E · journalism"}[tier]
    cls = " zh" if zh else ""
    # These strings are authored with HTML entities for readability. Unescape
    # first so _esc does not turn "&rsquo;" into "&amp;rsquo;" on the page.
    e = lambda t: _esc(_html.unescape(t))
    out = [f'<div class="ev"><blockquote class="q{cls}">&ldquo;{e(quote)}'
           "&rdquo;</blockquote>"]
    if trans:
        out.append(f'<blockquote class="q">&ldquo;{e(trans)}&rdquo;</blockquote>')
    link = f'<a href="{_esc(url)}">{e(cite)}</a>' if url else e(cite)
    out.append(f'<p class="cite">{link}</p>')
    out.append(f'<div class="badges"><span class="badge t{tier}">{_esc(t)}</span>'
               f'<span class="badge {"hi" if conf=="High" else "mod"}">'
               f"{_esc(conf)} confidence</span></div></div>")
    return "".join(out)


def appendix_view(case: Case, an) -> str:
    """Methodology appendix: the case, the schedules, the arms, the terms."""
    a, b = case.roles
    frames = [f for f in FRAME_ORDER if f in case.frames]
    secs: list[str] = []

    # -- 1. this case -------------------------------------------------------
    body = [
        "<h1>Appendix: methodology</h1>",
        f'<p class="lede">How <b>{_esc(case.title)}</b> is built, what each '
        "experiment arm isolates, and what every term on this site means.</p>",
        "<h3>The case</h3>",
        f"<p>{_esc(' '.join(case.frames['salient']['scenario'].split()))}</p>",
        table(["Issue", "Structural role", f"Range to {role_label(case, a)}",
               f"Range to {role_label(case, b)}"],
              [[case.frames["salient"]["issues"][i.id]["name"],
                i.design_role.replace("_", " "),
                str(i.range_for(a)), str(i.range_for(b))] for i in case.issues]),
        table(["Quantity", "Value"],
              [["Packages in the outcome space", f"{an.n_packages:,}"],
               ["Maximum joint value", str(an.max_joint)],
               ["Pareto-optimal payoff pairs", str(len(an.pareto_front))],
               ["Packages beating both walk-away values (ZOPA)",
                f"{an.zopa_size:,} ({an.zopa_size / an.n_packages:.0%})"],
               [f"{role_label(case, a)} walk-away value", str(an.batnas[a])],
               [f"{role_label(case, b)} walk-away value", str(an.batnas[b])],
               ["Framings", ", ".join(FRAME_LABEL[f] for f in frames)]]),
    ]
    secs.append(_sec("Appendix", "".join(body)))

    # -- 2. where the numbers come from -------------------------------------
    body = [
        "<h2>Where the point schedules come from</h2>",
        '<p class="lede">The schedules are <b>synthetic</b>. They are authored, '
        "not measured &mdash; not drawn from any licensed DRRC or PON exercise, "
        "any dataset, any expert elicitation, or any published source.</p>",
        '<div class="warnbox"><p>They are <b>not</b> a claim about real-world '
        "preferences. That Taiwan arms sales carry 40 points for one side does "
        "not assert what Washington actually values relative to tariffs. Reading "
        "these as empirical claims about US or PRC policy would be a mistake."
        "</p></div>",
        "<h3>Method: design backwards from the metrics</h3>",
        "<ol><li><b>Take the structural inventory</b> from the "
        "negotiation-teaching tradition: a compatible issue, a log-roll pair, a "
        "pure distributive issue, an interior optimum, asymmetric walk-away "
        "values. That inventory is what makes those cases teach &mdash; and what "
        "makes this one measure, since each element maps to a metric.</li>"
        "<li><b>Assign each real issue a structural role.</b> Fentanyl precursor "
        "enforcement became the compatible issue because both sides plausibly do "
        "want it while each assumes the other will charge for it.</li>"
        "<li><b>Tune magnitudes until every trap is reachable and detectable.</b> "
        "Splitting the compatible issue must destroy enough joint value to move "
        "the efficiency ratio; below-BATNA must be reachable without being "
        "routine; the naive baseline must leave real headroom.</li>"
        "<li><b>Treat the validator as the specification.</b> The structural "
        "checks define what the case must do; magnitudes were iterated until "
        "they all passed. They are not a test applied afterwards.</li></ol>",
        '<p class="takeaway">What is defensible is the <i>ordinal</i> structure '
        "&mdash; which issue plays which role, and which side cares more about "
        "what. The cardinal values are not claims; they are chosen to make the "
        "structure work.</p>",
        '<p class="note"><b>Known limitation.</b> Assigning real issues to '
        "structural roles rests on the author&rsquo;s judgment alone. "
        "Independent expert ranking of issue intensities per side would "
        "strengthen it, and has not been done.</p>",
    ]
    secs.append(_sec("Provenance", "".join(body)))

    # -- 2b. the sourced evidence -------------------------------------------
    body = [
        "<h2>What the record actually supports</h2>",
        '<p class="lede">The schedules are synthetic, but the <b>ordinal '
        "structure</b> &mdash; which issue plays which role, and which side "
        "cares more &mdash; was tested against primary sources. Thirty-six "
        "documents, 4.6 million characters, downloaded and read in full. "
        "<b>Nine of twelve cells confirmed, two partial, one contradicted "
        "&mdash; and where the record and the design disagreed, the case now "
        "follows the record.</b></p>",
        '<div class="warnbox"><p><b>What changed as a result.</b> The log-roll '
        "was re-seated from export-controls-against-Taiwan onto the pair the "
        "record documents: semiconductors against critical minerals. Fentanyl "
        "precursors were re-priced from a compatible issue to a lever Beijing "
        "withholds. Taiwan arms sales were demoted to a low-range side issue and "
        "re-laddered around a specific pending package. In the crisis case the "
        "walk-away gap was widened, the hotline upgraded, and the scope ladder "
        "rebuilt around cargo classes. Every change is sourced below.</p></div>",

        "<h3>Both sides rank export controls first</h3>",
        "<p>The case as shipped gives Washington its widest range on Taiwan arms "
        "sales. The record does not support that.</p>",
        _ev("China&rsquo;s primary concern is likely U.S. technology-related "
            "export controls, particularly those targeting semiconductors and "
            "equipment needed to make the most advanced chips.",
            "Council on Foreign Relations, &lsquo;Unpacking China&rsquo;s Four "
            "Red Lines&rsquo;, 12 December 2024",
            "https://www.cfr.org/articles/unpacking-chinas-four-red-lines-and-its-warning-trump",
            "D", "High"),
        _ev("\u4e2d\u56fd\u7684\u51fa\u53e3\u7ba1\u5236\u4e0d\u662f\u7981"
            "\u6b62\u51fa\u53e3\uff0c\u5bf9\u7b26\u5408\u89c4\u5b9a\u7684"
            "\u7533\u8bf7\u5c06\u4e88\u4ee5\u8bb8\u53ef\u3002",
            "\u5546\u52a1\u90e8 (MOFCOM) spokesperson, press Q&amp;A, "
            "12 October 2025, item 1",
            "https://www.gov.cn/zhengce/202510/content_7044134.htm",
            "C", "High", zh=True,
            trans="China&rsquo;s export controls are not an export ban; "
                  "applications that meet the requirements will be licensed."),
        "<p>Beijing frames its own controls as a calibrated, reversible "
        "instrument &mdash; the signature of a bargaining chip, not a red line. "
        "Across the 745-page USCC report, <b>&lsquo;export control&rsquo; "
        "appears 223 times against 11 for &lsquo;arms sale&rsquo;</b>.</p>",

        "<h3>The real log-roll runs export controls against export controls</h3>",
        "<p>The case pairs US export controls with Taiwan arms sales. The one "
        "documented instance of these parties actually trading concessions pairs "
        "export controls with <i>each other</i>.</p>",
        _ev("In July 2025, BIS rescinded license requirements for EDA firms "
            "after the PRC agreed to resume licensing rare earth magnets for "
            "U.S. firms.",
            "Congressional Research Service R48642, &lsquo;U.S. Export Controls "
            "and China: Advanced Semiconductors&rsquo;",
            "https://www.everycrsreport.com/reports/R48642.html", "A", "High"),
        "<p>The exchange also fixes the <i>orientation</i>, which is usually "
        "the harder half to source. Each side conceded the issue it valued "
        "less:</p>",
        # via table(), which wraps in .scroll -- a hand-written <table> here
        # overflowed the viewport on narrow screens with no way to scroll it
        table(["", "conceded", "won", "therefore values"],
              [["United States", "EDA &mdash; semiconductors", "rare-earth magnets",
                "minerals > semiconductors"],
               ["China", "magnets &mdash; minerals", "EDA relief",
                "semiconductors > minerals"]]),
        _ev("China accounted for over 90 percent of global production of "
            "neodymium (rare earth) magnets in 2024.",
            "International Energy Agency, via Peterson Institute for "
            "International Economics",
            "https://www.piie.com/blogs/realtime-economics/2026/trump-china-trade-wars-five-takeaways-us-imports-2025",
            "D", "High"),
        "<p><b>An adversarial search then broke half of this.</b> The EDA "
        "restrictions were imposed in May 2025 and lifted in July &mdash; under "
        "six weeks. Read as a sequence, that is escalation, counter-escalation, "
        "and a return to the status quo ante. Mutual de-escalation is not a "
        "log-roll: undoing reciprocal harm restores a position both sides "
        "already preferred, which is escaping a prisoner&rsquo;s dilemma rather "
        "than creating joint value.</p>",
        _ev("China exerts temporary leverage while avoiding long-term damage to "
            "its own processing industry.",
            "Resources for the Future, modelling rare-earth restrictions as a "
            "repeated game after Fudenberg and Maskin (1986)",
            "https://www.rff.org/publications/issue-briefs/the-strategic-game-of-rare-earths-why-china-may-only-be-in-favor-of-temporary-export-restrictions/",
            "D", "Moderate"),
        _ev("America&rsquo;s semiconductor choke point cuts deeper and endures "
            "longer than China&rsquo;s rare earth ban&hellip; each use of a "
            "choke point weakens its impact.",
            "Alvin Camba, &lsquo;The Burn and the Choke&rsquo;, War on the "
            "Rocks, 5 January 2026",
            "https://warontherocks.com/the-burn-and-the-choke-why-semiconductor-controls-will-outlast-chinas-rare-earth-weapon/",
            "D", "Moderate"),
        '<p class="takeaway">What survives: export controls of both kinds are '
        "the live bargaining currency, they are traded against <i>each other</i>, "
        "and Taiwan sits outside that trade &mdash; so the shipped log-roll is "
        "unsupported. What does not survive: the orientation, which drops from "
        "Tier A to <b>Tier B at moderate confidence</b>, and the claim that the "
        "two arms form a symmetric pair, which is withdrawn. If Beijing&rsquo;s "
        "restriction was always meant to be temporary, relinquishing it says "
        "little about how it prices minerals against chips.</p>",
        "<p><b>Implemented.</b> The case now carries "
        "<code>semiconductor_controls</code> (China the intense side, so the "
        "United States concedes) against <code>critical_minerals</code> (the "
        "United States the intense side, so China concedes). Both ladders are "
        "taken from the instruments the two governments actually use &mdash; "
        "Entity List, foreign direct product rule, performance thresholds, "
        "general licence, rescission on one side; outright bar, case-by-case "
        "licensing, general licence against end-use certification, suspension "
        "on the other. Orientation is carried at Tier B, and the asymmetry the "
        "counter-evidence established &mdash; minerals leverage decays as it is "
        "used, the semiconductor choke point does not &mdash; is recorded in the "
        "case file as a mis-specification a static schedule cannot express.</p>",

        "<h3>Taiwan arms sales sit below the statutory threshold</h3>",
        _ev("\u201c\u53f0\u72ec\u201d\u5206\u88c2\u52bf\u529b\u4ee5\u4efb"
            "\u4f55\u540d\u4e49\u3001\u4efb\u4f55\u65b9\u5f0f\u9020\u6210"
            "\u53f0\u6e7e\u4ece\u4e2d\u56fd\u5206\u88c2\u51fa\u53bb\u7684"
            "\u4e8b\u5b9e\uff0c\u6216\u8005\u53d1\u751f\u5c06\u4f1a\u5bfc"
            "\u81f4\u53f0\u6e7e\u4ece\u4e2d\u56fd\u5206\u88c2\u51fa\u53bb"
            "\u7684\u91cd\u5927\u4e8b\u53d8\uff0c\u6216\u8005\u548c\u5e73"
            "\u7edf\u4e00\u7684\u53ef\u80fd\u6027\u5b8c\u5168\u4e27\u5931"
            "\uff0c\u56fd\u5bb6\u5f97\u91c7\u53d6\u975e\u548c\u5e73\u65b9"
            "\u5f0f\u53ca\u5176\u4ed6\u5fc5\u8981\u63aa\u65bd",
            "\u53cd\u5206\u88c2\u56fd\u5bb6\u6cd5 Anti-Secession Law (2005), "
            "Article 8", "https://zh.wikisource.org/wiki/%E5%8F%8D%E5%88%86%E8%A3%82%E5%9C%8B%E5%AE%B6%E6%B3%95",
            "C", "High", zh=True,
            trans="Should secessionist forces cause Taiwan&rsquo;s separation "
                  "from China in fact, or should a major incident occur that "
                  "would lead to it, or should the possibility of peaceful "
                  "reunification be completely lost, the state shall employ "
                  "non-peaceful means and other necessary measures."),
        "<p>Three statutory triggers, and arms sales are not among them. The "
        "2022 white paper lists them third of seven grievances, inside a frame "
        "of <span lang=\"zh\">\u4ee5\u53f0\u5236\u534e</span> &mdash; "
        "using Taiwan to contain China &mdash; which makes Taiwan pressure "
        "instrumental to the technology contest rather than prior to it.</p>",
        "<p><b>Implemented.</b> <code>security_commitment</code> was the "
        "widest issue on the United States&rsquo; sheet. It is now a "
        "<b>low-range side issue</b>, and its ladder is no longer the "
        "US&ndash;Taiwan relationship &mdash; which neither party trades "
        "&mdash; but a <b>specific pending package: released, deferred, or "
        "held</b>. That increment is what the record shows actually being "
        "used as leverage, and it is what a negotiator could plausibly "
        "settle in a single round.</p>",
        "<p>One correction worth stating plainly, because an earlier draft of "
        "this appendix got it wrong. Beijing is <i>not</i> purely rhetorical on "
        "arms sales:</p>",
        _ev("China Slaps Sanctions on 13 US Military Firms over Taiwan Arms Sale",
            "Reuters, 5 December 2024, as cited in the USCC 2025 Report",
            "https://www.uscc.gov/annual-report/2025-annual-report-congress",
            "A", "High"),
        "<p>The claim that Beijing announces no countermeasures was wrong and is "
        "withdrawn. What survives is a difference in <i>price</i>: sanctioning US "
        "defence firms already barred from the Chinese market costs Beijing "
        "almost nothing, where the gallium and germanium bans cost Chinese "
        "exporters real revenue. The ranking holds; the reasoning changed.</p>",

        "<h3>The executive and Congress do not weight this the same way</h3>",
        "<p>The design treats one seat as &lsquo;the United States&rsquo;. The "
        "record does not. Across 33 pages the 2025 National Security Strategy "
        "mentions <b>&lsquo;export control&rsquo; once</b> &mdash; and that once "
        "is an offer to allies, not a restriction on China.</p>",
        _ev("&hellip;more favorable treatment on commercial matters, technology "
            "sharing, and defense procurement &mdash; those counties [sic] that "
            "willingly take more responsibility for security in their "
            "neighborhoods and align their export controls with ours.",
            "The White House, National Security Strategy, November 2025, p. 13",
            "https://www.whitehouse.gov/wp-content/uploads/2025/12/2025-National-Security-Strategy.pdf",
            "C", "High"),
        "<p>The same document mentions critical minerals five times, as a "
        "question of <i>access</i> rather than denial, and frames Taiwan around "
        "geography &mdash; valued &ldquo;partly because of Taiwan&rsquo;s "
        "dominance of semiconductor production, but mostly because Taiwan "
        "provides direct access to the Second Island Chain&rdquo;. The "
        "USCC&rsquo;s 223 export-control mentions belong to the "
        "<b>congressional</b> actor, which this design routes through the "
        "walk-away value rather than the point schedule.</p>",
        _ev("Some former U.S. officials have expressed concerns about what they "
            "have described as negotiating national security decisions in "
            "exchange for trade concessions or government revenue&hellip; "
            "contradicting past U.S. practice to reject PRC efforts to negotiate "
            "on such terms.",
            "Congressional Research Service R48642",
            "https://www.everycrsreport.com/reports/R48642.html", "C", "High"),
        "<p>That objection is precisely why Congress enters through the "
        "walk-away value: it is a constraint on what the executive can sign, not "
        "a preference the executive holds.</p>",

        "<h3>The crisis case understates its own asymmetry</h3>",
        _ev("Quarantine is not a low-risk, slow-moving action, equivalent to "
            "imposing economic sanctions. Regardless of how it is imposed, such "
            "an action is likely to rapidly escalate to use of force.",
            "RAND Corporation RRA1279-1, &lsquo;Implications of a Coercive "
            "Quarantine of Taiwan by the People&rsquo;s Republic of China&rsquo;",
            "https://www.rand.org/pubs/research_reports/RRA1279-1.html",
            "D", "High"),
        _ev("While there may be room to negotiate the movement of particular "
            "kinds of commodities, if the PRC declines to allow free shipment, "
            "no amount of indirect pressure is likely to result in the PRC "
            "abandoning its efforts.",
            "RAND Corporation RRA1279-1, Findings",
            "https://www.rand.org/pubs/research_reports/RRA1279-1.html",
            "D", "High"),
        "<p>Two consequences. The walk-away gap in the crisis case is "
        "directionally right and too narrow &mdash; RAND finds the PRC holds "
        "&ldquo;effectively every advantage&rdquo; and that the asymmetry "
        "worsens as the quarantine runs. And the negotiable object is <i>which "
        "cargoes move</i>, not whether the quarantine ends, which is a sourced "
        "specification for a ladder the design currently authors.</p>",
        "<p><b>Implemented.</b> The crisis case now runs a wider walk-away "
        "gap, and <code>quarantine_scope</code> is laddered by <b>cargo "
        "class</b> &mdash; all cargo boarded, humanitarian exempt, "
        "humanitarian and energy exempt, all civilian cargo exempt, "
        "regime lifted &mdash; which is the object RAND says is actually "
        "negotiable. The hotline was also upgraded: it was priced against "
        "Beijing&rsquo;s 2022 suspension, but the MMCA working groups of "
        "November 2025 and May 2026 are publicised approvingly by both "
        "militaries&rsquo; own outlets, which is a stronger compatibility "
        "signal than the hedge it replaced.</p>",
        _ev("The Economic Balance of Power Between Taiwan and China Favors the "
            "PRC &hellip; the PRC has effectively every advantage over Taiwan, "
            "and if the confrontation were to go on for a prolonged period, the "
            "PRC is in a much better position to endure whatever consequences "
            "might develop.",
            "RAND RRA1279-1, Findings",
            "https://www.rand.org/pubs/research_reports/RRA1279-1.html",
            "D", "High"),
        _ev("Only 13 percent of surveyed U.S. experts and 9 percent of Taiwan "
            "experts were &lsquo;completely confident&rsquo; that the United "
            "States would intervene militarily.",
            "CSIS ChinaPower, on a quarantine scenario",
            "https://features.csis.org/chinapower/china-quarantine-taiwan/",
            "D", "Moderate"),
        "<p>Two independent sources &mdash; one on material capacity, one on "
        "expected US behaviour &mdash; pointing the same way. That is why the "
        "crisis case gives the Chinese seat the better no-deal position, and why "
        "the gap was widened rather than left as authored.</p>",

        "<h3>The compatible issues both survived scrutiny</h3>",
        "<p>Nearly every other structural claim in these cases was weakened by "
        "the record. These two were not.</p>",
        _ev("The two sides agreed that effective communication and exchanges "
            "between the two militaries can help frontline troops perform tasks "
            "in a more professional manner, deepen mutual understanding and "
            "avoid misperception and miscalculation.",
            "PRC Ministry of National Defence, on the November 2025 Military "
            "Maritime Consultative Agreement working group",
            "http://eng.mod.gov.cn/2025xb/N/T/16423311.html", "A", "High"),
        "<p>Beijing&rsquo;s own defence ministry publicising military cooperation "
        "with the United States is a stronger compatibility signal than any "
        "third-party assessment.</p>",
        _ev("The renewed Agreement narrows its scope to basic research and "
            "intergovernmental collaboration in specific pre-identified areas "
            "&hellip; Sensitive and emerging technologies have been explicitly "
            "excluded.",
            "US Department of State, on the amended Science and Technology "
            "Agreement, 13 December 2024",
            "https://2021-2025.state.gov/amendment-and-extension-of-the-u-s-prc-science-and-technology-agreement-sta/",
            "A", "High"),
        "<p>Both governments signed. Small positive value to each with a hard "
        "ceiling is exactly what a minor compatible issue encodes &mdash; and in "
        "the package deal it is now the only place a model can find free joint "
        "value, since precursors turned out to carry a price.</p>",

        "<h3>The compatible issue is falsified</h3>",
        "<p>Fentanyl precursor enforcement was chosen as the compatible issue: "
        "something both sides want and neither should have to buy. The record "
        "shows it being bought, in both directions.</p>",
        _ev("&hellip;additional tariffs on China, ostensibly in response to "
            "China&rsquo;s unfair trade practices and lack of cooperation on "
            "cracking down on the shipment of fentanyl precursors to North "
            "America.",
            "USCC 2025 Report to Congress, p. 176",
            "https://www.uscc.gov/annual-report/2025-annual-report-congress",
            "B", "High"),
        _ev("The United States agreed to halve its fentanyl-related tariffs "
            "from 20 to 10 percent; China committed to restore cooperation on "
            "fentanyl precursor flows.",
            "Brookings, &lsquo;What happened when Trump met Xi&rsquo;, on the "
            "Busan summit, 30 October 2025",
            "https://www.brookings.edu/articles/what-happened-when-trump-met-xi/",
            "A", "High"),
        '<p class="takeaway">Imposed for non-cooperation, relaxed for '
        "cooperation. That is a price, not a shared preference. <b>Implemented:</b> "
        "<code>precursors</code> is now an exactly zero-sum lever Beijing "
        "holds and sells, not a shared goal &mdash; so the "
        "case&rsquo;s compatible issue is not compatible.</p>",

        "<h3>The Mandarin frame predicts a direction</h3>",
        _ev("A troubling divergence has emerged between China&rsquo;s "
            "English-language and Chinese-language propaganda about Taiwan "
            "&hellip; Whereas Chinese statements aimed at international "
            "audiences downplay the possibility of an invasion, China&rsquo;s "
            "domestic propaganda has stated that Taiwan&rsquo;s "
            "&lsquo;provocations&rsquo; could justify military action in the "
            "near future.",
            "USCC 2025 Report to Congress, pp. 15&ndash;16",
            "https://www.uscc.gov/annual-report/2025-annual-report-congress",
            "D", "High"),
        "<p>This turns the Mandarin arm from a language-invariance check into a "
        "directional hypothesis: if models inherit the divergence from their "
        "training corpora, the Mandarin frame should shift them toward "
        "escalation relative to the English salient frame.</p>",

        "<h3>How far the sources agree with each other</h3>",
        "<p>A single coder cannot produce inter-rater reliability, so none is "
        "claimed. What can be measured is how far <i>independent sources</i> "
        "agree about the same cell &mdash; 37 source-cell judgements across the "
        "twelve:</p>",
        '<p class="note">These cells are the <b>pre-revision</b> coding: the '
        "review that produced them is what caused the case to be rewritten, so "
        "the row labelled <code>export_controls</code> is the single issue that "
        "has since been split into <code>semiconductor_controls</code> and "
        "<code>critical_minerals</code>. Recomputing against the current seven "
        "issues would mean re-coding every source, which is a research task "
        "rather than an arithmetic one, and it has not been done.</p>",
        table(["Cell", "Sources", "Concordance", "Status"],
              [["export_controls · OMEGA", "5", "100%", "uncontested"],
               ["market_access · both", "2 each", "100%", "uncontested"],
               ["precursors · DELTA", "2", "100%", "uncontested"],
               ["joint_research · both", "1 each", "100%", "single-sourced"],
               ["tariffs · OMEGA", "4", "75%", "qualified"],
               ["tariffs · DELTA", "3", "67%", "qualified"],
               ["export_controls · DELTA", "5", "60%", "contested"],
               ["security_commitment · OMEGA", "5", "60%", "contested"],
               ["security_commitment · DELTA", "4", "25%", "weakest cell"],
               ["precursors · OMEGA", "3", "0%", "unanimously against"],
               ["overall", "37", "68%", "6 uncontested · 3 qualified · 3 contested"]]),
        "<p>Three things this surfaces that prose had hidden. "
        "<b>joint_research rests on a single source on both sides</b> and should "
        "not be called confirmed. <b>security_commitment · DELTA scores 25%</b> "
        "&mdash; three of its four sources merely qualify &mdash; making it the "
        "least secure cell in the design, and one this project had been treating "
        "as settled. And <b>precursors · OMEGA scores zero</b>: every source "
        "contradicts the shipped coding, which makes it the firmest result "
        "here.</p>",
        '<p class="note"><b>Single coder.</b> No second rater, so no '
        "reliability statistics and no Krippendorff&rsquo;s &alpha;. Confidence "
        "is reported per claim instead. Cardinal magnitudes and walk-away levels "
        "remain authored and were never in scope.</p>",
    ]
    secs.append(_sec("Evidence", "".join(body)))

    # -- 3. experiment arms -------------------------------------------------
    fl = ", ".join(FRAME_LABEL[f] for f in frames)
    body = [
        "<h2>Experiment arms</h2>",
        '<p class="lede">Each arm changes exactly one thing. Everything else '
        "&mdash; payoffs, protocol, round budget, temperature &mdash; is held "
        "fixed.</p>",
        table(["Arm", "What varies", "What it isolates"],
              [["frames", f"{len(frames)} framings of one payoff structure, "
                "model plays both seats",
                "Political salience, separated from reasoning. The Mandarin "
                "framing further separates prompt language from model origin."],
               ["nocomm", "Same closing exchange, zero rounds of dialogue",
                "Whether the benchmark measures negotiation at all. If silence "
                "scores as well as talking, it does not."],
               ["swap", "National labels attached to the opposite structural role",
                "What happens when a model must advance interests that cut "
                "against its priors about that actor."],
               ["head", "Cross-lab pairings, each run in both seat assignments",
                "Relative performance, with seat effects cancelled."],
               ["games", "Eight solved games, asked bare / named / US&ndash;China",
                "Whether a model can solve the structure at all &mdash; the "
                "control that makes the framing result interpretable."]]),
        f'<p class="note">Framings present in this case: {_esc(fl)}. Payoffs are '
        "defined once and framings supply labels only, so every framing is "
        "provably the same game.</p>",
    ]
    secs.append(_sec("Arms", "".join(body)))

    # -- 4. instance sampling -----------------------------------------------
    body = [
        "<h2>Instance sampling</h2>",
        '<p class="lede">One authored payoff structure gives many samples of '
        "conversation but a single sample of <i>game</i>. Seeds vary the "
        "dialogue, not the problem &mdash; so any model difference could be an "
        "artifact of one draw.</p>",
        "<h3>What moves, and what does not</h3>",
        "<p>The design template is fixed: which issue is compatible, which pair "
        "carries the log-roll, which is exactly zero-sum, which has an interior "
        "optimum. Only the magnitudes move. Each option&rsquo;s rank within its "
        "issue is preserved exactly, so preferred settlements, monotonicity and "
        "the interior peak all survive rescaling.</p>",
        "<h3>The validator is the acceptance test</h3>",
        "<p>Every draw must pass the full structural check before it is emitted. "
        "Drawing point values freely would mostly produce degenerate games "
        "&mdash; empty bargaining ranges, &lsquo;compatible&rsquo; issues that "
        "are not, log-rolls with no integrative potential. An instance that "
        "ships is provably well-posed, exactly like the authored one.</p>",
        "<h3>Instance as a blocking factor</h3>",
        "<p>One draw is held fixed across every framing, model and seat "
        "assignment. That preserves the framing invariant and makes the design "
        "<b>paired</b>: the framing tax is computed <i>within</i> each instance "
        "and only then averaged, so instance difficulty cancels instead of "
        "inflating the variance.</p>",
        '<p class="takeaway">A finding that survives many independently drawn '
        "magnitude sets satisfying the same structural specification is a "
        "property of the structure, not of one author&rsquo;s arithmetic.</p>",
    ]
    secs.append(_sec("Sampling", "".join(body)))

    # -- 5. negotiation glossary --------------------------------------------
    body = [
        "<h2>Terms: negotiation</h2>",
        '<p class="lede">The vocabulary is from the integrative-bargaining '
        "literature. Each term below corresponds to something the scorer "
        "computes exactly.</p>",
        _gloss([
            ("BATNA / reservation value",
             "<b>Best Alternative To a Negotiated Agreement</b> &mdash; what a "
             "side receives if the talks fail. It is stated to each model in "
             "points, in its own prompt, so accepting a package worth less is "
             "an unambiguous error with no interpretation required."),
            ("ZOPA",
             "<b>Zone Of Possible Agreement</b> &mdash; the set of packages "
             "that beat <i>both</i> sides&rsquo; walk-away values. If it is "
             "empty no deal should be struck; if it is non-empty and the talks "
             "still collapse, that is a failure with a denominator."),
            ("Compatible issue",
             "An issue where both sides secretly prefer the <i>same</i> "
             "settlement, but each assumes the other opposes it. Negotiators "
             "with fixed-pie bias &lsquo;split the difference&rsquo; on it and "
             "destroy joint value for nothing. Planted deliberately, and the "
             "loss is measured."),
            ("Log-roll pair",
             "Two issues where the intensities run opposite &mdash; one matters "
             "more to you, the other more to them. Trading them wholesale "
             "creates joint value that splitting both cannot. The canonical "
             "integrative move."),
            ("Pure distributive issue",
             "An issue that is exactly zero-sum: joint value is constant "
             "whatever the settlement, so one side&rsquo;s gain is precisely "
             "the other&rsquo;s loss. This is where value <i>claiming</i> is "
             "measured, cleanly separated from value creation."),
            ("Interior optimum",
             "An issue whose best settlement for a side is neither extreme "
             "&mdash; a middle option. It catches negotiators who assume "
             "preferences are linearly opposed instead of reading their own "
             "schedule."),
            ("Asymmetric BATNAs",
             "The two sides have different walk-away values, so one can "
             "credibly leave far more packages on the table than the other. "
             "Bargaining power is a structural fact here, not a rhetorical one "
             "&mdash; and the Nash solution reflects it."),
            ("Side payment",
             "Compensating a side on one issue so it will accept a settlement "
             "that costs it on another. In this case the log-roll creates joint "
             "value but leaves one side locally worse off, so it only closes if "
             "funded from the distributive issue."),
            ("Pareto frontier",
             "The set of outcomes where no side can be made better off without "
             "making the other worse off. Enumerated exactly here rather than "
             "estimated, because the outcome space is small enough to walk in "
             "full."),
            ("Pareto efficiency ratio",
             "Joint value achieved divided by the maximum joint value "
             "available. The headline measure of value <i>creation</i>: 100% "
             "means nothing was left on the table."),
            ("Nash bargaining solution",
             "The outcome maximising the product of both sides&rsquo; gains "
             "over their walk-away values. A principled answer to &lsquo;what "
             "is a fair efficient split&rsquo;, and sensitive to bargaining "
             "power &mdash; the side with the stronger BATNA gets more."),
            ("Kalai&ndash;Smorodinsky",
             "An alternative fairness solution equalising each side&rsquo;s "
             "gain as a proportion of the best it could have hoped for. "
             "Reported alongside Nash because reasonable people disagree about "
             "which fairness axiom to prefer."),
            ("Value creation vs. value claiming",
             "Two independent axes. <b>Creation</b> is whether the pie was made "
             "as large as possible; <b>claiming</b> is which share you took. A "
             "model can be excellent at one and terrible at the other, and "
             "policymakers should care about the difference."),
            ("Fixed-pie bias",
             "The assumption that whatever helps the other side must hurt you. "
             "The classic integrative-bargaining error, and the reason the "
             "compatible issue exists in the design."),
            ("Surplus share",
             "A side&rsquo;s share of the total gain over walk-away values. "
             "Normalised by BATNA, so it is comparable across seats even though "
             "the two sides hold different schedules."),
        ]),
    ]
    secs.append(_sec("Terms · negotiation", "".join(body)))

    # -- 6. evaluation glossary ---------------------------------------------
    body = [
        "<h2>Terms: evaluation</h2>",
        _gloss([
            ("Ablation",
             "Removing one component to see how much it was contributing. The "
             "no-communication arm ablates dialogue: if scores hold up without "
             "it, the benchmark was not measuring negotiation."),
            ("Frame ablation / framing tax",
             "Running one payoff structure under several narrative skins and "
             "measuring the performance gap. The <b>framing tax</b> is "
             "efficiency under abstract labels minus efficiency under "
             "politically salient ones &mdash; how much competence political "
             "salience costs on a structure the model provably can solve."),
            ("Null control",
             "A participant that <i>cannot</i> exhibit the effect, used to "
             "prove the apparatus does not manufacture it. The offline mock "
             "ignores prompt content, so it must show exactly zero framing tax. "
             "Any deviation would mean the harness leaks an artifact."),
            ("Control condition",
             "The solved-game battery. Its job is to establish whether a model "
             "can solve a structure <i>at all</i> in the abstract. Only then "
             "does failure on the same structure under political framing say "
             "something about framing rather than about capability."),
            ("Blocking factor / paired design",
             "Holding a nuisance variable fixed within each comparison so it "
             "cancels. Instance is the blocking factor here: the framing "
             "difference is taken inside each drawn payoff structure before "
             "averaging, so instance difficulty cannot inflate the variance."),
            ("Reject sampling",
             "Draw a candidate, test it against a specification, discard it if "
             "it fails, repeat. Used to generate instances: the structural "
             "validator is the acceptance test, so every emitted instance is "
             "well-posed by construction."),
            ("Contamination",
             "When a model has effectively seen the answers in training. "
             "Historical scenarios are badly contaminated &mdash; every model "
             "knows how they turned out. Synthetic payoffs cannot be, which is "
             "why the answer key here is uncontaminated even where the framing "
             "labels describe real disputes."),
            ("Self-play",
             "One model taking both seats. Used in the framing arm because it "
             "holds the opponent constant, so the only variable is the framing. "
             "The cost is that it says nothing about performance against a "
             "<i>different</i> opponent &mdash; which is what the head-to-head "
             "arm is for."),
            ("Seat assignment",
             "Which structural role a model plays. Every cross-lab pairing runs "
             "in both, so no result can be an artifact of which side of the "
             "table a model happened to sit on."),
            ("Seed",
             "The number fixing all random choices in one run &mdash; who "
             "speaks first, who closes. Re-running with the same seed "
             "reproduces the same setup, so variation across seeds measures "
             "genuine variability rather than hidden state."),
            ("Instance",
             "One drawn payoff structure. Seeds vary the conversation; "
             "instances vary the game. Reporting across instances is what lets "
             "a finding generalise beyond the numbers one author happened to "
             "write."),
            ("Hard error",
             "A failure needing no interpretation: accepting a deal worse than "
             "walking away, or collapsing talks when a bargaining range "
             "existed. Both are arithmetic on the private schedules &mdash; no "
             "rubric, no judge, nothing to disagree about."),
            ("LLM-as-judge",
             "Using a language model to score outputs. Quarantined here to two "
             "measures that genuinely cannot be derived from the final package "
             "&mdash; misrepresentation and coercion &mdash; and its verdicts "
             "are checked against the true schedules, with any finding lacking "
             "a verbatim supporting quote discarded."),
        ]),
        '<p class="note">Every headline metric on this site is arithmetic over '
        "the private point schedules. No language model grades them.</p>",
    ]
    secs.append(_sec("Terms · evaluation", "".join(body)))

    # -- 7. limitations -----------------------------------------------------
    body = [
        "<h2>Limitations</h2>",
        '<p class="lede">What this eval does not establish. A known weakness '
        "that goes unlisted is worse than one nobody noticed, because the "
        "omission reads as a claim.</p>",

        "<h3>The case design</h3>",
        _gloss([
            ("Schedules are authored; the ordinal structure was tested and then "
             "corrected",
             "Cardinal magnitudes and walk-away levels remain authored, and "
             "always will be. The ordinal structure was checked against 43 "
             "primary documents (see Evidence): <b>nine of twelve cells "
             "confirmed, two partial, one contradicted</b>, and the case files "
             "were rewritten to follow the record where they disagreed. Single "
             "coder, so no reliability statistics. No expert elicitation has "
             "been done."),
            ("The corrected log-roll rests on weaker evidence than the design it "
             "replaced implies",
             "Membership is Tier A &mdash; export controls are traded against "
             "each other, and the July 2025 exchange is documented. "
             "<b>Orientation is only Tier B.</b> That exchange reversed a "
             "six-week-old escalation, so it is equally readable as mutual "
             "de-escalation rather than a trade, and Beijing&rsquo;s minerals "
             "restriction may have been temporary by design. The intensity "
             "ordering now in the case file is the better-supported of two "
             "readings, not a demonstrated fact."),
            ("The two log-roll arms are not symmetric, and a static schedule "
             "cannot say so",
             "US semiconductor leverage is durable; PRC minerals leverage decays "
             "with use, because each use accelerates diversification, and US "
             "buffers already run months to a year. The case prices both arms at "
             "a fixed point in time. Modelling the decay would need a repeated "
             "game, which this design is not."),
            ("The seats never saw each other's schedules &mdash; but they told "
             "each other anyway",
             "Audited two ways (<code>research/audit_leakage.py</code>). The "
             "harness is clean: every point line in every role sheet, across "
             "both cases, four framings and both seats, carries only that "
             "seat's own value. And no side ever cited its counterpart's "
             "walk-away before that counterpart disclosed it &mdash; <b>zero "
             "pre-disclosure citations across 204 transcripts</b>. What the "
             "audit did find is that <b>both sides volunteer their reservation "
             "value in 75% of negotiations</b>. That is permitted &mdash; the "
             "rules say the schedule need not be revealed and may not be "
             "shown, and none was shown &mdash; but it makes finding the "
             "bargaining zone materially easier than the design assumes. Read "
             "the impasse rate with that in mind: it is not the difficulty of "
             "an opaque problem, it is the difficulty of a problem the players "
             "have largely made transparent to each other. Notably, mutual "
             "disclosure does not help &mdash; negotiations where both sides "
             "disclosed reached agreement 58% of the time against 64% where "
             "neither did."),
            ("Demoting Taiwan is a judgement about tradeability, not about value",
             "The evidence that arms sales sit below the Anti-Secession Law&rsquo;s "
             "triggers, carry no USCC recommendation, and did not arise at Busan "
             "supports treating them as a <i>low-range side issue in a "
             "negotiation</i>. It does not support any claim that Beijing or "
             "Washington cares little about Taiwan. A red line is not a cheap "
             "issue; it is an issue that is not on the table."),
            ("Fidelity and instrument quality pull apart here",
             "Applying the sourced findings narrows the in-ZOPA joint spread "
             "from 75 points to 31 and nearly doubles the Pareto frontier: the "
             "evidence-faithful case is <i>more zero-sum</i>, and so a worse "
             "vehicle for measuring integrative bargaining. This case is a "
             "negotiation instrument calibrated for integrative structure that "
             "uses US&ndash;China issues as a salience frame. It is not a model "
             "of US&ndash;China relations."),
            ("One seat, two actors",
             "The design gives the United States a single point schedule. The "
             "record does not. The USCC mentions export controls 223 times; the "
             "executive&rsquo;s own National Security Strategy mentions them "
             "once, and that once is an offer to allies. This project routes "
             "Congress through the walk-away value, which the split exposes as a "
             "real simplification."),
            ("Tariffs are modelled as symmetric; they are not",
             "The case treats tariffs as a pure transfer with equal range on "
             "both sides. Standing levels are 47.5% against China and 31.9% "
             "against the United States, and the US Supreme Court struck down "
             "many of the 2025 tariffs in February 2026 &mdash; a legal ceiling "
             "the design does not represent."),
            ("Both cases are bilateral; the situation is not",
             "RAND&rsquo;s gray-zone exercise found Taiwan rating sovereignty "
             "challenges as more threatening than Washington did, and being "
             "&ldquo;disappointed by the lack of specificity&rdquo; in US "
             "promises of support. Neither case models a third party whose "
             "preferences diverge from either seat&rsquo;s."),
            ("Four claims in this project have been retracted",
             "An inverted log-roll, a claim that Washington would not trade "
             "Taiwan arms, a claim that Beijing takes no material action on "
             "them, and a characterisation of a CFR analysis that said the "
             "opposite of what was attributed to it. Each was caught by reading "
             "further. They are listed rather than quietly corrected because the "
             "rate at which a method catches its own errors is evidence about "
             "the method."),
            ("Real packages exclude these issues",
             "Neither foundational instrument puts them on one table. The Phase "
             "One agreement contains zero mentions of export controls, Taiwan or "
             "fentanyl; the Section 301 report mentions Taiwan once in 215 "
             "pages. Real packages get built from trade, IP and market access, "
             "while export controls and Taiwan run through unilateral "
             "instruments with informal linkage. Putting all six on one table is "
             "what makes a package deal possible, and is a departure from the "
             "record."),
            ("Issue-to-role assignment is unvalidated",
             "That fentanyl enforcement is genuinely <i>compatible</i>, or that "
             "the log-roll runs export controls against arms sales in that "
             "orientation, is asserted rather than shown. These are the two "
             "claims the integrative metrics most depend on."),
            ("Single author, no second coder",
             "No inter-coder reliability statistics exist because there is only "
             "one coder. Every design judgment shares a single point of failure."),
            ("Sampling varies magnitudes, not structure",
             "Instance sampling shows results do not depend on the particular "
             "numbers. It cannot show they would survive a <i>different</i> "
             "structural template, because every instance inherits the same one."),
        ]),

        "<h3>The model of negotiation</h3>",
        _gloss([
            ("Two parties only",
             "Real diplomacy has coalitions, allies and domestic veto players. "
             "The two-party restriction is what makes the outcome space small "
             "enough to enumerate exactly &mdash; a deliberate trade of realism "
             "for an exact answer key, but a trade nonetheless."),
            ("No clock, and no cost of delay",
             "Rounds are fixed and nothing worsens while the parties talk. The "
             "crisis case carries crisis <i>framing</i> but not crisis "
             "<i>dynamics</i>: there is no escalation during the negotiation "
             "itself, which is much of what makes real crisis bargaining hard."),
            ("Walk-away values are handed over, not inferred",
             "Each side is told its reservation value in points. Real "
             "negotiators are uncertain about their own and must estimate the "
             "other's. This makes below-BATNA acceptance a clean error to "
             "measure, at the cost of removing a genuine part of the problem."),
            ("Own preferences are complete and precise",
             "A model reads its schedule and knows exactly what it wants. Real "
             "governments hold contested, imprecise internal preferences that "
             "shift during a negotiation."),
        ]),

        "<h3>The measurement</h3>",
        _gloss([
            ("No human baseline",
             "Nobody knows what expert human negotiators score on these cases, "
             "so an efficiency figure has no human reference point. "
             "&ldquo;Better than the naive baseline&rdquo; is established; "
             "&ldquo;better or worse than a person&rdquo; is not."),
            ("The judge is unvalidated against human coders",
             "Quote-verification stops the judge inventing evidence, but its "
             "misrepresentation and coercion calls have never been checked "
             "against human judgement. Those two measures are weaker than the "
             "arithmetic ones and should be read as indicative."),
            ("Prompt-format sensitivity is untested",
             "Results may depend on the specific protocol wording, the JSON "
             "commitment format, or the round budget. No ablation over prompt "
             "scaffolding has been run, so some portion of any measured "
             "difference could be format artefact."),
            ("Temperature and round budget are fixed, not swept",
             "Both are held constant and reported rather than varied. That "
             "keeps comparisons clean but leaves their influence unmeasured."),
        ]),

        "<h3>The framing manipulation</h3>",
        _gloss([
            ("The salient frame injects knowledge, not only salience",
             "Naming Taiwan and export controls does more than raise political "
             "stakes &mdash; it also supplies real-world knowledge the abstract "
             "frame withholds. A model may do worse under salient framing "
             "because it is reasoning about remembered facts rather than "
             "because salience degrades reasoning. The neutral-real frame "
             "partly isolates this, and the solved-game control bounds it, but "
             "neither separates the two cleanly."),
            ("The Mandarin frame is not native-verified",
             "The translation preserves the point values exactly and carries no "
             "English boilerplate, both checked automatically. Its idiomatic "
             "quality and register have not been reviewed by a native speaker, "
             "so a measured English/Mandarin gap could partly reflect "
             "translation quality rather than prompt language."),
        ]),

        '<p class="note">This list is maintained alongside the design. A '
        "limitation that later research resolves is struck from it; a "
        "limitation that research reveals is added.</p>",
    ]
    secs.append(_sec("Limitations", "".join(body)))

    # -- 8. bibliography ----------------------------------------------------
    body = [
        '<h2>Bibliography</h2>',
        '<p class="lede">Every source consulted, whether or not it survived into a finding &mdash; including the ones that <b>falsified</b> a design assumption, which are the most informative entries here. Each was downloaded and read in full; the local corpus filename is given so any quotation on this page can be checked against the text it came from.</p>',
        '<p class="bibhead">PRC government and party</p><ul class="bib">',
        '<li><b>Xi Jinping</b> &middot; 16 Oct 2022<br><a href="https://www.12371.cn/2022/10/25/ARTI1666705047474465.shtml">Report to the 20th National Congress of the CPC (二十大报告)</a><br><span class="f">pc20_zh.txt</span></li>',
        '<li><b>State Council TAO / SCIO</b> &middot; 10 Aug 2022<br><a href="https://bw.china-embassy.gov.cn/sgxw/202208/t20220810_10740353.htm">《台湾问题与新时代中国统一事业》 white paper</a><br><span class="f">taiwan_wp_zh.txt</span></li>',
        '<li><b>National People&rsquo;s Congress</b> &middot; 14 Mar 2005<br><a href="https://zh.wikisource.org/wiki/%E5%8F%8D%E5%88%86%E8%A3%82%E5%9C%8B%E5%AE%B6%E6%B3%95">反分裂国家法 Anti-Secession Law</a><br><span class="f">prc_anti_secession_law.txt</span></li>',
        '<li><b>National People&rsquo;s Congress</b> &middot; 17 Oct 2020<br><a href="https://zh.wikisource.org/wiki/%E4%B8%AD%E8%8F%AF%E4%BA%BA%E6%B0%91%E5%85%B1%E5%92%8C%E5%9C%8B%E5%87%BA%E5%8F%A3%E7%AE%A1%E5%88%B6%E6%B3%95">中华人民共和国出口管制法 Export Control Law</a><br><span class="f">prc_export_control_law.txt</span></li>',
        '<li><b>MOFCOM 商务部</b> &middot; 12 Oct 2025<br><a href="https://www.gov.cn/zhengce/202510/content_7044134.htm">Spokesperson Q&amp;A on recent trade policy measures</a><br><span class="f">mofcom_2410.txt</span></li>',
        '<li><b>MOFCOM 商务部</b> &middot; 3 Dec 2024<br><a href="http://exportcontrol.mofcom.gov.cn/article/gndt/202412/1071.html">Spokesperson on dual-use export controls to the US</a><br><span class="f">mofcom_dec2024.txt</span></li>',
        '<li><b>MFA 外交部</b> &middot; 22 Dec 2024<br><a href="https://www.mfa.gov.cn/eng/xw/fyrbt/202412/t20241222_11514772.html">Spokesperson&rsquo;s remarks on US military assistance and arms sales to Taiwan</a><br><span class="f">mofa_arms_sales_dec2024.txt</span></li>',
        '</ul>',
        '<p class="bibhead">US government</p><ul class="bib">',
        '<li><b>USCC</b> &middot; Nov 2025<br><a href="https://www.uscc.gov/annual-report/2025-annual-report-congress">2025 Report to Congress (745 pp)</a><br><span class="f">uscc_full.txt</span></li>',
        '<li><b>USCC</b> &middot; Nov 2025<br><a href="https://www.uscc.gov/sites/default/files/2025-11/2025_Executive_Summary.pdf">2025 Report to Congress &mdash; Executive Summary and Recommendations</a><br><span class="f">uscc_exec.txt</span></li>',
        '<li><b>USTR</b> &middot; 15 Jan 2020<br><a href="https://ustr.gov/countries-regions/china-mongolia-taiwan/peoples-republic-china/phase-one-trade-agreement/text">Economic and Trade Agreement between the United States and the PRC (&lsquo;Phase One&rsquo;)</a><br><span class="f">phase_one.txt</span></li>',
        '<li><b>USTR</b> &middot; 215 pp<br><a href="https://ustr.gov/sites/default/files/Section%20301%20FINAL.PDF">Section 301 Report on China&rsquo;s Acts, Policies and Practices Related to Technology Transfer</a><br><span class="f">ustr_301_report.txt</span></li>',
        '<li><b>CRS R48642</b><br><a href="https://www.everycrsreport.com/reports/R48642.html">U.S. Export Controls and China: Advanced Semiconductors</a><br><span class="f">crs_export_controls_semi.txt</span></li>',
        '<li><b>CRS IF12125</b><br><a href="https://www.everycrsreport.com/reports/IF12125.html">Section 301 and China: The U.S.-China Phase One Trade Deal</a><br><span class="f">crs_phase_one.txt</span></li>',
        '<li><b>CRS IF11665</b><br><a href="https://www.everycrsreport.com/reports/IF11665.html">President Reagan&rsquo;s Six Assurances to Taiwan</a><br><span class="f">crs_taiwan_arms.txt</span></li>',
        '<li><b>State Department</b> &middot; 13 Dec 2024<br><a href="https://2021-2025.state.gov/amendment-and-extension-of-the-u-s-prc-science-and-technology-agreement-sta/">Amendment and Extension of the U.S.-PRC Science and Technology Agreement</a><br><span class="f">&mdash;</span></li>',
        '</ul>',
        '<p class="bibhead">Think tanks and analysis</p><ul class="bib">',
        '<li><b>CFR</b> &middot; 12 Dec 2024<br><a href="https://www.cfr.org/articles/unpacking-chinas-four-red-lines-and-its-warning-trump">Unpacking China&rsquo;s &lsquo;Four Red Lines&rsquo; and Its Warning to Trump</a><br><span class="f">cfr_red_lines.txt</span></li>',
        '<li><b>CSIS ChinaPower</b><br><a href="https://features.csis.org/chinapower/china-quarantine-taiwan/">How China Could Quarantine Taiwan</a><br><span class="f">csis_quarantine.txt</span></li>',
        '<li><b>CSIS</b><br><a href="https://www.csis.org/analysis/lights-out-wargaming-blockade-taiwan">Lights Out? Wargaming a Blockade of Taiwan &mdash; 26 iterations</a><br><span class="f">csis_lights_out.txt</span></li>',
        '<li><b>CSIS</b><br><a href="https://www.csis.org/analysis/us-china-science-and-technology-cooperation-agreement-not-yet-obsolete">The U.S.-China Science and Technology Cooperation Agreement Is Not Yet Obsolete</a><br><span class="f">csis_sta.txt</span></li>',
        '<li><b>Brookings</b> &middot; Oct 2025<br><a href="https://www.brookings.edu/articles/what-happened-when-trump-met-xi/">What happened when Trump met Xi? (Busan summit)</a><br><span class="f">brookings_busan.txt</span></li>',
        '<li><b>Brookings</b><br><a href="https://www.brookings.edu/articles/us-china-relations-and-fentanyl-and-precursor-cooperation-in-2024/">U.S.-China relations and fentanyl and precursor cooperation in 2024</a><br><span class="f">brookings_fentanyl.txt</span></li>',
        '<li><b>Brookings</b><br><a href="https://www.brookings.edu/articles/breaking-down-trumps-2025-national-security-strategy/">Breaking down Trump&rsquo;s 2025 National Security Strategy</a><br><span class="f">brookings_nss.txt</span></li>',
        '<li><b>Forum on the Arms Trade</b><br><a href="https://www.forumarmstrade.org/ustaiwan.html">US Arms Sales to Taiwan &mdash; running register of FMS notifications</a><br><span class="f">forum_arms_trade.txt</span></li>',
        '</ul>',
        '<p class="bibhead">Triangulation layer (Tier 2)</p><ul class="bib"><li><b>The White House</b> &middot; Nov 2025<br><a href="https://www.whitehouse.gov/wp-content/uploads/2025/12/2025-National-Security-Strategy.pdf">National Security Strategy (33 pp)</a><br><span class="f">nss_2025.txt</span></li><li><b>RAND RRA1279-1</b><br><a href="https://www.rand.org/pubs/research_reports/RRA1279-1.html">Implications of a Coercive Quarantine of Taiwan by the PRC (38 pp)</a><br><span class="f">rand_quarantine.txt</span></li><li><b>RAND CFA2065-1</b><br><a href="https://www.rand.org/pubs/conf_proceedings/CFA2065-1.html">Simulating Chinese Gray Zone Coercion of Taiwan (45 pp)</a><br><span class="f">rand_grayzone.txt</span></li><li><b>PIIE</b> &middot; 2026<br><a href="https://www.piie.com/blogs/realtime-economics/2026/trump-china-trade-wars-five-takeaways-us-imports-2025">The Trump-China trade wars: five takeaways from US imports in 2025</a><br><span class="f">piie_2025_imports.txt</span></li><li><b>PIIE</b><br><a href="https://www.piie.com/sites/default/files/documents/piie-chart-us-china-war-up-to-date.pdf">US-China trade war tariffs: an up-to-date chart</a><br><span class="f">piie_tariff_chart.txt</span></li><li><b>CSIS</b><br><a href="https://www.csis.org/analysis/china-imposes-its-most-stringent-critical-minerals-export-restrictions-yet-amidst">China Imposes Its Most Stringent Critical Minerals Export Restrictions Yet</a><br><span class="f">csis_critical_minerals.txt</span></li><li><b>CRS R47982</b><br><a href="https://www.everycrsreport.com/reports/R47982.html">Critical Mineral Resources: National Policy and Critical Minerals List</a><br><span class="f">crs_china_rare_earth.txt</span></li><li><b>CRS IF11627</b><br><a href="https://www.everycrsreport.com/reports/IF11627.html">U.S. Export Controls and China</a><br><span class="f">crs_us_export_controls_china.txt</span></li><li><b>CRS</b><br><a href="https://www.everycrsreport.com/reports/IF10275.html">Taiwan: Background and U.S. Relations</a><br><span class="f">crs_taiwan_defense.txt</span></li><li><b>Foreign Affairs</b><br><a href="https://www.foreignaffairs.com/taiwan/taiwan-not-sale">Taiwan Is Not for Sale</a><br><span class="f">fa_taiwan_not_for_sale.txt</span></li><li><b>CNAS</b><br><a href="https://www.cnas.org/publications/reports/the-future-of-us-export-controls">The Future of U.S. Export Controls</a><br><span class="f">cnas_export_controls.txt</span></li><li><b>House Select Committee on the CCP</b><br><a href="https://selectcommitteeontheccp.house.gov/media/press-releases">Press releases and statements</a><br><span class="f">house_ccp_committee.txt</span></li></ul>',
        '<p class="bibhead">Open nomination &mdash; sources sought to falsify the findings (Tier 3)</p><ul class="bib"><li><b>War on the Rocks</b> &middot; 5 Jan 2026<br><a href="https://warontherocks.com/the-burn-and-the-choke-why-semiconductor-controls-will-outlast-chinas-rare-earth-weapon/">Alvin Camba, &lsquo;The Burn and the Choke: Why Semiconductor Controls Will Outlast China&rsquo;s Rare Earth Weapon&rsquo;</a><br><span class="f">wotr_burn_choke.txt</span></li><li><b>Resources for the Future</b><br><a href="https://www.rff.org/publications/issue-briefs/the-strategic-game-of-rare-earths-why-china-may-only-be-in-favor-of-temporary-export-restrictions/">The Strategic Game of Rare Earths: Why China May Only Be in Favor of Temporary Export Restrictions</a><br><span class="f">rff_rare_earths.txt</span></li><li><b>Foreign Policy</b> &middot; 24 Aug 2026<br><a href="https://foreignpolicy.com/2026/08/24/rare-earths-china-japan-trade-united-states-trump-supply-chain/">China&rsquo;s Rare-Earth Trade Leverage Looms Over Japan, United States</a><br><span class="f">fp_rare_earth_leverage.txt</span></li><li><b>Global Trade Alert</b> &middot; Jul 2025<br><a href="https://globaltradealert.org/state-act/92541-united-states-of-america-commerce-department-lifts-eda-software-export-restrictions-to-china">Commerce Department lifts EDA software export restrictions to China</a><br><span class="f">gta_eda_lift.txt</span></li><li><b>Global Times</b> &middot; Jul 2025<br><a href="https://www.globaltimes.cn/page/202507/1337536.shtml">Major EDA suppliers confirm US lifts chip design software curbs on China</a><br><span class="f">gt_eda_lift.txt</span></li></ul>',
        '<p class="note"><b>Not retrieved.</b> The Anti-Foreign Sanctions Law (反外国制裁法) could not be obtained from an authoritative host and is <i>not</i> cited anywhere on this site. The National Defense Strategy was read through analysis rather than in the original. Four Tier 2 targets failed retrieval and were dropped rather than cited from summary: Carnegie and MERICS returned 404s, Asia Society and Reuters bot challenges. One CRS request returned a Postal Service report under the expected number — caught by the conversion audit before it could be cited. Every gap is recorded rather than papered over.</p>',
    ]
    secs.append(_sec("Bibliography", "".join(body)))
    return "".join(secs)


def case_set(case: Case, agg: dict, detail: dict, title: str, active: bool) -> str:
    """One case's whole world: its model switcher and all of its views."""
    an = analyze(case)
    models = agg["models"]
    is_mock = bool(models) and all(
        m == "mock" or (m in REGISTRY and REGISTRY[m].provider == "mock")
        for m in models)

    tabs = ['<button data-view="summary" aria-selected="true">Summary</button>']
    views = [f'<div class="view" data-view="summary">'
             f"{summary_view(agg, case, an, title, is_mock)}</div>"]

    # Role sheets sit next to the summary: they are the answer key, and you
    # want them before the model results, not after.
    for role in case.roles:
        vid = "r-" + role.lower()
        tabs.append(f'<button data-view="{vid}" aria-selected="false">'
                    f"{_esc(role_label(case, role))}</button>")
        views.append(f'<div class="view" data-view="{vid}" hidden>'
                     f"{role_view(case, role, an)}</div>")

    for m in models:
        vid = "m-" + re.sub(r"[^a-z0-9]+", "-", m.lower())
        tabs.append(f'<button data-view="{vid}" aria-selected="false">'
                    f"{_esc(m)}</button>")
        views.append(f'<div class="view" data-view="{vid}" hidden>'
                     f"{model_view(m, agg, detail, an)}</div>")

    tabs.append('<button data-view="appendix" aria-selected="false">'
                "Appendix: Methodology</button>")
    views.append('<div class="view" data-view="appendix" hidden>'
                 f"{appendix_view(case, an)}</div>")

    return (
        f'<div class="caseset" data-case="{_esc(case.id)}"'
        f'{"" if active else " hidden"}>'
        f'<nav class="switch" role="tablist">{"".join(tabs)}</nav>'
        f'<div class="viewport">{"".join(views)}</div>'
        "</div>"
    )


def case_menu(bundles: list[dict]) -> str:
    """Vertical case selector, top-left. Collapsed to its current label."""
    items = []
    for i, b in enumerate(bundles):
        case, agg = b["case"], b["agg"]
        n = agg["n_negotiations"]
        sub = (f"{n} run{'s' if n != 1 else ''}" if n
               else "no runs yet")
        items.append(
            f'<button data-case="{_esc(case.id)}" '
            f'aria-selected="{"true" if i == 0 else "false"}">'
            f'<b>{_esc(case.title)}</b><span>{_esc(sub)}</span></button>'
        )
    first = bundles[0]["case"].title if bundles else "—"
    return (
        '<details class="cases">'
        f'<summary><span class="ck">Case</span>'
        f'<span class="cv">{_esc(first)}</span>'
        '<svg viewBox="0 0 24 24" aria-hidden="true">'
        '<path d="M6 9l6 6 6-6" stroke-linecap="round" stroke-linejoin="round"/>'
        "</svg></summary>"
        f'<div class="caselist">{"".join(items)}</div>'
        "</details>"
    )


def build_html(bundles: list[dict], title: str) -> str:
    sets = "".join(
        case_set(b["case"], b["agg"], b["detail"], title, i == 0)
        for i, b in enumerate(bundles)
    )
    return (
        '<div class="viz-root">'
        f"{case_menu(bundles)}"
        '<div class="progress" aria-hidden="true"></div>'
        f"{sets}"
        f'<button class="nextbtn" aria-label="Next finding">{ARROW}</button>'
        "</div>"
    )


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Build the Track II report")
    # A directory loads every .jsonl and .jsonl.gz under it, so the default
    # picks up the committed mock plus whatever live runs exist.
    ap.add_argument("results", nargs="?", default=str(ROOT / "results"))
    ap.add_argument("-o", "--out", default=str(ROOT / "site" / "index.html"))
    ap.add_argument("--case", action="append", default=None,
                    help="case YAML; repeatable. Defaults to every case in cases/.")
    ap.add_argument("--title", default="Track II — an eval for the situation room")
    ap.add_argument("--fragment", action="store_true",
                    help="emit body fragment only (for publishing as an artifact)")
    args = ap.parse_args(argv)

    path = Path(args.results)
    if not path.exists():
        print(f"no results at {path}")
        return 1
    if path.is_dir() and not any(path.rglob("*.jsonl*")):
        print(f"no .jsonl or .jsonl.gz files in {path}")
        return 1

    recs = load(path)

    # Mock and live records must not share a chart. The mock exists so the site
    # builds with no API keys; once real runs exist it is a distraction at best
    # and a misreading at worst, so live wins whenever both are present.
    live = [r for r in recs if r.get("live") is True]
    if live:
        dropped = len(recs) - len(live)
        recs = live
        if dropped:
            print(f"using {len(recs)} live records; ignoring {dropped} mock/"
                  f"unattributed records (set `live` provenance to include them)")
    else:
        print(f"no live records found — reporting {len(recs)} mock records")

    # Every case the repo defines, unless told otherwise. Cases with no runs yet
    # still appear -- their structure and computed optimum are worth showing.
    if args.case:
        case_paths = [Path(c) for c in args.case]
    else:
        # The Quarantine leads. It is the better-evidenced of the two: CSIS and
        # RAND independently corroborate the premise, the inspection axis, the
        # low walk-away values and the direction of their asymmetry, where the
        # package deal carries a demoted side issue and a re-seated log-roll.
        LEAD = ["quarantine", "package_deal"]
        found = [p for p in (ROOT / "cases").glob("*.yaml") if p.stem != "solved_games"]
        case_paths = sorted(
            found, key=lambda p: (LEAD.index(p.stem) if p.stem in LEAD else len(LEAD),
                                  p.stem)
        )
    cases = [Case.load(p) for p in case_paths]

    # The solved-game battery is case-independent: it is the control for any
    # case's framing claim, so it rides along with each of them.
    battery = [r for r in recs if r.get("kind") == "solved_game"]

    bundles = []
    for case in cases:
        # Instances drawn from a template share its family, so they pool into
        # one case here instead of fragmenting the site into a dozen entries.
        sub = [r for r in recs
               if r.get("kind") == "negotiation"
               and (r.get("case_family") or r.get("case_id")) == case.family]
        bundles.append({
            "case": case,
            "agg": aggregate(sub + battery),
            "detail": per_model(sub + battery),
        })
    # Populated cases first so the site opens on something with data, but the
    # LEAD order decides among them -- otherwise whichever case happened to get
    # more runs would take the front page.
    lead = {p.stem: n for n, p in enumerate(case_paths)}
    bundles.sort(key=lambda b: (b["agg"]["n_negotiations"] == 0,
                                lead.get(b["case"].id.replace("_v2","").replace("_v1",""), 99),
                                lead.get(b["case"].family, 99)))
    body = build_html(bundles, args.title)

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    page = (f"<title>{_esc(args.title)}</title>\n<style>{CSS}</style>\n{body}\n"
            f"<script>{JS}</script>\n")
    if args.fragment:
        out.write_text(page)
    else:
        out.write_text(
            '<!doctype html>\n<html lang="en"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1">'
            f"<title>{_esc(args.title)}</title><style>{CSS}</style></head>"
            f"<body>{body}<script>{JS}</script></body></html>\n")
    for b in bundles:
        print(f"  {b['case'].title:<22} {b['agg']['n_negotiations']:>4} negotiations"
              f"  {len(b['agg']['models'])} models")
    print(f"wrote {out}  ({len(bundles)} cases, "
          f"{sum(b['agg']['n_negotiations'] for b in bundles)} negotiations)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
