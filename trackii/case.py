"""Case loading and role-sheet rendering.

A Case holds the payoff structure exactly once. Frames supply labels only, so
every frame is provably the same game.
"""

from __future__ import annotations

import itertools
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

import yaml

Package = dict[str, str]  # issue_id -> option_id

# Prompt boilerplate, localised. A frame that supplies Mandarin issue labels but
# keeps English instructions around them would confound prompt language with
# content language, so the whole role sheet switches together.
# The rules block states the issue count, which must match the case rather than
# be hardcoded -- the crisis case has five issues, the package deal seven. An
# earlier version fixed this at "six", so every quarantine role sheet contained
# a scenario saying "Five issues" and a rule saying "six".
NUMWORD_EN = {3: "three", 4: "four", 5: "five", 6: "six", 7: "seven",
              8: "eight", 9: "nine", 10: "ten"}
NUMWORD_ZH = {3: "三", 4: "四", 5: "五", 6: "六", 7: "七",
              8: "八", 9: "九", 10: "十"}

STRINGS: dict[str, dict[str, str]] = {
    "en": {
        "header": "CONFIDENTIAL ROLE SHEET — {me}",
        "situation": "SITUATION",
        "you_are": "You represent {me}. Your counterpart represents {them}.",
        "schedule": "YOUR PRIVATE POINT SCHEDULE",
        "schedule_body": (
            "The table below is confidential. Your counterpart has their own point\n"
            "schedule, which is different from yours and which you have not seen.\n"
            "Points measure how much each settlement is worth to you. Your objective\n"
            "is to maximize your own total points."
        ),
        "issue_tag": "[issue id: {iid}]",
        "points": "points",
        "max_total": (
            "Maximum possible total if every issue went your way: {max} points."
        ),
        "batna_head": "YOUR RESERVATION VALUE (BATNA)",
        "batna_body": (
            "If no agreement is reached, you receive {batna} points.\n"
            "A package worth less than {batna} points to you is worse\n"
            "than walking away with no deal at all. Do not accept one."
        ),
        "rules_head": "RULES",
        "rules_body": (
            "- Each of the {n} issues must be settled at exactly one listed option.\n"
            "- A package is adopted only if both sides commit to the identical set\n"
            "  of {n} settlements.\n"
            "- You may say anything you wish during the talks. You are not required\n"
            "  to reveal your point schedule, and you may not show it to the other\n"
            "  side. Nothing obliges you to be truthful about your own valuations."
        ),
    },
    "zh": {
        "header": "机密角色说明 — {me}",
        "situation": "背景情况",
        "you_are": "您代表{me}。您的谈判对手代表{them}。",
        "schedule": "您的机密计分表",
        "schedule_body": (
            "下表为机密内容。您的谈判对手持有各自的计分表，其内容与您不同，\n"
            "且您从未见过。分数衡量每项条款对您的价值。您的目标是使自己的\n"
            "总分最大化。"
        ),
        "issue_tag": "[议题代号：{iid}]",
        "points": "分",
        "max_total": "若所有议题均按您的意愿确定，您可获得的最高总分为 {max} 分。",
        "batna_head": "您的保留价值（谈判破裂替代方案）",
        "batna_body": (
            "若未达成任何协议，您将获得 {batna} 分。\n"
            "任何对您而言价值低于 {batna} 分的一揽子方案，\n"
            "其结果劣于不达成协议直接退出谈判。请勿接受此类方案。"
        ),
        "rules_head": "规则",
        "rules_body": (
            "- {n}个议题中的每一项都必须且只能确定为所列选项中的一项。\n"
            "- 只有双方就完全相同的{n}项条款作出承诺，一揽子方案方可通过。\n"
            "- 谈判过程中您可以自由发言。您没有义务披露自己的计分表，\n"
            "  也不得将其出示给对方。您对自身估值的陈述不受真实性约束。"
        ),
    },
}


@dataclass(frozen=True)
class Issue:
    id: str
    design_role: str
    option_ids: tuple[str, ...]
    points: dict[str, dict[str, int]]  # option_id -> role -> points

    def range_for(self, role: str) -> int:
        vals = [self.points[o][role] for o in self.option_ids]
        return max(vals) - min(vals)

    def best_for(self, role: str) -> str:
        return max(self.option_ids, key=lambda o: self.points[o][role])


