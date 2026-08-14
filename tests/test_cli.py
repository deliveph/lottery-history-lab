import contextlib
import io
import tempfile
import unittest
from pathlib import Path

from lottery_lab.cli import main
from lottery_lab.models import DLT_RULE, SSQ_RULE, Draw, GameRule
from lottery_lab.storage import save_history


def history(rule: GameRule) -> list[Draw]:
    if rule.code == "dlt":
        primary, secondary = (1, 7, 14, 22, 35), (2, 11)
    else:
        primary, secondary = (1, 6, 12, 19, 27, 33), (16,)
    return [
        Draw.create(rule, f"00{index}", f"2026-01-{index:02d}", primary, secondary)
        for index in range(1, 7)
    ][::-1]


class CliTests(unittest.TestCase):
    def test_generate_offline_prints_five_candidates_for_each_game(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            data_dir = Path(directory)
            save_history(data_dir, DLT_RULE, history(DLT_RULE))
            save_history(data_dir, SSQ_RULE, history(SSQ_RULE))
            output = io.StringIO()

            with contextlib.redirect_stdout(output):
                exit_code = main(
                    [
                        "generate",
                        "--offline",
                        "--data-dir",
                        str(data_dir),
                        "--seed",
                        "42",
                    ]
                )

            text = output.getvalue()
            self.assertEqual(exit_code, 0)
            self.assertIn("大乐透候选号码（5 组）", text)
            self.assertIn("双色球候选号码（5 组）", text)
            self.assertEqual(text.count("前区"), 5)
            self.assertEqual(text.count("红球"), 5)
            self.assertIn("模式 历史加权", text)
            self.assertIn("历史统计不能预测下一期", text)
            text.encode("gbk")

    def test_coverage_mode_is_available_from_offline_cli(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            data_dir = Path(directory)
            save_history(data_dir, DLT_RULE, history(DLT_RULE))
            save_history(data_dir, SSQ_RULE, history(SSQ_RULE))
            output = io.StringIO()

            with contextlib.redirect_stdout(output):
                exit_code = main(
                    [
                        "generate",
                        "--offline",
                        "--mode",
                        "coverage",
                        "--data-dir",
                        str(data_dir),
                        "--seed",
                        "42",
                    ]
                )

            self.assertEqual(exit_code, 0)
            self.assertIn("模式 低重叠覆盖", output.getvalue())


if __name__ == "__main__":
    unittest.main()
