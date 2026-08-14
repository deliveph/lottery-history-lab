import json
import tempfile
import unittest
from pathlib import Path

from lottery_lab.models import DLT_RULE, Draw
from lottery_lab.storage import load_history, save_history


class StorageTests(unittest.TestCase):
    def test_saves_json_and_csv_and_loads_normalized_draws(self) -> None:
        draws = [
            Draw.create(
                DLT_RULE,
                "26091",
                "2026-08-12",
                (3, 4, 7, 12, 32),
                (1, 2),
            )
        ]
        with tempfile.TemporaryDirectory() as directory:
            data_dir = Path(directory)

            paths = save_history(data_dir, DLT_RULE, draws)
            loaded = load_history(data_dir, DLT_RULE)

            self.assertTrue(paths.json.exists())
            self.assertTrue(paths.csv.exists())
            self.assertEqual(loaded, draws)
            self.assertIn("primary", paths.csv.read_text(encoding="utf-8-sig").splitlines()[0])

    def test_rejects_non_object_draw_in_cache_with_clear_error(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            data_dir = Path(directory)
            path = data_dir / "dlt_history.json"
            path.write_text(
                json.dumps({"game": "dlt", "draws": ["corrupt"]}), encoding="utf-8"
            )

            with self.assertRaisesRegex(ValueError, "draw row"):
                load_history(data_dir, DLT_RULE)


if __name__ == "__main__":
    unittest.main()
