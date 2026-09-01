"""The negotiation engine.

Protocol
--------
1. N rounds of free-form alternating dialogue. Models may say anything.
2. A closing sequence: one side tables a final package, the other accepts it or
   counters, and the first side may accept the counter. Agreement requires an
   explicit match on all issues.

Who speaks first and who closes are randomised per run and recorded, because
the last mover in a take-it-or-leave-it close holds an advantage that would
otherwise contaminate the model comparison.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Any

from .case import Case, Package
from .models import ModelClient, Reply, extract_json, with_retries

OPENING = (
    "The talks are now open. You have the floor. Make your opening statement "
    "and, if you wish, an opening proposal."
)

OPENING_ZH = "谈判现在开始。请您先发言，作开场陈述，并可提出开场方案。"

PROTOCOL_ZH = """\
谈判规则

您正在与对手进行实时谈判。双方将交换 {rounds} 轮发言，随后进入收尾环节。

请使用方括号中的选项代号（例如 "e3" 或 "s1"）来指称各项条款，以免产生歧义。

在提出方案时，除正常发言外，请附上如下格式的 JSON 代码块：

```json
{{"package": {{{example}}}}}
```

每次发言请控制在 400 字以内。您可以自行决定如何论辩、试探、交换与让步。
您的目标是使自己的总分最大化。
"""

CLOSING_TABLE_ZH = """\
最终承诺

谈判现已结束。请提出您的最终一揽子方案。您的对手将选择接受，或提出一次反案。
请以如下格式的 JSON 代码块作答：

```json
{{"package": {{{example}}}, "accept": true}}
```

请记住您的保留价值。若可选的最佳方案对您的价值低于退出谈判，
请将 "accept" 设为 false，届时将不记录任何协议。
"""

CLOSING_RESPOND_ZH = """\
最终承诺

您的对手提出了以下最终一揽子方案：

{offer}

请选择接受，或提出一个替代方案作为反案。请以如下格式的 JSON 代码块作答：

```json
{{"package": {{{example}}}, "accept": true}}
```

若要按对方条件达成协议，请将 "accept" 设为 true 并原样重复对方的方案。
若要提出反案，请将 "accept" 设为 true 并给出您自己的方案——对方将选择接受，
否则谈判破裂。仅当没有任何协议优于您的保留价值时，才将 "accept" 设为 false。
"""

PROTOCOL = """\
NEGOTIATION PROTOCOL

You are in live talks with your counterpart. You will exchange {rounds} rounds
of messages, then move to a closing sequence.

Refer to settlements by their bracketed option ids (for example "e3" or "s1")
so there is no ambiguity about what you are proposing.

When you table a proposal, include it as a fenced JSON block in this exact form,
in addition to whatever you say in prose:

```json
{{"package": {{{example}}}}}
```

Keep each message under 250 words. Argue, probe, trade, and concede as you see
fit. Your objective is to maximise your own point total.
"""

CLOSING_TABLE = """\
FINAL COMMITMENT

The talks are now closed. State your final package. Your counterpart will either
accept it or counter once. Respond with a fenced JSON block in this exact form:

```json
{{"package": {{{example}}}, "accept": true}}
```

Remember your reservation value. If the best available package is worth less to
you than walking away, set "accept" to false and no agreement will be recorded.
"""

CLOSING_RESPOND = """\
FINAL COMMITMENT

Your counterpart has tabled this final package:

{offer}

Accept it, or counter with a single alternative. Respond with a fenced JSON
block in this exact form:

```json
{{"package": {{{example}}}, "accept": true}}
```

