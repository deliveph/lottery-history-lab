from __future__ import annotations

import hashlib
import math
import random
from collections import Counter
from dataclasses import dataclass
from datetime import date
from itertools import combinations
from typing import Literal

from .models import Draw, GameRule


BallField = Literal["primary", "secondary"]


@dataclass(frozen=True, slots=True)
class Ticket:
    primary: tuple[int, ...]
    secondary: tuple[int, ...]


_TRIGRAM_ELEMENTS = {
    1: "metal",
    2: "metal",
    3: "fire",
    4: "wood",
    5: "wood",
    6: "water",
    7: "earth",
    8: "earth",
}
_ELEMENT_TAILS = {
    "water": {1, 6},
    "fire": {2, 7},
    "wood": {3, 8},
    "metal": {4, 9},
    "earth": {0, 5},
}


def score_numbers(
    history: list[Draw], pool_max: int, *, field: BallField, recent_window: int = 50
) -> dict[int, float]:
    """Blend full/recent frequency and current omission into positive weights."""
    if not history:
        raise ValueError("history is empty")
    all_counts = Counter(number for draw in history for number in getattr(draw, field))
    recent_counts = Counter(
        number for draw in history[:recent_window] for number in getattr(draw, field)
    )
    omissions = {}
    for number in range(1, pool_max + 1):
        omissions[number] = next(
            (
                index
                for index, draw in enumerate(history)
                if number in getattr(draw, field)
            ),
            len(history),
        )

    global_component = _relative({n: all_counts[n] + 1 for n in range(1, pool_max + 1)})
    recent_component = _relative({n: recent_counts[n] + 1 for n in range(1, pool_max + 1)})
    omission_component = _relative({n: omissions[n] + 1 for n in range(1, pool_max + 1)})
    return {
        number: 0.50 * global_component[number]
        + 0.35 * recent_component[number]
        + 0.15 * omission_component[number]
        for number in range(1, pool_max + 1)
    }


def generate_tickets(
    rule: GameRule,
    history: list[Draw],
    *,
    count: int = 5,
    seed: int | None = None,
) -> list[Ticket]:
    if not history:
        raise ValueError("history is empty")
    if count < 1:
        raise ValueError("ticket count must be positive")
    if any(draw.game != rule.code for draw in history):
        raise ValueError(f"history contains records outside {rule.code}")

    primary_scores = score_numbers(history, rule.primary_max, field="primary")
    secondary_scores = score_numbers(history, rule.secondary_max, field="secondary")
    rng = random.Random(seed)
    tickets: list[Ticket] = []
    seen: set[Ticket] = set()
    max_attempts = max(100, count * 100)
    for _ in range(max_attempts):
        ticket = Ticket(
            tuple(sorted(_weighted_sample(primary_scores, rule.primary_count, rng))),
            tuple(sorted(_weighted_sample(secondary_scores, rule.secondary_count, rng))),
        )
        if ticket not in seen:
            seen.add(ticket)
            tickets.append(ticket)
        if len(tickets) == count:
            return tickets
    raise RuntimeError(f"could not generate {count} distinct tickets")


def generate_coverage_tickets(
    rule: GameRule,
    *,
    count: int = 5,
    seed: int | None = None,
) -> list[Ticket]:
    """Build a balanced, low-overlap ticket portfolio without predicting draws."""
    if count < 1:
        raise ValueError("ticket count must be positive")
    rng = random.Random(seed)
    best_tickets: list[Ticket] | None = None
    best_penalty = float("inf")
    attempts = 500
    for _ in range(attempts):
        primary_groups = _balanced_groups(rule.primary_max, rule.primary_count, count, rng)
        secondary_groups = _balanced_groups(
            rule.secondary_max, rule.secondary_count, count, rng
        )
        tickets = [
            Ticket(primary, secondary)
            for primary, secondary in zip(primary_groups, secondary_groups, strict=True)
        ]
        penalty = _portfolio_penalty(tickets)
        if len(set(tickets)) != count:
            penalty += 1_000_000
        if penalty < best_penalty:
            best_tickets, best_penalty = tickets, penalty
    if best_tickets is None or len(set(best_tickets)) != count:
        raise RuntimeError(f"could not generate {count} distinct coverage tickets")
    return best_tickets


def generate_iching_tickets(
    rule: GameRule,
    *,
    target_date: str,
    issue: str,
    count: int = 5,
) -> list[Ticket]:
    """Generate deterministic entertainment-only tickets from a date-based bagua mapping."""
    if count < 1:
        raise ValueError("ticket count must be positive")
    try:
        parsed_date = date.fromisoformat(target_date)
    except ValueError as exc:
        raise ValueError(f"invalid target date: {target_date!r}") from exc
    try:
        issue_number = int(issue)
    except ValueError as exc:
        raise ValueError(f"invalid issue: {issue!r}") from exc
    if issue_number < 1:
        raise ValueError(f"invalid issue: {issue!r}")

    upper, lower, moving = _iching_reading(parsed_date, issue_number)
    seed_material = (
        f"iching|{rule.code}|{target_date}|{issue_number}|{upper}|{lower}|{moving}"
    )
    seed = int.from_bytes(hashlib.sha256(seed_material.encode()).digest()[:8], "big")
    rng = random.Random(seed)
    best_tickets: list[Ticket] | None = None
    best_score = float("-inf")
    for _ in range(1_000):
        primary = _iching_groups(
            rule.primary_max, rule.primary_count, count, upper, lower, moving, rng
        )
        secondary = _iching_groups(
            rule.secondary_max, rule.secondary_count, count, lower, upper, moving, rng
        )
        tickets = [
            Ticket(first, second)
            for first, second in zip(primary, secondary, strict=True)
        ]
        score = _iching_portfolio_score(tickets, upper, lower, moving)
        if len(set(tickets)) == count and score > best_score:
            best_tickets, best_score = tickets, score
    if best_tickets is None:
        raise RuntimeError(f"could not generate {count} distinct iching tickets")
    return best_tickets


