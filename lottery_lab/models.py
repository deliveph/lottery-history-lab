from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True, slots=True)
class GameRule:
    code: str
    name: str
    primary_count: int
    primary_max: int
    secondary_count: int
    secondary_max: int


DLT_RULE = GameRule("dlt", "大乐透", 5, 35, 2, 12)
SSQ_RULE = GameRule("ssq", "双色球", 6, 33, 1, 16)
RULES = {rule.code: rule for rule in (DLT_RULE, SSQ_RULE)}


@dataclass(frozen=True, slots=True)
class Draw:
    game: str
    issue: str
    draw_date: str
    primary: tuple[int, ...]
    secondary: tuple[int, ...]

    @classmethod
    def create(
        cls,
        rule: GameRule,
        issue: object,
        draw_date: object,
        primary: tuple[int, ...],
        secondary: tuple[int, ...],
    ) -> Draw:
        issue_text = str(issue).strip()
        date_text = str(draw_date).strip()
        if not issue_text:
            raise ValueError("draw issue is empty")
        try:
            date.fromisoformat(date_text)
        except ValueError as exc:
            raise ValueError(f"issue {issue_text}: invalid date {date_text!r}") from exc
        _validate_ball_set(
            issue_text, "primary", primary, rule.primary_count, rule.primary_max
        )
        _validate_ball_set(
            issue_text,
            "secondary",
            secondary,
            rule.secondary_count,
            rule.secondary_max,
        )
        return cls(
            rule.code,
            issue_text,
            date_text,
            tuple(sorted(primary)),
            tuple(sorted(secondary)),
        )


@dataclass(frozen=True, slots=True)
class DrawPage:
    page_no: int
    total_pages: int
    total_records: int
    draws: tuple[Draw, ...]


def _validate_ball_set(
    issue: str, label: str, numbers: tuple[int, ...], expected_count: int, maximum: int
) -> None:
    if len(numbers) != expected_count:
        raise ValueError(f"issue {issue}: expected {expected_count} {label} numbers")
    if len(set(numbers)) != len(numbers):
        raise ValueError(f"issue {issue}: duplicate {label} numbers")
    if any(number < 1 or number > maximum for number in numbers):
        raise ValueError(f"issue {issue}: {label} number outside 1..{maximum}")
