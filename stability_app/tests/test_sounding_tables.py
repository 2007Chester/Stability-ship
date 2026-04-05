"""Таблицы sounding → тонны."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sounding_tables import tons_from_sounding_mm


class TestSoundingTables(unittest.TestCase):
    def test_interp_midpoint(self):
        pts = [(0.0, 0.0), (10000.0, 100.0)]
        self.assertAlmostEqual(tons_from_sounding_mm(5000.0, pts), 50.0, places=5)

    def test_interp_clamp(self):
        pts = [(100.0, 1.0), (1000.0, 10.0)]
        self.assertAlmostEqual(tons_from_sounding_mm(50.0, pts), 1.0, places=5)
        self.assertAlmostEqual(tons_from_sounding_mm(2000.0, pts), 10.0, places=5)

    def test_need_two_points(self):
        self.assertIsNone(tons_from_sounding_mm(100.0, [(0.0, 0.0)]))
        self.assertIsNone(tons_from_sounding_mm(100.0, []))


if __name__ == "__main__":
    unittest.main()
