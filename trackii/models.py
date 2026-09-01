"""Model adapters.

One interface over Anthropic and any OpenAI-compatible endpoint (we use
OpenRouter for the Chinese models), plus a deterministic mock so the whole
pipeline is testable without API keys or spend.
"""

from __future__ import annotations

import json
import os
import random
import re
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Protocol


@dataclass
class Reply:
    text: str
    input_tokens: int = 0
    output_tokens: int = 0
    error: str | None = None


class ModelClient(Protocol):
    name: str

    def complete(self, system: str, messages: list[dict], max_tokens: int) -> Reply: ...


# ---------------------------------------------------------------------------
# Registry — cheap tiers only, per the eval budget.
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ModelSpec:
    key: str            # short name used in results and reports
    provider: str       # "anthropic" | "openrouter" | "mock"
    model_id: str
    lab: str
    origin: str         # "US" | "CN" — drives the head-to-head analysis


REGISTRY: dict[str, ModelSpec] = {
    m.key: m
    for m in [
        # Cheap tiers only, per the eval budget. OpenRouter slugs move fast --
        # run `python -m trackii.run --list` and check openrouter.ai/models
        # before a live sweep. The Chinese-lab set is chosen to overlap the
        # models ChinaTalk's own Civ V work reports on (DeepSeek, GLM, Kimi,
        # Qwen, MiniMax), so results are comparable to theirs.
        ModelSpec("haiku-4.5", "anthropic", "claude-haiku-4-5-20251001",
                  "Anthropic", "US"),
        # Verified against the live OpenRouter catalogue, 2026-08-31. The
        # original pins were a generation stale and one (qwen3-235b) had been
        # withdrawn entirely -- the API rejected it as "not a valid model ID".
        # The set is chosen by LAB, to overlap ChinaTalk's own Civ V work, and
        # within each lab by cheap tier, to match Haiku 4.5's position rather
        # than its price exactly.
        ModelSpec("deepseek", "openrouter", "deepseek/deepseek-v4-flash-0731",
                  "DeepSeek", "CN"),
        ModelSpec("glm", "openrouter", "z-ai/glm-5.3-flash",
                  "Zhipu", "CN"),
        ModelSpec("kimi", "openrouter", "moonshotai/kimi-k2.5",
                  "Moonshot", "CN"),
        ModelSpec("qwen", "openrouter", "qwen/qwen3.8-flash",
                  "Alibaba", "CN"),
        ModelSpec("minimax", "openrouter", "minimax/minimax-m3",
                  "MiniMax", "CN"),
        ModelSpec("mock", "mock", "mock", "—", "—"),
    ]
}


class AnthropicClient:
    def __init__(self, spec: ModelSpec, temperature: float = 1.0):
        import anthropic

        self.spec = spec
        self.name = spec.key
        self.temperature = temperature
        # Pass the key explicitly when it is set; otherwise let the SDK resolve
        # credentials itself, which picks up ANTHROPIC_AUTH_TOKEN or a profile
        # from `ant auth login`. Hard-requiring the env var meant an already
        # authenticated machine still had to mint and paste a long-lived key.
        key = os.environ.get("ANTHROPIC_API_KEY")
        # Identity-linked keys must name the workspace they act in, or the API
        # rejects the request with a 400 before doing any work. Classic keys do
        # not need this, so the header is only sent when the id is available.
        ws = os.environ.get("ANTHROPIC_WORKSPACE_ID")
        headers = {"anthropic-workspace-id": ws} if ws else None
        self._client = (anthropic.Anthropic(api_key=key, default_headers=headers)
                        if key else anthropic.Anthropic(default_headers=headers))

    # anthropic 1.x removed temperature/top_p/top_k from messages.create; passing
    # temperature raises TypeError before any request is made. Sampling variance
    # across seeds now comes from the API being nondeterministic by default,
    # which is what the seeds were labelling anyway. `applied_temperature`
    # reports what was actually sent so provenance does not overclaim.
    applied_temperature = None

    def complete(self, system: str, messages: list[dict], max_tokens: int = 2000) -> Reply:
        try:
            r = self._client.messages.create(
                model=self.spec.model_id,
                system=system,
                messages=messages,
                max_tokens=max_tokens,
            )
            text = "".join(b.text for b in r.content if b.type == "text")
            return Reply(text, r.usage.input_tokens, r.usage.output_tokens)
        except Exception as e:  # noqa: BLE001 — surfaced as a run-level error
            return Reply("", error=f"{type(e).__name__}: {e}")


class OpenRouterClient:
    def __init__(self, spec: ModelSpec, temperature: float = 1.0):
        from openai import OpenAI

        self.spec = spec
        self.name = spec.key
        self.temperature = temperature
        self._client = OpenAI(
            api_key=os.environ["OPENROUTER_API_KEY"],
            base_url="https://openrouter.ai/api/v1",
        )

    @property
    def applied_temperature(self) -> float:
        """The OpenAI-compatible endpoint still accepts sampling parameters."""
        return self.temperature

    def complete(self, system: str, messages: list[dict], max_tokens: int = 2000) -> Reply:
        try:
            r = self._client.chat.completions.create(
                model=self.spec.model_id,
                messages=[{"role": "system", "content": system}, *messages],
                max_tokens=max_tokens,
                temperature=self.temperature,
            )
            u = r.usage
            return Reply(
                r.choices[0].message.content or "",
                getattr(u, "prompt_tokens", 0),
                getattr(u, "completion_tokens", 0),
            )
        except Exception as e:  # noqa: BLE001
            return Reply("", error=f"{type(e).__name__}: {e}")


