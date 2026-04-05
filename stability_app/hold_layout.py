"""
Геометрия грузового трюма для схемы (вид сбоку).

Размеры судна — из `ship_data.SHIP` (буклет / Kimtrans SPB 3210).
Границы трюма по длине — ориентир по типовой компоновке и расположению цистерн
разд. 6 (`tank_booklet`): кормовая зона до ~20 м, носовые BW-01 / форпик с ~86 м.
При появлении точных координат с чертежа GA (P0532-G1) — заменить константы ниже.
"""

from __future__ import annotations

from typing import Any

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

# --- Ориентиры по GA (Kimtrans SPB / баржи серии); уточнить по «General Arrangement» P0532-G1 ---
# Внутреннее дно трюма (верх двойного дна / tank top) над килем, м
INNER_BOTTOM_ABOVE_KEEL_M = 1.0
# Комингсы грузового люка над линией главной палубы у борта, м (высота борта коминга)
COAMING_HEIGHT_ABOVE_DECK_M = 0.85


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


def main_deck_above_keel_m() -> float:
    """Конструктивная главная палуба (молдинг D)."""
    return float(DEPTH_M)


def hold_moulded_depth_m() -> float:
    """
    Глубина трюма **под главной палубой**: от линии главной палубы до внутреннего дна (м).
    Выше главной палубы — комингсы люка; ниже — грузовой трюм до дна.
    """
    return float(DEPTH_M) - float(INNER_BOTTOM_ABOVE_KEEL_M)


def coaming_top_above_keel_m() -> float:
    """Верх грузового коминга над килем (палуба + высота коминга)."""
    return float(DEPTH_M) + float(COAMING_HEIGHT_ABOVE_DECK_M)


def hold_stowage_height_limit_m() -> float:
    """Максимальная высота насыпи от внутреннего дна до верха комингсов, м."""
    return max(0.0, coaming_top_above_keel_m() - float(INNER_BOTTOM_ABOVE_KEEL_M))


def coal_uniform_stowage_m(mass_t: float, rho_t_m3: float) -> dict[str, Any]:
    """
    Ровный слой угля по площади L×B от внутреннего дна; верх груза не выше верха комингсов.

    **Выше главной палубы** — борт комингсов; **от палубы вверх** до верха комингсов — `COAMING_HEIGHT_ABOVE_DECK_M`.
    Зазор **от поверхности груза вверх** до верха комингсов — `clearance_cooming_m`.
    """
    L = hold_length_m()
    B = BEAM_M
    y_tt = float(INNER_BOTTOM_ABOVE_KEEL_M)
    y_deck = main_deck_above_keel_m()
    h_lim = hold_stowage_height_limit_m()
    hd = hold_moulded_depth_m()
    if L <= 0 or B <= 0 or rho_t_m3 <= 0 or mass_t <= 0:
        return {
            "h_from_inner_bottom_m": 0.0,
            "clearance_cooming_m": h_lim,
            "volume_m3": 0.0,
            "tons_per_section": 0.0,
            "capped_by_cooming": False,
            "h_if_unlimited_m": 0.0,
            "hold_depth_moulded_m": float(hd),
            "cargo_surface_below_main_deck_m": float(hd),
            "coaming_height_above_main_deck_m": float(COAMING_HEIGHT_ABOVE_DECK_M),
        }
    vol = float(mass_t) / float(rho_t_m3)
    h_need = vol / (L * B)
    capped = h_need > h_lim + 1e-9
    h = min(h_need, h_lim)
    clearance = max(0.0, h_lim - h)
    t_sec = float(mass_t) / float(NUM_HOLD_SECTIONS)
    # Насколько поверхность груза ниже линии главной палубы (м); «вверх» от груза — к палубе и комингсам
    cargo_below_deck = max(0.0, float(y_deck) - y_tt - float(h))
    return {
        "h_from_inner_bottom_m": float(h),
        "clearance_cooming_m": float(clearance) if not capped else 0.0,
        "volume_m3": float(vol),
        "tons_per_section": float(t_sec),
        "capped_by_cooming": capped,
        "h_if_unlimited_m": float(h_need),
        "hold_depth_moulded_m": float(hd),
        "cargo_surface_below_main_deck_m": float(cargo_below_deck),
        "coaming_height_above_main_deck_m": float(COAMING_HEIGHT_ABOVE_DECK_M),
    }


def coal_uniform_layer_height_m(mass_t: float, rho_t_m3: float) -> tuple[float, float, float]:
    """Обратная совместимость: высота от **киля** (старое API), т/секция, объём."""
    d = coal_uniform_stowage_m(mass_t, rho_t_m3)
    h_keel = float(INNER_BOTTOM_ABOVE_KEEL_M) + float(d["h_from_inner_bottom_m"])
    return h_keel, float(d["tons_per_section"]), float(d["volume_m3"])
