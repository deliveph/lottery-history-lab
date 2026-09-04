from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .fetchers import fetch_dlt_history, fetch_ssq_history
from .models import DLT_RULE, SSQ_RULE, Draw, GameRule
from .simulation import (
    Ticket,
    generate_coverage_tickets,
    generate_iching_tickets,
    generate_tickets,
)
from .storage import load_history, save_history


DISCLAIMER = (
    "仅供娱乐：开奖是独立随机事件，历史统计不能预测下一期，"
    "玄学映射也不能提高中奖概率。"
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m lottery_lab",
        description="拉取彩票历史数据并生成娱乐性加权随机候选号码。",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    run_parser = subparsers.add_parser("run", help="联网更新历史数据，然后生成候选号码")
    _common_options(run_parser)
    offline_parser = subparsers.add_parser("generate", help="从本地缓存生成候选号码")
    _common_options(offline_parser)
    offline_parser.add_argument(
        "--offline", action="store_true", help="明确仅使用本地缓存（generate 始终离线）"
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    data_dir = Path(args.data_dir)
    try:
        if args.command == "run":
            histories = _refresh(data_dir)
        else:
            histories = {
                DLT_RULE.code: load_history(data_dir, DLT_RULE),
                SSQ_RULE.code: load_history(data_dir, SSQ_RULE),
            }
        print()
        for rule in (DLT_RULE, SSQ_RULE):
            draws = histories[rule.code]
            target_date = None
            if args.mode == "coverage":
                tickets = generate_coverage_tickets(rule, count=args.count, seed=args.seed)
            elif args.mode == "iching":
                target_date = args.dlt_date if rule.code == "dlt" else args.ssq_date
                if target_date is None:
                    raise ValueError(f"iching 模式缺少 {rule.name} 目标日期")
                next_issue = str(int(draws[0].issue) + 1).zfill(len(draws[0].issue))
                tickets = generate_iching_tickets(
                    rule,
                    target_date=target_date,
                    issue=next_issue,
                    count=args.count,
                )
            else:
                tickets = generate_tickets(rule, draws, count=args.count, seed=args.seed)
            _print_tickets(
                rule, draws, tickets, mode=args.mode, target_date=target_date
            )
        print(f"\n提示：{DISCLAIMER}")
        return 0
    except (OSError, ValueError, RuntimeError) as exc:
        print(f"错误：{exc}", file=sys.stderr)
        return 1


def _common_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--count", type=_positive_int, default=5, help="每种彩票生成组数（默认 5）")
    parser.add_argument("--seed", type=int, help="可选随机种子，用于复现相同结果")
    parser.add_argument("--data-dir", default="data", help="历史数据目录（默认 ./data）")
    parser.add_argument(
        "--mode",
        choices=("weighted", "coverage", "iching"),
        default="weighted",
        help="生成模式：历史加权 weighted、低重叠覆盖 coverage 或易经八卦 iching",
    )
    parser.add_argument("--dlt-date", help="iching 模式的大乐透目标日期（YYYY-MM-DD）")
    parser.add_argument("--ssq-date", help="iching 模式的双色球目标日期（YYYY-MM-DD）")


def _positive_int(value: str) -> int:
    parsed = int(value)
    if parsed < 1:
        raise argparse.ArgumentTypeError("必须是正整数")
    return parsed


def _refresh(data_dir: Path) -> dict[str, list[Draw]]:
    print("正在拉取大乐透完整历史数据……")
    dlt_draws = fetch_dlt_history()
    print(f"已获取大乐透 {len(dlt_draws)} 期。")
    print("正在拉取双色球完整历史数据……")
    ssq_draws = fetch_ssq_history()
    print(f"已获取双色球 {len(ssq_draws)} 期。")
    for rule, draws in ((DLT_RULE, dlt_draws), (SSQ_RULE, ssq_draws)):
        paths = save_history(data_dir, rule, draws)
        print(f"已保存 {rule.name}：{paths.json}；{paths.csv}")
    return {DLT_RULE.code: dlt_draws, SSQ_RULE.code: ssq_draws}


def _print_tickets(
    rule: GameRule,
    draws: list[Draw],
    tickets: list[Ticket],
    *,
    mode: str,
    target_date: str | None = None,
) -> None:
    latest = draws[0]
    mode_label = {
        "weighted": "历史加权",
        "coverage": "低重叠覆盖",
        "iching": "易经八卦",
    }[mode]
    target_label = f"｜目标 {target_date}" if target_date else ""
    print(
        f"\n{rule.name}候选号码（{len(tickets)} 组）"
        f"｜模式 {mode_label}{target_label}"
        f"｜历史 {len(draws)} 期｜最新 {latest.issue}（{latest.draw_date}）"
    )
    first_label, second_label = ("前区", "后区") if rule.code == "dlt" else ("红球", "蓝球")
    for index, ticket in enumerate(tickets, start=1):
        primary = " ".join(f"{number:02d}" for number in ticket.primary)
        secondary = " ".join(f"{number:02d}" for number in ticket.secondary)
        print(f"{index}. {first_label} {primary} | {second_label} {secondary}")
