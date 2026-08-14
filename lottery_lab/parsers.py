from __future__ import annotations

import json
import re
from collections.abc import Mapping
from typing import Any

from .models import DLT_RULE, SSQ_RULE, Draw, DrawPage, GameRule


_JSONP_RE = re.compile(r"^[A-Za-z_$][\w.$]*\((.*)\)\s*;?$", re.DOTALL)


def parse_dlt_page(payload: Mapping[str, Any]) -> DrawPage:
    if payload.get("success") is not True or str(payload.get("errorCode")) != "0":
        raise ValueError(
            f"upstream DLT error {payload.get('errorCode')}: {payload.get('errorMessage', '')}"
        )
    value = _mapping(payload.get("value"), "DLT value")
    rows = value.get("list")
    if not isinstance(rows, list):
        raise ValueError("DLT value.list is not a list")
    draws = []
    for row_value in rows:
        row = _mapping(row_value, "DLT draw")
        numbers = _numbers(row.get("lotteryDrawResult"), row.get("lotteryDrawNum"))
        draws.append(
            Draw.create(
                DLT_RULE,
                row.get("lotteryDrawNum"),
                row.get("lotteryDrawTime"),
                numbers[: DLT_RULE.primary_count],
                numbers[DLT_RULE.primary_count :],
            )
        )
    return _page(value, draws, page_key="pageNo")


def parse_ssq_page(raw: str | Mapping[str, Any]) -> DrawPage:
    payload = _decode_jsonp(raw) if isinstance(raw, str) else raw
    if str(payload.get("resCode")) != "000000":
        raise ValueError(
            f"upstream SSQ error {payload.get('resCode')}: {payload.get('message', '')}"
        )
    rows = payload.get("data")
    if not isinstance(rows, list):
        raise ValueError("SSQ data is not a list")
    draws = []
    for row_value in rows:
        row = _mapping(row_value, "SSQ draw")
        primary = _numbers(row.get("frontWinningNum"), row.get("issue"))
        secondary = _numbers(row.get("backWinningNum"), row.get("issue"))
        draws.append(
            Draw.create(
                SSQ_RULE,
                row.get("issue"),
                row.get("openTime"),
                primary,
                secondary,
            )
        )
    return _page(payload, draws, page_key="pageNum")


def _decode_jsonp(raw: str) -> Mapping[str, Any]:
    text = raw.strip()
    match = _JSONP_RE.fullmatch(text)
    json_text = match.group(1) if match else text
    try:
        return _mapping(json.loads(json_text), "SSQ payload")
    except json.JSONDecodeError as exc:
        raise ValueError("SSQ response is not valid JSON or JSONP") from exc


def _numbers(value: object, issue: object) -> tuple[int, ...]:
    try:
        return tuple(int(part) for part in str(value).split())
    except ValueError as exc:
        raise ValueError(f"issue {issue}: non-numeric draw result") from exc


def _mapping(value: object, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{label} is not an object")
    return value


def _page(
    payload: Mapping[str, Any], draws: list[Draw], *, page_key: str
) -> DrawPage:
    try:
        return DrawPage(
            page_no=int(payload[page_key]),
            total_pages=int(payload["pages"]),
            total_records=int(payload["total"]),
            draws=tuple(draws),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("upstream response has invalid pagination metadata") from exc
