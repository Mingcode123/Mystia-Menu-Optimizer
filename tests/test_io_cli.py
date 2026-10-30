import contextlib
import copy
import io
import json
from pathlib import Path
import tempfile
import unittest

from mystia_planner.cli import main
from mystia_planner.io import dataset_from_dict


def payload():
    return {
        "format": "mystia-planner-data/v1",
        "metadata": {"kind": "synthetic test"},
        "sheets": {
            "食材": [{"Name": "base", "Tags": "hidden"}],
            "食材merchant_data": [{"Name": "base", "Total Daily Quantity": 20}],
            "料理": [{"Name": "dish", "Tags": "a、b、c", "Cookware": "pot", "Sell Price": 30, "Required Ingredients": "base", "Owned": 1}],
            "稀客": [{"Name": "guest", "Preferred Tags": "a、b、c", "Disliked Tags": "", "Budget": "10–20"}],
        },
    }


class InputAndCliTests(unittest.TestCase):
    def test_schema_preserves_repeated_base_ingredients(self):
        value = payload()
        value["sheets"]["料理"][0]["Required Ingredients"] = "base、base"
        data = dataset_from_dict(value)
        self.assertEqual(data.dishes[0].required_ingredients, ("base", "base"))

    def test_continuation_guests_are_merged(self):
        value = payload()
        value["sheets"]["稀客"].append({"Name": "", "Preferred Tags": "c、d", "Disliked Tags": "bad"})
        data = dataset_from_dict(value)
        self.assertEqual(data.guests[0].preferred_tags, ("a", "b", "c", "d"))
        self.assertEqual(data.guests[0].disliked_tags, frozenset({"bad"}))

    def test_missing_supply_and_unknown_owned_ingredients_are_rejected(self):
        value = payload()
        value["sheets"]["食材merchant_data"][0]["Name"] = "wrong-name"
        with self.assertRaisesRegex(ValueError, "missing named supply"):
            dataset_from_dict(value)
        value = payload()
        value["sheets"]["料理"][0]["Required Ingredients"] = "unknown"
        with self.assertRaisesRegex(ValueError, "unknown base ingredient"):
            dataset_from_dict(value)
        value["sheets"]["料理"][0]["Owned"] = 0
        self.assertFalse(dataset_from_dict(value).dishes[0].owned)

    def test_invalid_and_duplicate_values_are_rejected(self):
        for quantity in (None, "#DIV/0!", float("nan"), -1, True):
            value = payload()
            value["sheets"]["食材merchant_data"][0]["Total Daily Quantity"] = quantity
            with self.subTest(quantity=quantity), self.assertRaises(ValueError):
                dataset_from_dict(value)
        value = payload()
        value["sheets"]["食材"].append(copy.deepcopy(value["sheets"]["食材"][0]))
        with self.assertRaisesRegex(ValueError, "duplicate Name"):
            dataset_from_dict(value)

    def test_cli_creates_json_csv_without_any_prompt(self):
        with tempfile.TemporaryDirectory() as directory:
            directory = Path(directory)
            source = directory / "input.json"
            output = directory / "out" / "plan.json"
            csv = directory / "out" / "plan.csv"
            source.write_text(json.dumps(payload(), ensure_ascii=False), encoding="utf-8")
            with contextlib.redirect_stdout(io.StringIO()):
                code = main(["--input", str(source), "--output", str(output), "--csv", str(csv), "--guest", "guest", "--cookware-count", "1", "--orders-per-day", "3"])
            self.assertEqual(code, 0)
            report = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(report["summary"]["planned_count"], 1)
            self.assertEqual(report["guests"][0]["plan"]["supply_margin"], 17)
            self.assertIn("dish", csv.read_text(encoding="utf-8-sig"))

    def test_cli_errors_do_not_overwrite_input_or_create_output(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "input.json"
            output = Path(directory) / "plan.json"
            original = json.dumps(payload())
            source.write_text(original, encoding="utf-8")
            with contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(main(["--input", str(source), "--output", str(source)]), 2)
                self.assertEqual(main(["--input", str(source), "--output", str(output), "--orders-per-day", "0"]), 2)
            self.assertEqual(source.read_text(encoding="utf-8"), original)
            self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
