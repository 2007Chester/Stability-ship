"""
Цистерны из разд. 6 буклета остойчивости: LCG от шп. кормы (м), KG (VCG над килем, м) при 100%.
Используются для моментов при заданной пользователем массе в танке (упрощение: LCG/KG танка постоянны).
"""

from __future__ import annotations

# (обозначение, LCG от кормы м, KG м, ориентир макс. массы т при 100%)
BOOKLET_TANKS: list[tuple[str, float, float, float]] = [
    ("FUEL-PTS.P (топливо, лев)", 18.288, 3.657, 94.78),
    ("FUEL-STB.S (топливо, прав)", 18.288, 3.657, 94.78),
    ("FRESH-PTS.P (пресная, лев)", 82.216, 3.113, 110.29),
    ("FRESH-STB.S (пресная, прав)", 82.216, 3.113, 110.29),
    ("BW-01 PTS-FWD.P (балласт нос, лев)", 87.134, 3.439, 221.76),
    ("BW-01 STB-FWD.S (балласт нос, прав)", 87.134, 3.439, 221.76),
    ("FORE PEAK SW.C (носовой пик)", 93.102, 4.359, 101.62),
    ("BW-02 PTS-AFT.P (балласт корма, лев)", 9.467, 3.666, 212.31),
    ("BW-02 STB-AFT.S (балласт корма, прав)", 9.467, 3.666, 212.31),
]


def booklet_default_lcg_kg() -> tuple[list[float], list[float]]:
    """LCG от шп. кормы (м) и KG (м) из буклета по порядку stab_t0…stab_t8."""
    lcgs = [float(t[1]) for t in BOOKLET_TANKS]
    kgs = [float(t[2]) for t in BOOKLET_TANKS]
    return lcgs, kgs


def x_table_from_lcg_ap(lcg_ap_m: float, lbp_m: float, *, x_from_midship: bool) -> float:
    """X для таблицы: от миделя (+к носу) или от кормы — как в excel_ui."""
    if x_from_midship:
        return float(lcg_ap_m) - float(lbp_m) / 2.0
    return float(lcg_ap_m)
