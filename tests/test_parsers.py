import unittest

from lottery_lab.models import DLT_RULE, SSQ_RULE
from lottery_lab.parsers import parse_dlt_page, parse_ssq_page


class ParserTests(unittest.TestCase):
    def test_parses_dlt_response_into_normalized_draw(self) -> None:
        payload = {
            "success": True,
            "errorCode": "0",
            "value": {
                "pageNo": 1,
                "pages": 2,
                "total": 2,
                "list": [
                    {
                        "lotteryDrawNum": "26091",
                        "lotteryDrawTime": "2026-08-12",
                        "lotteryDrawResult": "03 04 07 12 32 01 02",
                    }
                ],
            },
        }

        page = parse_dlt_page(payload)

        self.assertEqual(page.page_no, 1)
        self.assertEqual(page.total_pages, 2)
        self.assertEqual(page.total_records, 2)
        self.assertEqual(page.draws[0].game, DLT_RULE.code)
        self.assertEqual(page.draws[0].primary, (3, 4, 7, 12, 32))
        self.assertEqual(page.draws[0].secondary, (1, 2))

    def test_parses_ssq_jsonp_without_executing_callback(self) -> None:
        raw = (
            'jQuery1122_123({"pageNum":"1","pages":"3","total":"3",'
            '"resCode":"000000","data":[{"issue":"2026093",'
            '"openTime":"2026-08-13","frontWinningNum":"05 08 15 20 21 24",'
            '"backWinningNum":"09"}]})'
        )

        page = parse_ssq_page(raw)

        self.assertEqual(page.total_pages, 3)
        self.assertEqual(page.draws[0].game, SSQ_RULE.code)
        self.assertEqual(page.draws[0].primary, (5, 8, 15, 20, 21, 24))
        self.assertEqual(page.draws[0].secondary, (9,))

    def test_rejects_draw_with_wrong_number_count(self) -> None:
        payload = {
            "success": True,
            "errorCode": "0",
            "value": {
                "pageNo": 1,
                "pages": 1,
                "total": 1,
                "list": [
                    {
                        "lotteryDrawNum": "bad",
                        "lotteryDrawTime": "2026-08-12",
                        "lotteryDrawResult": "03 04 07 12 01 02",
                    }
                ],
            },
        }

        with self.assertRaisesRegex(ValueError, "bad"):
            parse_dlt_page(payload)

    def test_rejects_unsuccessful_upstream_response(self) -> None:
        with self.assertRaisesRegex(ValueError, "upstream"):
            parse_dlt_page({"success": False, "errorCode": "999", "errorMessage": "failed"})


if __name__ == "__main__":
    unittest.main()
