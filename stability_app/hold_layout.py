"""
Геометрия грузового трюма для схемы (вид сбоку).

Размеры судна — из `ship_data.SHIP` (буклет / Kimtrans SPB 3210).
Границы трюма по длине — ориентир по типовой компоновке и расположению цистерн
разд. 6 (`tank_booklet`): кормовая зона до ~20 м, носовые BW-01 / форпик с ~86 м.
При появлении точных координат с чертежа GA (P0532-G1) — заменить константы ниже.
"""

from __future__ import annotations

from ship_data import SHIP

LOA_M = float(SHIP["loa_m"])
LBP_M = float(SHIP["lbp_m"])
BEAM_M = float(SHIP["beam_m"])
DEPTH_M = float(SHIP["depth_m"])

# LCG от кормы (м): кормовой и носовой борта грузового трюма
HOLD_LCG_AP_AFT_M = 22.0
HOLD_LCG_AP_FWD_M = 88.0

NUM_HOLD_SECTIONS = 20

# Документация проекта (docs/10-chertezhi-ga-i-rina.md)
FRAME_SPACING_MAIN_M = 1.8288


def hold_length_m() -> float:
    return float(HOLD_LCG_AP_FWD_M - HOLD_LCG_AP_AFT_M)


def section_edges_from_ap_m() -> list[float]:
    """Границы 20 секций: координаты от кормы (м), len = 21."""
    a, b = float(HOLD_LCG_AP_AFT_M), float(HOLD_LCG_AP_FWD_M)
    n = NUM_HOLD_SECTIONS
    return [a + (b - a) * i / n for i in range(n + 1)]


def section_centers_from_ap_m() -> list[float]:
    """Центры секций 1..20 (от кормы, м)."""
    edges = section_edges_from_ap_m()
    return [0.5 * (edges[i] + edges[i + 1]) for i in range(NUM_HOLD_SECTIONS)]


def section_length_m() -> float:
    return hold_length_m() / float(NUM_HOLD_SECTIONS)


def waterline_draft_at_x_from_ap_m(x: float, t_aft: float, t_fwd: float, lbp: float) -> float:
    """Осадка по длине при линейном дифференте (нос — x = lbp, корма — x = 0)."""
    x = max(0.0, min(float(lbp), float(x)))
    return float(t_aft) + (float(t_fwd) - float(t_aft)) * (x / float(lbp))


def coal_uniform_layer_height_m(mass_t: float, rho_t_m3: float) -> tuple[float, float, float]:
    """
    Ровный слой угля на всё дно трюма (упрощение: прямоугольник L×B).

    Возвращает (высота слоя м, т на секцию, объём м³).
    """
    L = hold_length_m()
    B = BEAM_M
    if L <= 0 or B <= 0 or rho_t_m3 <= 0 or mass_t <= 0:
        return 0.0, 0.0, 0.0
    vol = float(mass_t) / float(rho_t_m3)
    h = vol / (L * B)
    t_sec = float(mass_t) / float(NUM_HOLD_SECTIONS)
    return h, t_sec, vol
