"""Run every test: python tests/run_tests.py  (standard library only, nothing to install)."""
import sys
import unittest
from pathlib import Path

if __name__ == "__main__":
    burasi = Path(__file__).resolve().parent
    sys.path.insert(0, str(burasi))
    takim = unittest.defaultTestLoader.discover(str(burasi), pattern="test_*.py", top_level_dir=str(burasi))
    sonuc = unittest.TextTestRunner(verbosity=2).run(takim)
    sys.exit(0 if sonuc.wasSuccessful() else 1)
