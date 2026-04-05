"""Таблица загрузки в стиле Excel."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from excel_ui import (
    COL_KG,
    COL_MASS,
    COL_NAME,
    COL_X,
    normalize_load_columns,
    table_x_from_lcg_ap,
    trim_table_excel_with_total,
    x_g_to_from_ap,
)


class TestExcelUi(unittest.TestCase):
    def test_legacy_rename(self):
        df = pd.DataFrame([{"Наименование": "a", "Масса_т": 10.0, "Xг_м": 2.0, "KG_м": 3.0}])
        n = normalize_load_columns(df)
        self.assertIn("Масса, т", n.columns)
        self.assertEqual(float(n["Масса, т"].iloc[0]), 10.0)

    def test_total_lcg_kg(self):
        df = pd.DataFrame(
            [
                {COL_NAME: "A", COL_MASS: 100.0, COL_X: 0.0, COL_KG: 4.0},
                {COL_NAME: "B", COL_MASS: 100.0, COL_X: 10.0, COL_KG: 6.0},
            ]
        )
        t = trim_table_excel_with_total(df)
        last = t.iloc[-1]
        self.assertEqual(last[COL_NAME], "ИТОГО:")
        self.assertAlmostEqual(last[COL_MASS], 200.0)
        self.assertAlmostEqual(last[COL_X], 5.0)  # LCG
        self.assertAlmostEqual(last[COL_KG], 5.0)  # KG

    def test_lcg_ap_roundtrip_midship(self):
        lbp = 96.78
        for xm in (-10.0, 0.0, 20.0, 40.0):
            ap = float(x_g_to_from_ap(np.array([xm]), lbp, from_midship=True)[0])
            back = table_x_from_lcg_ap(ap, lbp, from_midship=True)
            self.assertAlmostEqual(back, xm, places=5)

    def test_lcg_ap_roundtrip_from_ap(self):
        lbp = 96.78
        for xap in (5.0, 48.39, 90.0):
            back = table_x_from_lcg_ap(xap, lbp, from_midship=False)
            self.assertAlmostEqual(back, xap)


if __name__ == "__main__":
    unittest.main()
