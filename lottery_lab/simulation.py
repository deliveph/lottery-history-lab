from __future__ import annotations

import random
from collections import Counter
from dataclasses import dataclass
from itertools import combinations
from typing import Literal

from .models import Draw, GameRule


BallField = Literal["primary", "secondary"]


@dataclass(frozen=True, slots=True)
class Ticket:
    primary: tuple[int, ...]
    secondary: tuple[int, ...]


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
