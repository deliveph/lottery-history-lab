import unittest

from lottery_lab.models import DLT_RULE, SSQ_RULE, Draw
from lottery_lab.simulation import (
    generate_coverage_tickets,
    generate_iching_tickets,
    generate_tickets,
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


if __name__ == "__main__":
    unittest.main()
