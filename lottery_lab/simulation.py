from __future__ import annotations

import hashlib
import math
import random
from collections import Counter
from dataclasses import dataclass
from datetime import date, datetime, time
from itertools import combinations
from typing import Literal

from .models import Draw, GameRule


BallField = Literal["primary", "secondary"]


@dataclass(frozen=True, slots=True)
class Ticket:
    primary: tuple[int, ...]
    secondary: tuple[int, ...]


_DIRECTION_VALUES = {
    "北": 1,
    "东北": 2,
    "东": 3,
    "东南": 4,
    "南": 5,
    "西南": 6,
    "西": 7,
    "西北": 8,
    "中": 9,
}
_TRIGRAM_DIRECTIONS = {
    1: "西北",
    2: "西",
    3: "南",
    4: "东",
    5: "东南",
    6: "北",
    7: "东北",
    8: "西南",
}
_EARTHLY_BRANCHES = (
    "子",
    "丑",
    "寅",
    "卯",
    "辰",
    "巳",
    "午",
    "未",
    "申",
    "酉",
    "戌",
    "亥",
)


@dataclass(frozen=True, slots=True)
class IChingContext:
    """Validated inputs for the optional context-aware entertainment mapping."""

    draw_time: str
    cast_at: str
    lunar_birth_date: str | None = None
    birth_time: str | None = None
    location: str = "未指定"
    latitude: float | None = None
    longitude: float | None = None
    direction: str = "中"
    wealth_direction: str | None = None

    @classmethod
    def create(
        cls,
        *,
        draw_time: str,
        cast_at: str,
        lunar_birth_date: str | None = None,
        birth_time: str | None = None,
        location: str = "未指定",
        latitude: float | None = None,
        longitude: float | None = None,
        direction: str = "中",
        wealth_direction: str | None = None,
    ) -> IChingContext:
        normalized_draw_time = _normalize_clock(draw_time, "draw time")
        normalized_birth_time = (
            _normalize_clock(birth_time, "birth time") if birth_time else None
        )
        normalized_cast_at = _normalize_datetime(cast_at)
        normalized_birth_date = (
            _normalize_lunar_date(lunar_birth_date) if lunar_birth_date else None
        )
        if (latitude is None) != (longitude is None):
            raise ValueError("latitude and longitude must be supplied together")
        if latitude is not None and not -90 <= latitude <= 90:
            raise ValueError("latitude must be within -90..90")
        if longitude is not None and not -180 <= longitude <= 180:
            raise ValueError("longitude must be within -180..180")
        if direction not in _DIRECTION_VALUES:
            raise ValueError(f"invalid direction: {direction!r}")
        if wealth_direction is not None and wealth_direction not in _DIRECTION_VALUES:
            raise ValueError(f"invalid wealth direction: {wealth_direction!r}")
        normalized_location = location.strip() or "未指定"
        return cls(
            draw_time=normalized_draw_time,
            cast_at=normalized_cast_at,
            lunar_birth_date=normalized_birth_date,
            birth_time=normalized_birth_time,
            location=normalized_location,
            latitude=latitude,
            longitude=longitude,
            direction=direction,
            wealth_direction=wealth_direction,
        )


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
    context: IChingContext | None = None,
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

    upper, lower, moving = _iching_reading(parsed_date, issue_number, context)
    context_material = _iching_context_material(context, parsed_date)
    seed_material = (
        f"iching|{rule.code}|{target_date}|{issue_number}|{upper}|{lower}|{moving}"
        f"|{context_material}"
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


def _iching_reading(
    target: date, issue_number: int, context: IChingContext | None = None
) -> tuple[int, int, int]:
    date_total = target.year + target.month + target.day
    if context is not None:
        birth_value, time_value, place_value, direction_value = _context_values(
            context, target
        )
        upper_source = date_total + birth_value + place_value + direction_value
        lower_source = date_total + issue_number + time_value + place_value
        return (
            _one_based_remainder(upper_source, 8),
            _one_based_remainder(lower_source, 8),
            _one_based_remainder(upper_source + lower_source, 6),
        )
    return (
        _one_based_remainder(date_total, 8),
        _one_based_remainder(date_total + issue_number, 8),
        _one_based_remainder(date_total + issue_number, 6),
    )


def iching_context_summary(context: IChingContext, *, target_date: str) -> str:
    """Return the normalized inputs used by a contextual I Ching run."""
    target = date.fromisoformat(target_date)
    birth = context.lunar_birth_date or "未提供"
    if context.birth_time:
        birth_time = f"{context.birth_time}（{_earthly_branch(context.birth_time)}时）"
    else:
        birth_time = "未提供（非完整八字）"
    if context.latitude is None:
        location = context.location
    else:
        location = (
            f"{context.location}（{context.latitude:.4f}, {context.longitude:.4f}）"
        )
    wealth = context.wealth_direction or _wealth_direction(target)
    return (
        f"开奖 {context.draw_time}（{_earthly_branch(context.draw_time)}时）"
        f"｜起卦时间 {context.cast_at}"
        f"｜农历生辰 {birth}｜出生时辰 {birth_time}"
        f"｜定位 {location}｜方位 {context.direction}"
        f"｜财位 {wealth}（娱乐卦象映射）"
    )


def _normalize_clock(value: str, label: str) -> str:
    try:
        parsed = time.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"invalid {label}: {value!r}") from exc
    return parsed.strftime("%H:%M")


