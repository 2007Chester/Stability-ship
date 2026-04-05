"""Тесты расчёта GZ и критериев ИМО (ошибка searchsorted при φ = первому углу таблицы)."""

from __future__ import annotations

import math
import sys
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from rs_criteria import gz_at
from stability import (
    build_fine_gz,
    cargo_mass_from_drafts,
    displacement_from_draft,
    drafts_fwd_aft_from_lcg,
    gm_metacentric,
    gz0_at,
    imo749_intact,
    mctc_t_m_per_cm,
)
from ship_data import GZ_ANGLES_DEG, GZ_DISPLACEMENTS


class TestGz0At(unittest.TestCase):
    def test_first_table_angle_nonzero(self):
        """При φ, равном первому углу таблицы (5°), GZ₀ не должен обнуляться."""
        delta = 8000.0
        g5 = gz0_at(delta, 5.0)
        g10 = gz0_at(delta, 10.0)
        self.assertGreater(g5, 0.01, "GZ₀(5°) должно быть > 0 (баг searchsorted side=left)")
        self.assertGreater(g10, g5 * 0.5, "GZ₀(10°) должно быть сопоставимо с кривой")

    def test_interpolation_between_nodes(self):
        delta = GZ_DISPLACEMENTS[len(GZ_DISPLACEMENTS) // 2]
        g7 = gz0_at(delta, 7.0)
        g5 = gz0_at(delta, 5.0)
        g10 = gz0_at(delta, 10.0)
        self.assertGreater(g7, min(g5, g10) - 1e-6)
        self.assertLess(g7, max(g5, g10) + 1e-6)

    def test_small_angle_ramp(self):
        """0 < φ < 5°: линейный подъём к значению на 5°."""
        delta = 5000.0
        g2 = gz0_at(delta, 2.0)
        g5 = gz0_at(delta, 5.0)
        self.assertAlmostEqual(g2 / g5, 2.0 / 5.0, places=5)

    def test_gz_matches_gm_small_angle(self):
        """На малых углах GZ ≈ GM·sin(φ) с точностью порядка 15 % (табличная кривая)."""
        delta = 8000.0
        kg = 5.5
        gm = gm_metacentric(delta, kg, 0.0)
        phi = math.radians(5.0)
        gz = gz0_at(delta, 5.0) - kg * math.sin(phi)
        gz_lin = gm * math.sin(phi)
        rel = abs(gz - gz_lin) / max(abs(gz_lin), 0.05)
        self.assertLess(rel, 0.25, "GZ(5°) должно быть близко к GM·sin(5°)")


class TestBuildFineGz(unittest.TestCase):
    def test_range_includes_0_and_60(self):
        phis, gzs = build_fine_gz(7500.0, 5.0, 0.5)
        self.assertEqual(phis[0], 0.0)
        self.assertGreaterEqual(float(phis[-1]), 60.0)
        self.assertEqual(len(phis), len(gzs))

    def test_no_spurious_max_at_zero(self):
        """Максимум GZ не должен сидеть в φ=0 при нормальной загрузке."""
        delta = 8000.0
        kg = 5.5
        phis, gzs = build_fine_gz(delta, kg, 0.5)
        imax = int(gzs.argmax())
        self.assertGreater(float(phis[imax]), 5.0, "макс. GZ обычно не при 0°")


class TestLongitudinalDrafts(unittest.TestCase):
    def test_mctc_positive(self):
        m = mctc_t_m_per_cm(8000.0, 96.78, 24.384, 3.5)
        self.assertGreater(m, 0.0)

    def test_trim_stern_when_lcg_aft(self):
        """LCG кормее LCF (меньше x от кормы) → корма глубже."""
        lbp = 96.78
        lcf = lbp / 2.0
        t_mean = 3.5
        # G ближе к корме, чем LCF
        r = drafts_fwd_aft_from_lcg(8000.0, t_mean, 20.0, lbp_m=lbp, beam_m=24.384, lcf_from_ap_m=lcf)
        self.assertGreater(r.t_aft_m, r.t_fwd_m)
        self.assertGreater(r.trim_cm, 0.0)

    def test_equal_lcg_lcf_no_trim(self):
        lbp = 96.78
        lcf = lbp / 2.0
        r = drafts_fwd_aft_from_lcg(5000.0, 3.0, lcf, lbp_m=lbp, beam_m=24.384, lcf_from_ap_m=lcf)
        self.assertAlmostEqual(r.trim_cm, 0.0, places=3)
        self.assertAlmostEqual(r.t_fwd_m, r.t_aft_m, places=5)


class TestCargoFromDrafts(unittest.TestCase):
    def test_equal_drafts_matches_coal_formula(self):
        """Та же логика, что M_уголь = Δ(T_ср) − M_прочее при равных осадках."""
        t = 4.35
        m_wo = 2367.0
        d, tm, cargo = cargo_mass_from_drafts(t, t, m_wo)
        self.assertAlmostEqual(tm, t, places=6)
        self.assertAlmostEqual(d, displacement_from_draft(t), places=3)
        self.assertAlmostEqual(cargo, max(d - m_wo, 0.0), places=3)


class TestGzChartMatchesFormula(unittest.TestCase):
    """График GZ на вкладке строится из meta = build_fine_gz — совпадает с GZ = GZ₀ − KG₀·sin φ."""

    def test_build_fine_gz_equals_gz_at(self):
        delta = 7800.0
        kg0 = 5.4
        phis, gzs = build_fine_gz(delta, kg0, 0.5)
        for p, g in zip(phis, gzs):
            g_ref = gz_at(delta, kg0, float(p))
            self.assertAlmostEqual(float(g), g_ref, places=9)

    def test_imo749_meta_matches_build_fine_gz(self):
        delta = 8000.0
        kg0 = 5.5
        _, meta = imo749_intact(delta, kg0, 0.0, 55.0)
        phis_b, gzs_b = build_fine_gz(delta, kg0, 0.5)
        self.assertTrue(
            np.allclose(np.asarray(meta["phis_deg"], float), np.asarray(phis_b, float))
        )
        self.assertTrue(np.allclose(np.asarray(meta["gz_m"], float), gzs_b))


class TestImo749(unittest.TestCase):
    def test_runs_without_nan(self):
        crit, meta = imo749_intact(8000.0, 5.5, 0.0, 55.0)
        self.assertEqual(len(crit), 5)
        self.assertFalse(math.isnan(meta["a_0_15"]))
        self.assertGreater(meta["a_0_15"], 0.0)


if __name__ == "__main__":
    unittest.main()
