"""Run the Python regression suite from a checkout without installation."""
import sys
import unittest
from pathlib import Path

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / 'src'))
suite = unittest.defaultTestLoader.discover(str(root / 'tests'))
if __name__ == '__main__':
    raise SystemExit(not unittest.TextTestRunner(verbosity=2).run(suite).wasSuccessful())