def _normalize_datetime(value: str) -> str:
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"invalid cast time: {value!r}") from exc
    return parsed.isoformat(timespec="seconds")


def _normalize_lunar_date(value: str) -> str:
    parts = value.split("-")
    if len(parts) != 3:
        raise ValueError(f"invalid lunar birth date: {value!r}")
    try:
        year, month, day_value = (int(part) for part in parts)
    except ValueError as exc:
        raise ValueError(f"invalid lunar birth date: {value!r}") from exc
    if year < 1 or not 1 <= month <= 12 or not 1 <= day_value <= 30:
        raise ValueError(f"invalid lunar birth date: {value!r}")
    return f"{year:04d}-{month:02d}-{day_value:02d}"


def _earthly_branch(clock: str) -> str:
    hour = int(clock[:2])
    branch_index = 0 if hour == 23 else (hour + 1) // 2
    return _EARTHLY_BRANCHES[branch_index]


def _wealth_direction(target: date) -> str:
    date_total = target.year + target.month + target.day
    return _TRIGRAM_DIRECTIONS[_one_based_remainder(date_total, 8)]


def _context_values(
    context: IChingContext, target: date
) -> tuple[int, int, int, int]:
    birth_value = 0
    if context.lunar_birth_date:
        birth_value = sum(int(part) for part in context.lunar_birth_date.split("-"))
    if context.birth_time:
        birth_value += _clock_minutes(context.birth_time) + _branch_index(
            context.birth_time
        )

    cast = datetime.fromisoformat(context.cast_at)
    time_value = (
        _clock_minutes(context.draw_time)
        + _branch_index(context.draw_time)
        + cast.year
        + cast.month
        + cast.day
        + cast.hour * 60
        + cast.minute
    )
    location_hash = hashlib.sha256(context.location.encode()).digest()
    place_value = int.from_bytes(location_hash[:4], "big")
    if context.latitude is not None and context.longitude is not None:
        place_value += round((context.latitude + 90) * 10_000)
        place_value += round((context.longitude + 180) * 10_000)

    wealth = context.wealth_direction or _wealth_direction(target)
    direction_value = _DIRECTION_VALUES[context.direction] + _DIRECTION_VALUES[wealth]
    return birth_value, time_value, place_value, direction_value


def _iching_context_material(context: IChingContext | None, target: date) -> str:
    if context is None:
        return "legacy"
    wealth = context.wealth_direction or _wealth_direction(target)
    return "|".join(
        (
            context.draw_time,
            context.cast_at,
            context.lunar_birth_date or "",
            context.birth_time or "",
            context.location,
            "" if context.latitude is None else f"{context.latitude:.6f}",
            "" if context.longitude is None else f"{context.longitude:.6f}",
            context.direction,
            wealth,
        )
    )


def _clock_minutes(clock: str) -> int:
    hour, minute = (int(part) for part in clock.split(":"))
    return hour * 60 + minute


def _branch_index(clock: str) -> int:
    return _EARTHLY_BRANCHES.index(_earthly_branch(clock)) + 1


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
