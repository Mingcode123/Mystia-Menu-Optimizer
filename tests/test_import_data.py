import copy
import importlib.util
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location('prepare_data', Path(__file__).resolve().parents[1] / 'tools/prepare_data.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class ImportDataTests(unittest.TestCase):
    def fixture(self):
        return {'食材': [{'Name': 'A', 'Buy Price': 9, 'Icon': 'private-image'}, {'Name': 'B', 'Buy Price': 2}],
            '料理': [{'Name': 'dish', 'Cookware': 'pot', 'Sell Price': 8, 'Required Ingredients': 'A、A', 'Owned': 1}],
            '稀客': [{'Name': 'guest', 'Type': 'rare'}],
            '食材merchant_data': [
                {'Name': 'B', 'Average Buy Price': 9, 'Total Daily Quantity': 0},
                {'Name': 'A', 'Average Buy Price': 2, 'Total Daily Quantity': 12}]}

    def test_join_by_name_preserves_source_and_recipe_multiplicity(self):
        raw = self.fixture()
        original = copy.deepcopy(raw)
        data, report = module.normalize_sheets(raw)
        self.assertEqual([r['Buy Price'] for r in data['sheets']['食材']], [2, 9])
        self.assertEqual(len(report['price_corrections']), 2)
        self.assertNotIn('Icon', data['sheets']['食材'][0])
        self.assertEqual(data['sheets']['料理'][0]['Required Ingredients'], 'A、A')
        self.assertEqual(raw, original)

    def test_missing_price_is_unknown_not_free(self):
        raw = self.fixture()
        raw['食材merchant_data'][0]['Average Buy Price'] = '#DIV/0!'
        data, report = module.normalize_sheets(raw)
        self.assertIsNone(data['sheets']['食材'][1]['Buy Price'])
        self.assertEqual(data['sheets']['食材merchant_data'][0]['Total Daily Quantity'], 0)
        self.assertEqual(report['unknown_prices'], ['B'])

    def test_duplicate_or_missing_supply_rejected(self):
        for mutation in ('duplicate', 'missing', 'nonfinite'):
            raw = self.fixture()
            if mutation == 'duplicate':
                raw['食材merchant_data'].append(raw['食材merchant_data'][0])
            elif mutation == 'missing':
                raw['食材merchant_data'].pop()
            else:
                raw['食材merchant_data'][0]['Total Daily Quantity'] = float('nan')
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                module.normalize_sheets(raw)

    def test_symbolic_recipe_disabled_with_reason(self):
        raw = self.fixture()
        raw['料理'][0]['Required Ingredients'] = '任意'
        data, report = module.normalize_sheets(raw)
        self.assertEqual(data['sheets']['料理'][0]['Owned'], 0)
        self.assertIn('任意', report['disabled_recipes'][0]['reasons'][0])
