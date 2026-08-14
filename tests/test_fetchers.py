import json
import unittest

from lottery_lab.fetchers import fetch_dlt_history, fetch_ssq_history


class FetcherTests(unittest.TestCase):
    def test_fetches_every_dlt_page_and_returns_unique_draws(self) -> None:
        calls: list[str] = []

        def get_text(url: str, referer: str) -> str:
            calls.append(url)
            page_no = 2 if "pageNo=2" in url else 1
            rows = [
                {
                    "lotteryDrawNum": "002" if page_no == 1 else "001",
                    "lotteryDrawTime": "2026-01-02" if page_no == 1 else "2026-01-01",
                    "lotteryDrawResult": "01 02 03 04 05 01 02",
                }
            ]
            return json.dumps(
                {
                    "success": True,
                    "errorCode": "0",
                    "value": {
                        "pageNo": page_no,
                        "pages": 2,
                        "total": 2,
                        "list": rows,
                    },
                }
            )

        draws = fetch_dlt_history(get_text=get_text)

        self.assertEqual([draw.issue for draw in draws], ["002", "001"])
        self.assertEqual(len(calls), 2)

    def test_fetches_all_ssq_pages_from_jsonp(self) -> None:
        def get_text(url: str, referer: str) -> str:
            page_no = 2 if "pageNum=2" in url else 1
            row = {
                "issue": f"202600{3 - page_no}",
                "openTime": f"2026-01-0{3 - page_no}",
                "frontWinningNum": "01 02 03 04 05 06",
                "backWinningNum": "07",
            }
            return "callback(" + json.dumps(
                {
                    "pageNum": str(page_no),
                    "pages": "2",
                    "total": "2",
                    "resCode": "000000",
                    "data": [row],
                }
            ) + ")"

        draws = fetch_ssq_history(get_text=get_text)

        self.assertEqual(len(draws), 2)
        self.assertEqual(draws[0].issue, "2026002")

    def test_rejects_incomplete_history(self) -> None:
        def get_text(url: str, referer: str) -> str:
            return json.dumps(
                {
                    "success": True,
                    "errorCode": "0",
                    "value": {
                        "pageNo": 1,
                        "pages": 1,
                        "total": 2,
                        "list": [
                            {
                                "lotteryDrawNum": "001",
                                "lotteryDrawTime": "2026-01-01",
                                "lotteryDrawResult": "01 02 03 04 05 01 02",
                            }
                        ],
                    },
                }
            )

        with self.assertRaisesRegex(RuntimeError, "expected 2"):
            fetch_dlt_history(get_text=get_text)


if __name__ == "__main__":
    unittest.main()

