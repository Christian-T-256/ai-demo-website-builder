"""Deterministic copy checks for generated public pages."""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from html.parser import HTMLParser


@dataclass(frozen=True)
class CopyViolation:
    rule: str
    match: str


class CopyGateError(ValueError):
    def __init__(self, violations: list[CopyViolation]):
        self.violations = violations
        details = "; ".join(f"{item.rule}: {item.match!r}" for item in violations)
        super().__init__(f"Copy gate blocked the page. {details}")


class _VisibleCopyParser(HTMLParser):
    """Extract authored copy while excluding scripts, styles, and quoted reviews."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self._ignored_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"script", "style", "blockquote"}:
            self._ignored_depth += 1
            return
        if self._ignored_depth:
            return
        for name, value in attrs:
            if name in {"content", "title", "alt", "aria-label"} and value:
                self.parts.append(value)

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style", "blockquote"} and self._ignored_depth:
            self._ignored_depth -= 1

    def handle_data(self, data: str) -> None:
        if not self._ignored_depth:
            self.parts.append(data)


HARD_RULES: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("em or en dash", re.compile(r"[\u2013\u2014]|&(?:mdash|ndash);", re.IGNORECASE)),
    ("unfilled template token", re.compile(r"\{\{[^{}]+\}\}|\$\{[^{}]+\}")),
    ("the word worth", re.compile(r"\bworth\b", re.IGNORECASE)),
    (
        "explicit call duration",
        re.compile(
            r"\b(?:\d{1,2}|fifteen|thirty|forty[ -]?five)[ -]?(?:min|mins|minute|minutes)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "corporate or AI sounding word",
        re.compile(
            r"\b(?:utilize|seamless|robust|delve|elevate|streamline|synergy|holistic|"
            r"cutting[ -]?edge|empower|game[ -]?changer|supercharge|unlock|harness|"
            r"transformative|revolutionary|groundbreaking|tapestry|multifaceted)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "generic AI opener or closer",
        re.compile(
            r"\b(?:i hope this finds you|in today'?s|at the end of the day|"
            r"let me know if you have any questions|don'?t hesitate to|"
            r"it is important to note|let'?s dive in)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "chat or citation artifact",
        re.compile(
            r"(?:turn\d+search\d+|oaicite|contentreference|attached_file|"
            r"would you like me to|as of my last training)",
            re.IGNORECASE,
        ),
    ),
)


def visible_copy(text: str) -> str:
    if "<" not in text:
        return text
    parser = _VisibleCopyParser()
    parser.feed(text)
    return " ".join(parser.parts)


def lint_copy(text: str) -> list[CopyViolation]:
    searchable = visible_copy(text)
    violations: list[CopyViolation] = []
    for rule, pattern in HARD_RULES:
        target = text if rule in {"em or en dash", "unfilled template token"} else searchable
        match = pattern.search(target)
        if match:
            violations.append(CopyViolation(rule=rule, match=match.group(0)))
    return violations


def enforce_copy_gate(text: str) -> dict[str, object]:
    violations = lint_copy(text)
    if violations:
        raise CopyGateError(violations)
    return {"status": "passed", "hard_violations": 0, "rules_checked": len(HARD_RULES)}


def report(text: str) -> dict[str, object]:
    violations = lint_copy(text)
    return {
        "status": "blocked" if violations else "passed",
        "hard_violations": len(violations),
        "rules_checked": len(HARD_RULES),
        "violations": [asdict(item) for item in violations],
    }
