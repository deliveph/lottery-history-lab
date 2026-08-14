from __future__ import annotations

import random
from collections import Counter
from dataclasses import dataclass
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