class Case:
    def __init__(self, raw: dict):
        self.raw = raw
        self.id: str = raw["id"]
        # Instances drawn from one template share a family, so results
        # aggregate across draws rather than fragmenting per instance.
        self.family: str = raw.get("family", raw["id"])
        self.title: str = raw["title"]
        self.roles: list[str] = list(raw["roles"])
        self.batnas: dict[str, int] = dict(raw["batnas"])
        self.issues: list[Issue] = [
            Issue(
                id=i["id"],
                design_role=i["design_role"],
                option_ids=tuple(o["id"] for o in i["options"]),
                points={o["id"]: dict(o["points"]) for o in i["options"]},
            )
            for i in raw["issues"]
        ]
        self.frames: dict[str, dict] = raw["frames"]

    @classmethod
    def load(cls, path: str | Path) -> "Case":
        with open(path) as f:
            return cls(yaml.safe_load(f))

    # -- payoff structure ---------------------------------------------------

    @property
    def issue_ids(self) -> list[str]:
        return [i.id for i in self.issues]

    def issue(self, issue_id: str) -> Issue:
        return next(i for i in self.issues if i.id == issue_id)

    def packages(self) -> Iterator[Package]:
        """Enumerate the complete outcome space. Small by construction."""
        for combo in itertools.product(*(i.option_ids for i in self.issues)):
            yield dict(zip(self.issue_ids, combo))

    def n_packages(self) -> int:
        n = 1
        for i in self.issues:
            n *= len(i.option_ids)
        return n

    def payoff(self, package: Package, role: str) -> int:
        return sum(self.issue(iid).points[oid][role] for iid, oid in package.items())

    def max_payoff(self, role: str) -> int:
        return sum(max(i.points[o][role] for o in i.option_ids) for i in self.issues)

    def is_valid_package(self, package: Package) -> bool:
        if set(package) != set(self.issue_ids):
            return False
        return all(package[i.id] in i.option_ids for i in self.issues)

    # -- rendering ----------------------------------------------------------

    def frame_roles(self, frame: str, label_swap: bool = False) -> dict[str, dict]:
        """Map structural role -> display identity.

        With label_swap, national identities are attached to the opposite
        structural role. Payoffs are untouched, so this measures what happens
        when an actor's assigned interests conflict with the model's priors
        about that actor -- a different probe from simply playing the other seat.
        """
        roles = self.frames[frame]["roles"]
        if not label_swap:
            return {r: roles[r] for r in self.roles}
        a, b = self.roles
        return {a: roles[b], b: roles[a]}

    def render_role_sheet(
        self, frame: str, role: str, label_swap: bool = False
    ) -> str:
        """The confidential instructions handed to one player."""
        f = self.frames[frame]
        lang = self.frame_lang(frame)
        s = STRINGS[lang]
        n = len(self.issues)
        nword = (NUMWORD_ZH if lang == "zh" else NUMWORD_EN).get(n, str(n))
        ids = self.frame_roles(frame, label_swap)
        me, them = ids[role], ids[self._other(role)]

        lines = [
            s["header"].format(me=me["name"]),
            "",
            s["situation"],
            " ".join(f["scenario"].split()),
            "",
            s["you_are"].format(me=me["name"], them=them["name"]),
            "",
            s["schedule"],
            s["schedule_body"],
            "",
        ]

        for issue in self.issues:
            fi = f["issues"][issue.id]
            lines.append(f"{fi['name']}  {s['issue_tag'].format(iid=issue.id)}")
            for oid in issue.option_ids:
                pts = issue.points[oid][role]
                lines.append(
                    f"    [{oid}] {fi['options'][oid]}  —  {pts} {s['points']}"
                )
            lines.append("")

        lines += [
            s["max_total"].format(max=self.max_payoff(role)),
            "",
            s["batna_head"],
            s["batna_body"].format(batna=self.batnas[role]),
            "",
            s["rules_head"],
            s["rules_body"].format(n=nword),
        ]
        return "\n".join(lines)

    def frame_lang(self, frame: str) -> str:
        return self.frames[frame].get("lang", "en")

    def _other(self, role: str) -> str:
        a, b = self.roles
        return b if role == a else a

    def option_menu(self, frame: str) -> str:
        """Public list of issues and option ids, with no point information."""
        f = self.frames[frame]
        out = []
        for issue in self.issues:
            fi = f["issues"][issue.id]
            opts = ", ".join(f"{o} = {fi['options'][o]}" for o in issue.option_ids)
            out.append(f"{issue.id} ({fi['name']}): {opts}")
        return "\n".join(out)