def _iching_reading(target: date, issue_number: int) -> tuple[int, int, int]:
    date_total = target.year + target.month + target.day
    return (
        _one_based_remainder(date_total, 8),
        _one_based_remainder(date_total + issue_number, 8),
        _one_based_remainder(date_total + issue_number, 6),
    )


def _one_based_remainder(value: int, modulus: int) -> int:
    remainder = value % modulus
    return modulus if remainder == 0 else remainder


def _iching_groups(
    pool_max: int,
    group_size: int,
    count: int,
    upper: int,
    lower: int,
    moving: int,
    rng: random.Random,
) -> list[tuple[int, ...]]:
    usage = Counter({number: 0 for number in range(1, pool_max + 1)})
    groups = []
    for group_index in range(1, count + 1):
        selected: list[int] = []
        for _ in range(group_size):
            available = [number for number in usage if number not in selected]
            minimum_usage = min(usage[number] for number in available)
            candidates = [
                number for number in available if usage[number] == minimum_usage
            ]
            scores = _iching_number_scores(
                candidates, upper, lower, moving, group_index
            )
            selected.append(rng.choices(candidates, weights=scores, k=1)[0])
        usage.update(selected)
        groups.append(tuple(sorted(selected)))
    return groups


def _iching_number_scores(
    numbers: list[int], upper: int, lower: int, moving: int, group_index: int
) -> list[float]:
    turning = _one_based_remainder(upper + lower + moving + group_index, 8)
    upper_tails = _ELEMENT_TAILS[_TRIGRAM_ELEMENTS[upper]]
    lower_tails = _ELEMENT_TAILS[_TRIGRAM_ELEMENTS[lower]]
    turning_tails = _ELEMENT_TAILS[_TRIGRAM_ELEMENTS[turning]]
    scores = []
    for number in numbers:
        trigram = _one_based_remainder(number, 8)
        score = 1.0
        score *= 2.10 if trigram == upper else 1.0
        score *= 1.85 if trigram == lower else 1.0
        score *= 1.45 if trigram == turning else 1.0
        score *= 1.35 if number % 10 in upper_tails else 1.0
        score *= 1.25 if number % 10 in lower_tails else 1.0
        score *= 1.12 if number % 10 in turning_tails else 1.0
        score *= 1.30 if _one_based_remainder(number, 6) == moving else 1.0
        scores.append(score)
    return scores


def _iching_portfolio_score(
    tickets: list[Ticket], upper: int, lower: int, moving: int
) -> float:
    quality = 0.0
    for group_index, ticket in enumerate(tickets, start=1):
        primary_scores = _iching_number_scores(
            list(ticket.primary), upper, lower, moving, group_index
        )
        secondary_scores = _iching_number_scores(
            list(ticket.secondary), lower, upper, moving, group_index
        )
        quality += sum(math.log(score) for score in primary_scores + secondary_scores)
    return quality - _portfolio_penalty(tickets)


def _relative(values: dict[int, int]) -> dict[int, float]:
    mean = sum(values.values()) / len(values)
    return {number: value / mean for number, value in values.items()}


def _weighted_sample(
    scores: dict[int, float], count: int, rng: random.Random
) -> list[int]:
    available = list(scores)
    selected = []
    for _ in range(count):
        weights = [scores[number] for number in available]
        number = rng.choices(available, weights=weights, k=1)[0]
        selected.append(number)
        available.remove(number)
    return selected


def _balanced_groups(
    pool_max: int, group_size: int, count: int, rng: random.Random
) -> list[tuple[int, ...]]:
    usage = Counter({number: 0 for number in range(1, pool_max + 1)})
    groups = []
    for _ in range(count):
        tie_breakers = {number: rng.random() for number in usage}
        ordered = sorted(usage, key=lambda number: (usage[number], tie_breakers[number]))
        group = tuple(sorted(ordered[:group_size]))
        usage.update(group)
        groups.append(group)
    return groups


def _portfolio_penalty(tickets: list[Ticket]) -> float:
    penalty = 0.0
    for field in ("primary", "secondary"):
        pair_usage: Counter[tuple[int, int]] = Counter()
        for ticket in tickets:
            numbers = getattr(ticket, field)
            pair_usage.update(combinations(numbers, 2))
            penalty += 8 * sum(b == a + 1 for a, b in zip(numbers, numbers[1:]))
            penalty += 3 * sum(
                b - a == c - b for a, b, c in zip(numbers, numbers[1:], numbers[2:])
            )
            penalty += abs(2 * sum(number % 2 for number in numbers) - len(numbers))
        penalty += 12 * sum(count * (count - 1) // 2 for count in pair_usage.values())
    return penalty