class MockClient:
    """Deterministic stand-in.

    Emits plausible negotiation prose and, when asked to commit, a valid JSON
    package chosen by a seeded RNG. Lets us exercise every downstream code path
    -- parsing, scoring, aggregation, reporting -- with zero spend.
    """

    def __init__(self, spec: ModelSpec, option_space: dict[str, list[str]],
                 seed: int = 0, temperature: float = 1.0):
        self.spec = spec
        self.name = spec.key
        self.option_space = option_space
        self.rng = random.Random(seed)
        self.temperature = temperature

    def complete(self, system: str, messages: list[dict], max_tokens: int = 2000) -> Reply:
        last = messages[-1]["content"] if messages else ""

        # Solved-game question: answer with one of the choices the prompt names,
        # so the grading path is exercised at a realistic hit rate.
        m = re.search(r"answer field must be one of:\s*(.+?)\.?\s*$", last, re.M)
        if m:
            choices = [c.strip() for c in m.group(1).split(",") if c.strip()]
            pick = self.rng.choice(choices) if choices else "a1"
            return Reply(
                f"Working through the structure.\n\n"
                f'```json\n{{"answer": "{pick}"}}\n```',
                len(last) // 4, 40,
            )
        if "answer field must be a number" in last:
            pick = self.rng.choice(["0.5", "0.33", "0.5", "0.75"])
            return Reply(f'```json\n{{"answer": "{pick}"}}\n```', len(last) // 4, 20)

        closing = ("FINAL COMMITMENT", "最终承诺")
        if any(k in last for k in closing) or any(k in system for k in closing):
            # If an offer has been tabled, accept it most of the time. Random
            # play would never converge on 3,600 packages, and the scoring and
            # aggregation paths only get exercised when deals actually close.
            offered = re.findall(r"\[([a-z]\d)\]", last)
            if offered and self.rng.random() < 0.7:
                pkg = {}
                for k, opts in self.option_space.items():
                    hit = [o for o in offered if o in opts]
                    pkg[k] = hit[0] if hit else self.rng.choice(opts)
            else:
                pkg = {k: self.rng.choice(v) for k, v in self.option_space.items()}
            body = json.dumps({"package": pkg, "accept": True}, indent=2)
            return Reply(
                f"Here is my final position.\n\n```json\n{body}\n```",
                len(system) // 4, 60,
            )
        pkg = {k: self.rng.choice(v) for k, v in self.option_space.items()}
        return Reply(
            "We should be able to find a package here. My proposal:\n\n"
            f"```json\n{json.dumps({'package': pkg}, indent=2)}\n```\n"
            "I have flexibility on some of these but not all.",
            len(system) // 4, 80,
        )


def build_client(
    key: str,
    option_space: dict[str, list[str]] | None = None,
    seed: int = 0,
    temperature: float = 1.0,
) -> ModelClient:
    spec = REGISTRY[key]
    if spec.provider == "anthropic":
        return AnthropicClient(spec, temperature)
    if spec.provider == "openrouter":
        return OpenRouterClient(spec, temperature)
    if spec.provider == "mock":
        return MockClient(spec, option_space or {}, seed, temperature)
    raise ValueError(f"unknown provider {spec.provider}")


def _anthropic_credentials() -> bool:
    """Any credential the Anthropic SDK would accept, not just the env var."""
    if os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN"):
        return True
    # a profile written by `ant auth login`
    from pathlib import Path as _P
    return (_P.home() / ".config" / "anthropic").is_dir()


def available_models() -> list[str]:
    """Which registry entries can actually run given the current environment."""
    out = []
    for key, spec in REGISTRY.items():
        if spec.provider == "mock":
            out.append(key)
        elif spec.provider == "anthropic" and _anthropic_credentials():
            out.append(key)
        elif spec.provider == "openrouter" and os.environ.get("OPENROUTER_API_KEY"):
            out.append(key)
    return out


# ---------------------------------------------------------------------------
# Robust JSON extraction
# ---------------------------------------------------------------------------

_FENCE = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.DOTALL)


def extract_json(text: str) -> dict | None:
    """Pull the intended JSON object out of a model reply.

    Tries fenced blocks first (what we ask for), then the last balanced brace
    span. Returns None if nothing parses -- callers record that as a parse
    failure rather than silently guessing, so malformed output is measured
    instead of hidden.
    """
    for m in reversed(_FENCE.findall(text)):
        try:
            return json.loads(m)
        except json.JSONDecodeError:
            continue

    # Collect top-level balanced spans, scanning forward and skipping past each
    # match so we take outermost objects rather than nested fragments. Then
    # prefer the last one: a model that restates its position means the restated
    # version.
    spans: list[str] = []
    i, n = 0, len(text)
    while i < n:
        if text[i] != "{":
            i += 1
            continue
        depth, in_str, esc = 0, False, False
        for j in range(i, n):
            c = text[j]
            if in_str:
                if esc:
                    esc = False
                elif c == "\\":
                    esc = True
                elif c == '"':
                    in_str = False
                continue
            if c == '"':
                in_str = True
            elif c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    spans.append(text[i : j + 1])
                    i = j + 1
                    break
        else:
            break  # unbalanced tail; nothing further can close
        if depth != 0:
            break

    for span in reversed(spans):
        try:
            return json.loads(span)
        except json.JSONDecodeError:
            continue
    return None


def with_retries(fn: Callable[[], Reply], tries: int = 3, base: float = 2.0) -> Reply:
    """Retry transient API failures with exponential backoff."""
    last = Reply("", error="no attempt made")
    for k in range(tries):
        last = fn()
        if last.error is None:
            return last
        if k < tries - 1:
            time.sleep(base ** k)
    return last
