"""
Пресет «В грузу (из Excel)» — эталонные суммы и проверка согласованности с расчётом в коде.

Реальный Excel может отличаться (другая система Xг, LCF, GG₀, FSC, таблица KN).
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from cargo_excel_data import ROWS_CARGO_IN_GRUZ
from excel_ui import COL_KG, COL_MASS, COL_NAME, COL_X, trim_table_excel_with_total, x_g_to_from_ap
from ship_data import SHIP
from stability import draft_from_displacement, gm_metacentric, imo749_intact


class TestCargoInGruzPreset(unittest.TestCase):
    """Данные строк в точности как в app.py → defaults['В грузу (из Excel)']."""

    @classmethod
    def df(cls) -> pd.DataFrame:
        return pd.DataFrame([dict(r) for r in ROWS_CARGO_IN_GRUZ])

    def test_totals_match_excel_row_midship(self):
        """Как в приложении по умолчанию: Xг от миделя → LCG от кормы."""
        df = self.df()
        m = df[COL_MASS].values.astype(float)
        x = df[COL_X].values.astype(float)
        k = df[COL_KG].values.astype(float)
        delta = float(m.sum())
        kg = float((m * k).sum() / delta)
        lbp = float(SHIP.get("lbp_m", 96.78))
        x_ap = x_g_to_from_ap(x, lbp, from_midship=True)
        lcg = float((m * x_ap).sum() / delta)
        tbl = trim_table_excel_with_total(df, x_from_midship=True, lbp_m=lbp)
        last = tbl.iloc[-1]
        self.assertAlmostEqual(last[COL_MASS], delta, places=6)
        self.assertAlmostEqual(last[COL_KG], kg, places=6)
        self.assertAlmostEqual(last[COL_X], lcg, places=4)
        self.assertAlmostEqual(lcg, 49.098, places=2)

    def test_reference_hydro_imo(self):
        """Эталон при θзал=55°, FSC=0, GG₀=0 (как в приложении по умолчанию)."""
        df = self.df()
        m = df[COL_MASS].values
        k = df[COL_KG].values
        delta = float(m.sum())
        kg = float((m * k).sum() / delta)
        kg0 = kg
        t_mean = draft_from_displacement(delta)
        gm = gm_metacentric(delta, kg0, 0.0)
        crit, meta = imo749_intact(delta, kg0, kg0, 0.0, 55.0)

        self.assertAlmostEqual(delta, 8867.0, places=3)
        self.assertAlmostEqual(kg, 5.643780, places=4)
        self.assertAlmostEqual(t_mean, 4.351938, places=3)
        self.assertGreater(gm, 8.5)
        self.assertAlmostEqual(meta["gz_30"], 1.681970, places=3)
        self.assertTrue(all(c.ok for c in crit), msg=[(c.code, c.actual) for c in crit if not c.ok])

        phis = np.array(meta["phis_deg"])
        gzs = np.array(meta["gz_m"])
        i30 = int(np.argmin(np.abs(phis - 30.0)))
        self.assertAlmostEqual(gzs[i30], meta["gz_30"], places=5)


if __name__ == "__main__":
    unittest.main()