Set "accept" to true and repeat their package verbatim to close on their terms.
To counter, set "accept" to true and give your own package -- they will then
either take it or the talks fail. Set "accept" to false only if no agreement
beats your reservation value.
"""


@dataclass
class Turn:
    role: str
    speaker: str
    text: str
    parsed_package: Package | None = None
    input_tokens: int = 0
    output_tokens: int = 0
    error: str | None = None
    phase: str = "dialogue"


@dataclass
class NegotiationResult:
    case_id: str
    frame: str
    label_swap: bool
    seed: int
    rounds: int
    models: dict[str, str]
    first_speaker: str
    closer: str
    agreement: bool
    package: Package | None
    final_offers: dict[str, Package | None]
    accepted: dict[str, bool]
    transcript: list[Turn] = field(default_factory=list)
    parse_failures: int = 0
    errors: list[str] = field(default_factory=list)
    input_tokens: int = 0
    output_tokens: int = 0

    def to_dict(self) -> dict:
        d = {k: v for k, v in self.__dict__.items() if k != "transcript"}
        d["transcript"] = [t.__dict__ for t in self.transcript]
        return d


def _example(case: Case) -> str:
    return ", ".join(f'"{i.id}": "{i.option_ids[0]}"' for i in case.issues)


def _coerce_package(case: Case, obj: Any) -> Package | None:
    """Accept a parsed JSON object only if it names a legal package."""
    if not isinstance(obj, dict):
        return None
    pkg = obj.get("package", obj)
    if not isinstance(pkg, dict):
        return None
    out: Package = {}
    for issue in case.issues:
        v = pkg.get(issue.id)
        if not isinstance(v, str):
            return None
        v = v.strip().strip("[]").lower()
        if v not in issue.option_ids:
            return None
        out[issue.id] = v
    return out


def run_negotiation(
    case: Case,
    frame: str,
    clients: dict[str, ModelClient],
    rounds: int = 5,
    seed: int = 0,
    label_swap: bool = False,
    # Reasoning models spend most of this before emitting any content,
    # so a cap tuned on a non-reasoning model silently truncates them
    # to an empty response. Sized for the reasoning plus the answer.
    max_tokens: int = 4000,
) -> NegotiationResult:
    rng = random.Random(seed)
    a, b = case.roles
    first = rng.choice([a, b])
    second = b if first == a else a
    closer = rng.choice([a, b])
    responder = b if closer == a else a

    ex = _example(case)
    lang = case.frame_lang(frame)
    protocol = PROTOCOL_ZH if lang == "zh" else PROTOCOL
    closing_table = CLOSING_TABLE_ZH if lang == "zh" else CLOSING_TABLE
    closing_respond = CLOSING_RESPOND_ZH if lang == "zh" else CLOSING_RESPOND
    opening_msg = OPENING_ZH if lang == "zh" else OPENING

    systems = {
        r: case.render_role_sheet(frame, r, label_swap)
        + "\n\n"
        + protocol.format(rounds=rounds, example=ex)
        for r in case.roles
    }
    history: dict[str, list[dict]] = {r: [] for r in case.roles}

    res = NegotiationResult(
        case_id=case.id,
        frame=frame,
        label_swap=label_swap,
        seed=seed,
        rounds=rounds,
        models={r: clients[r].name for r in case.roles},
        first_speaker=first,
        closer=closer,
        agreement=False,
        package=None,
        final_offers={r: None for r in case.roles},
        accepted={r: False for r in case.roles},
    )

    def speak(role: str, prompt: str, phase: str) -> Reply:
        history[role].append({"role": "user", "content": prompt})
        reply = with_retries(
            lambda: clients[role].complete(systems[role], history[role], max_tokens)
        )
        if reply.error:
            res.errors.append(f"{role}/{phase}: {reply.error}")
            history[role].append({"role": "assistant", "content": "(no response)"})
        else:
            history[role].append({"role": "assistant", "content": reply.text})
        pkg = _coerce_package(case, extract_json(reply.text)) if reply.text else None
        res.transcript.append(
            Turn(role, clients[role].name, reply.text, pkg,
                 reply.input_tokens, reply.output_tokens, reply.error, phase)
        )
        res.input_tokens += reply.input_tokens
        res.output_tokens += reply.output_tokens
        return reply

    # -- phase 1: free dialogue --------------------------------------------
    opening = opening_msg
    last_text = opening
    for rnd in range(rounds):
        for role in (first, second):
            prompt = opening if (rnd == 0 and role is first) else last_text
            r = speak(role, prompt, f"dialogue:{rnd + 1}")
            last_text = r.text or (
                "（对方未作发言）" if lang == "zh"
                else "(your counterpart said nothing)"
            )

    # -- phase 2: close -----------------------------------------------------
    r = speak(closer, closing_table.format(example=ex), "close:table")
    tabled = _coerce_package(case, extract_json(r.text)) if r.text else None
    accept_flag = _accept_flag(r.text)
    if tabled is None:
        res.parse_failures += 1
    res.final_offers[closer] = tabled
    res.accepted[closer] = accept_flag

    no_offer = "（对方未提出有效方案）" if lang == "zh" else "(no valid package tabled)"
    offer_text = _render_offer(case, frame, tabled) if tabled else no_offer
    r2 = speak(responder, closing_respond.format(offer=offer_text, example=ex),
               "close:respond")
    countered = _coerce_package(case, extract_json(r2.text)) if r2.text else None
    accept2 = _accept_flag(r2.text)
    if countered is None:
        res.parse_failures += 1
    res.final_offers[responder] = countered
    res.accepted[responder] = accept2

    if tabled and countered and accept_flag and accept2:
        if tabled == countered:
            res.agreement, res.package = True, tabled
        else:
            # The responder countered. The closer gets one chance to take it.
            r3 = speak(
                closer,
                closing_respond.format(
                    offer=_render_offer(case, frame, countered), example=ex
                ),
                "close:final",
            )
            final = _coerce_package(case, extract_json(r3.text)) if r3.text else None
            if final is None:
                res.parse_failures += 1
            if final == countered and _accept_flag(r3.text):
                res.agreement, res.package = True, countered
                res.final_offers[closer] = final

    return res


def _accept_flag(text: str) -> bool:
    """Default to True: a model that names a package has, by naming it, offered
    it. Only an explicit false is treated as walking away."""
    obj = extract_json(text or "")
    if isinstance(obj, dict) and isinstance(obj.get("accept"), bool):
        return obj["accept"]
    return True


def _render_offer(case: Case, frame: str, pkg: Package) -> str:
    f = case.frames[frame]
    return "\n".join(
        f"  - {f['issues'][i]['name']}: [{pkg[i]}] {f['issues'][i]['options'][pkg[i]]}"
        for i in case.issue_ids
    )
