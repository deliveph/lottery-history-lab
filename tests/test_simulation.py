import unittest

from lottery_lab.models import DLT_RULE, SSQ_RULE, Draw
from lottery_lab.simulation import (
    IChingContext,
    generate_coverage_tickets,
    generate_iching_tickets,
    generate_tickets,
    iching_context_summary,
    score_numbers,
)


def sample_history() -> list[Draw]:
    draws = []
    for index in range(60):
        primary = tuple(sorted({1 + ((index + offset * 5) % 35) for offset in range(5)}))
        if len(primary) != 5:
            primary = (1, 8, 15, 22, 29)
        secondary = tuple(sorted({1 + (index % 12), 1 + ((index + 5) % 12)}))
        draws.append(
            Draw.create(
                DLT_RULE,
                f"{60 - index:03d}",
                f"2026-01-{1 + (index % 28):02d}",
                primary,
                secondary,
            )
        )
    return draws


class SimulationTests(unittest.TestCase):
    def test_seed_reproduces_five_distinct_valid_tickets(self) -> None:
        history = sample_history()

        first = generate_tickets(DLT_RULE, history, count=5, seed=20260814)
        second = generate_tickets(DLT_RULE, history, count=5, seed=20260814)

        self.assertEqual(first, second)
        self.assertEqual(len(first), 5)
        self.assertEqual(len(set(first)), 5)
        for ticket in first:
            self.assertEqual(len(ticket.primary), 5)
            self.assertEqual(len(ticket.secondary), 2)
            self.assertEqual(len(set(ticket.primary)), 5)
            self.assertEqual(len(set(ticket.secondary)), 2)
            self.assertTrue(all(1 <= number <= 35 for number in ticket.primary))
            self.assertTrue(all(1 <= number <= 12 for number in ticket.secondary))

    def test_scoring_assigns_a_positive_weight_to_every_ball(self) -> None:
        scores = score_numbers(sample_history(), DLT_RULE.primary_max, field="primary")

        self.assertEqual(set(scores), set(range(1, 36)))
        self.assertTrue(all(weight > 0 for weight in scores.values()))

    def test_rejects_empty_history(self) -> None:
        with self.assertRaisesRegex(ValueError, "history"):
            generate_tickets(DLT_RULE, [], count=5, seed=1)

    def test_coverage_mode_balances_five_ticket_portfolio(self) -> None:
        dlt = generate_coverage_tickets(DLT_RULE, count=5, seed=20260814)
        ssq = generate_coverage_tickets(SSQ_RULE, count=5, seed=20260814)

        self.assertEqual(dlt, generate_coverage_tickets(DLT_RULE, count=5, seed=20260814))
        self.assertEqual(len(set(dlt)), 5)
        self.assertEqual(len({number for ticket in dlt for number in ticket.primary}), 25)
        self.assertEqual(len({number for ticket in dlt for number in ticket.secondary}), 10)
        self.assertEqual(len({number for ticket in ssq for number in ticket.primary}), 30)
        self.assertEqual(len({number for ticket in ssq for number in ticket.secondary}), 5)

    def test_iching_mode_is_reproducible_and_date_specific(self) -> None:
        dlt = generate_iching_tickets(
            DLT_RULE, target_date="2026-08-31", issue="26099", count=5
        )
        repeated = generate_iching_tickets(
            DLT_RULE, target_date="2026-08-31", issue="26099", count=5
        )
        next_date = generate_iching_tickets(
            DLT_RULE, target_date="2026-09-02", issue="26100", count=5
        )
        ssq = generate_iching_tickets(
            SSQ_RULE, target_date="2026-09-01", issue="2026101", count=5
        )

        self.assertEqual(dlt, repeated)
        self.assertNotEqual(dlt, next_date)
        self.assertEqual(len(set(dlt)), 5)
        self.assertEqual(len({number for ticket in dlt for number in ticket.primary}), 25)
        self.assertEqual(len({number for ticket in dlt for number in ticket.secondary}), 10)
        self.assertEqual(len(set(ssq)), 5)
        self.assertEqual(len({number for ticket in ssq for number in ticket.primary}), 30)
        self.assertEqual(len({number for ticket in ssq for number in ticket.secondary}), 5)

    def test_iching_mode_rejects_invalid_date_and_issue(self) -> None:
        with self.assertRaisesRegex(ValueError, "target date"):
            generate_iching_tickets(
                DLT_RULE, target_date="2026-02-30", issue="26099", count=5
            )
        with self.assertRaisesRegex(ValueError, "issue"):
            generate_iching_tickets(
                DLT_RULE, target_date="2026-08-31", issue="not-a-number", count=5
            )

    def test_iching_context_is_reproducible_and_each_input_affects_mapping(self) -> None:
        base_inputs = {
            "draw_time": "21:25",
            "cast_at": "2026-09-07T10:30:00+08:00",
            "lunar_birth_date": "1993-01-12",
            "birth_time": "05:30",
            "location": "上海市",
            "latitude": 31.2304,
            "longitude": 121.4737,
            "direction": "东南",
            "wealth_direction": "南",
        }
        context = IChingContext.create(**base_inputs)
        baseline = generate_iching_tickets(
            DLT_RULE,
            target_date="2026-09-07",
            issue="26102",
            context=context,
        )

        self.assertEqual(
            baseline,
            generate_iching_tickets(
                DLT_RULE,
                target_date="2026-09-07",
                issue="26102",
                context=context,
            ),
        )
        variants = {
            "draw time": {"draw_time": "21:26"},
            "cast time": {"cast_at": "2026-09-07T10:30:01+08:00"},
            "lunar birth date": {"lunar_birth_date": "1993-01-13"},
            "birth time": {"birth_time": "07:30"},
            "location": {"location": "北京市"},
            "coordinates": {"latitude": 39.9042, "longitude": 116.4074},
            "direction": {"direction": "西北"},
            "wealth direction": {"wealth_direction": "北"},
        }
        for label, changes in variants.items():
            with self.subTest(label=label):
                changed_context = IChingContext.create(**(base_inputs | changes))
                self.assertNotEqual(
                    baseline,
                    generate_iching_tickets(
                        DLT_RULE,
                        target_date="2026-09-07",
                        issue="26102",
                        context=changed_context,
                    ),
                )

    def test_iching_context_validates_coordinates_and_describes_missing_birth_time(self) -> None:
        with self.assertRaisesRegex(ValueError, "latitude and longitude"):
            IChingContext.create(
                draw_time="21:15",
                cast_at="2026-09-07T10:30:00+08:00",
                latitude=31.2304,
            )

        context = IChingContext.create(
            draw_time="21:15",
            cast_at="2026-09-07T10:30:00+08:00",
            lunar_birth_date="1993-01-12",
        )
        summary = iching_context_summary(context, target_date="2026-09-08")
        self.assertIn("开奖 21:15（亥时）", summary)
        self.assertIn("农历生辰 1993-01-12", summary)
        self.assertIn("出生时辰 未提供（非完整八字）", summary)
        self.assertIn("财位", summary)


if __name__ == "__main__":
    unittest.main()
