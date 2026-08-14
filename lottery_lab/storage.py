from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from .models import Draw, GameRule


@dataclass(frozen=True, slots=True)
class HistoryPaths:
    json: Path
    csv: Path


def save_history(data_dir: Path, rule: GameRule, draws: list[Draw]) -> HistoryPaths:
    data_dir.mkdir(parents=True, exist_ok=True)
    paths = HistoryPaths(
        data_dir / f"{rule.code}_history.json",
        data_dir / f"{rule.code}_history.csv",
    )
    payload = {
        "game": rule.code,
        "gameName": rule.name,
        "recordCount": len(draws),
        "updatedAt": datetime.now(UTC).isoformat(),
        "draws": [_draw_dict(draw) for draw in draws],
    }
    paths.json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    with paths.csv.open("w", encoding="utf-8-sig", newline="") as csv_file:
        writer = csv.DictWriter(
            csv_file, fieldnames=("game", "issue", "draw_date", "primary", "secondary")
        )
        writer.writeheader()
        writer.writerows(_draw_dict(draw) for draw in draws)
    return paths


def load_history(data_dir: Path, rule: GameRule) -> list[Draw]:
    path = data_dir / f"{rule.code}_history.json"
    if not path.exists():
        raise FileNotFoundError(f"history cache not found: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("game") != rule.code or not isinstance(payload.get("draws"), list):
        raise ValueError(f"invalid {rule.name} history cache: {path}")
    return [
        Draw.create(
            rule,
            row.get("issue"),
            row.get("draw_date"),
            _stored_numbers(row.get("primary")),
            _stored_numbers(row.get("secondary")),
        )
        for row in payload["draws"]
    ]


def _draw_dict(draw: Draw) -> dict[str, str]:
    return {
        "game": draw.game,
        "issue": draw.issue,
        "draw_date": draw.draw_date,
        "primary": " ".join(f"{number:02d}" for number in draw.primary),
        "secondary": " ".join(f"{number:02d}" for number in draw.secondary),
    }


def _stored_numbers(value: object) -> tuple[int, ...]:
    try:
        return tuple(int(part) for part in str(value).split())
    except ValueError as exc:
        raise ValueError("history cache contains non-numeric draw result") from exc
