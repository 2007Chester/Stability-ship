"""Расчёт статической остойчивости и критериев ИМО A.749 (неповреждённое судно)."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Sequence

import numpy as np

from ship_data import (
    GZ_ANGLES_DEG,
    GZ0_TABLE,
    GZ_DISPLACEMENTS,
    HYDRO_DISP,
    HYDRO_KB,
    HYDRO_KMT,
    HYDRO_T,
    SHIP,
)

G = 9.81


def _interp(x: Sequence[float], y: Sequence[float], xi: float) -> float:
    return float(np.interp(xi, np.asarray(x, float), np.asarray(y, float)))


def displacement_from_draft(t_m: float) -> float:
    """Водоизмещение (т) по осадке от ОП (м), дифферент 0."""
    return _interp(HYDRO_T, HYDRO_DISP, t_m)


def draft_from_displacement(delta_t: float) -> float:
    """Средняя осадка (м) по водоизмещению."""
    return _interp(HYDRO_DISP, HYDRO_T, delta_t)


def kmt_from_displacement(delta_t: float) -> float:
    return _interp(HYDRO_DISP, HYDRO_KMT, delta_t)


def kb_from_displacement(delta_t: float) -> float:
    return _interp(HYDRO_DISP, HYDRO_KB, delta_t)


def gz0_at(delta_t: float, phi_deg: float) -> float:
    """Плечо ПСО из буклета при VCG=0 (от КН), интерполяция по Δ и углу."""
    col = np.asarray(GZ_ANGLES_DEG, float)
    i = np.searchsorted(col, phi_deg)
    if i <= 0:
        return 0.0
    if i >= len(col):
        i = len(col) - 1
        t = 1.0
    else:
        t = (phi_deg - col[i - 1]) / (col[i] - col[i - 1]) if col[i] != col[i - 1] else 0.0
    gz_low = np.interp(delta_t, GZ_DISPLACEMENTS, [row[i - 1] for row in GZ0_TABLE])
    gz_high = np.interp(delta_t, GZ_DISPLACEMENTS, [row[i] for row in GZ0_TABLE])
    return float(gz_low + t * (gz_high - gz_low))


def gz_curve(delta_t: float, vcg_m: float, phi_deg_list: Sequence[float]) -> tuple[list[float], list[float]]:
    """GZ(φ) = GZ₀ − VCG·sin φ (КН на ОП, как в буклете для таблиц при VCG=0)."""
    phis = []
    gzs = []
    for p in phi_deg_list:
        pr = math.radians(p)
        g = gz0_at(delta_t, p) - vcg_m * math.sin(pr)
        phis.append(p)
        gzs.append(g)
    return phis, gzs


def gm_metacentric(delta_t: float, kg_m: float, fsc_m: float = 0.0) -> float:
    """GM = KMT − KG − поправка на ПВСВ (потеря GM, м)."""
    return kmt_from_displacement(delta_t) - kg_m - fsc_m


def integrate_gz_m_rad(phi_deg: Sequence[float], gz_m: Sequence[float], a_deg: float, b_deg: float) -> float:
    """Площадь под GZ от a до b (м·рад); углы в градусах, абсцисса интеграла — радианы."""
    ph = np.asarray(phi_deg, float)
    gz = np.asarray(gz_m, float)
    mask = (ph >= a_deg - 1e-9) & (ph <= b_deg + 1e-9)
    if not np.any(mask):
        return 0.0
    idx = np.where(mask)[0]
    sl = slice(idx[0], idx[-1] + 1)
    phs = ph[sl]
    gzs = gz[sl]
    xr = np.radians(phs)
    return float(np.trapz(gzs, xr))


def build_fine_gz(
    delta_t: float,
    vcg_m: float,
    step_deg: float = 1.0,
) -> tuple[np.ndarray, np.ndarray]:
    """Плотная сетка 0…60° для интегралов и графика."""
    phis = np.arange(0.0, 60.0 + step_deg * 0.5, step_deg)
    gzs = []
    for p in phis:
        pr = math.radians(float(p))
        g = gz0_at(delta_t, float(p)) - vcg_m * math.sin(pr)
        gzs.append(max(g, -1.0))
    return phis, np.asarray(gzs)


@dataclass
class CriterionResult:
    code: str
    description: str
    required: str
    actual: str
    ok: bool


def imo749_intact(
    delta_t: float,
    vcg_m: float,
    kg_m: float,
    fsc_m: float,
    theta_flood_deg: float,
) -> tuple[list[CriterionResult], dict]:
    """
    Критерии неповреждённого судна (буклет, п. 5):
    1. A₀¹⁵ ≥ 0,070 м·рад
    2. A₃₀^θ ≥ 0,030 м·рад, θ = min(40°, θf)
    3. GZ₃₀ ≥ 0,20 м
    4. Угол макс. GZ ≥ 15°
    5. GM ≥ 0,15 м
    """
    gm = gm_metacentric(delta_t, kg_m, fsc_m)
    phis, gzs = build_fine_gz(delta_t, vcg_m, 0.5)
    phis_list = [float(x) for x in phis]
    gzs_list = [float(x) for x in gzs]

    a_0_15 = integrate_gz_m_rad(phis_list, gzs_list, 0.0, 15.0)
    theta_end = min(40.0, theta_flood_deg)
    a_30_end = integrate_gz_m_rad(phis_list, gzs_list, 30.0, theta_end)
    gz30 = float(np.interp(30.0, phis, gzs))
    imax = int(np.argmax(gzs))
    phi_max_gz = float(phis[imax])

    results = [
        CriterionResult(
            "1",
            "Площадь под кривой GZ до 15°",
            "≥ 0,070 м·рад",
            f"{a_0_15:.4f} м·рад",
            a_0_15 >= 0.070,
        ),
        CriterionResult(
            "2",
            f"Площадь GZ между 30° и min(40°, θзал) = {theta_end:.1f}°",
            "≥ 0,030 м·рад",
            f"{a_30_end:.4f} м·рад",
            a_30_end >= 0.030,
        ),
        CriterionResult(
            "3",
            "Плечо GZ при 30°",
            "≥ 0,20 м",
            f"{gz30:.3f} м",
            gz30 >= 0.20,
        ),
        CriterionResult(
            "4",
            "Угол при максимальном GZ",
            "≥ 15°",
            f"{phi_max_gz:.1f}°",
            phi_max_gz >= 15.0,
        ),
        CriterionResult(
            "5",
            "Начальная метацентрическая высота GM",
            "≥ 0,15 м",
            f"{gm:.3f} м",
            gm >= 0.15,
        ),
    ]
    meta = {
        "gm_m": gm,
        "a_0_15": a_0_15,
        "a_30_theta": a_30_end,
        "gz_30": gz30,
        "phi_max_gz": phi_max_gz,
        "phis_deg": phis_list,
        "gz_m": gzs_list,
    }
    return results, meta


def combine_masses(
    items: Sequence[tuple[float, float]],
) -> tuple[float, float]:
    """Список (масса_т, аппликата_KG_м) → Δ, KG."""
    total = sum(m for m, _ in items)
    if total <= 0:
        return 0.0, 0.0
    kg = sum(m * kg for m, kg in items) / total
    return total, kg


def coal_mass_from_draft(
    mean_draft_m: float,
    mass_without_coal_t: float,
) -> float:
    """
    Масса угля на борту (т) по средней осадке:
    M_уголь = Δ(T) − M_прочее (припасы, балласт, порожний корпус и т.д., без угля).
    """
    delta = displacement_from_draft(mean_draft_m)
    return max(delta - mass_without_coal_t, 0.0)


def coal_mass_table(
    mass_without_coal_t: float,
    t_min: float = 1.2,
    t_max: float = 4.4,
    step: float = 0.1,
) -> list[tuple[float, float, float]]:
    """Таблица: осадка → водоизмещение → масса угля."""
    rows = []
    t = t_min
    while t <= t_max + 1e-6:
        d = displacement_from_draft(t)
        coal = max(d - mass_without_coal_t, 0.0)
        rows.append((round(t, 2), d, coal))
        t += step
    return rows


def wind_heeling_levers(
    p_pa: float,
    a_m2: float,
    z_m: float,
    delta_t: float,
) -> tuple[float, float]:
    """LW1 и LW2 по буклету: LW1 = PAZ/(1000 g Δ), LW2 = 1,5 LW1 (м)."""
    lw1 = (p_pa * a_m2 * z_m) / (1000.0 * G * delta_t)
    return lw1, 1.5 * lw1


def imo_x1(bt: float) -> float:
    xs = [2.4, 2.5, 2.6, 2.7, 2.8, 2.9, 3.0, 3.2, 3.3, 3.4, 3.5]
    ys = [1.0, 0.98, 0.96, 0.95, 0.93, 0.91, 0.9, 0.86, 0.84, 0.82, 0.8]
    return float(np.interp(bt, xs, ys))


def imo_x2(cb: float) -> float:
    xs = [0.45, 0.5, 0.55, 0.6, 0.65, 0.7]
    ys = [0.75, 0.82, 0.89, 0.95, 0.97, 1.0]
    return float(np.interp(cb, xs, ys))


def imo_k_table(ratio: float) -> float:
    xs = [0.0, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0]
    ys = [1.0, 0.98, 0.95, 0.88, 0.79, 0.74, 0.72, 0.7]
    return float(np.interp(ratio, xs, ys))


def imo_s_from_tr(tr: float) -> float:
    xs = [6.0, 7.0, 8.0, 12.0, 14.0, 16.0, 18.0, 20.0]
    ys = [0.1, 0.098, 0.093, 0.065, 0.053, 0.044, 0.038, 0.035]
    return float(np.interp(tr, xs, ys))


def roll_angle_theta1_deg(
    *,
    b_m: float,
    d_m: float,
    l_m: float,
    cb: float,
    gm_m: float,
    ak_m2: float,
    og_m: float,
    k_ship: float = 0.7,
) -> float:
    """
    θ1 = 109 · k · X1 · X2 · (r s)^0,5 (градусы) — как в буклете.
    r = 0,73 + 0,6·OG/d; TR = 2·CB/√GM; s = s(TR).
    """
    bt = b_m / d_m
    x1 = imo_x1(bt)
    x2 = imo_x2(cb)
    ratio = 100.0 * ak_m2 / (l_m * b_m)
    ktab = imo_k_table(ratio)
    tr = 2.0 * cb / math.sqrt(max(gm_m, 1e-6))
    s = imo_s_from_tr(tr)
    r = 0.73 + 0.6 * (og_m / d_m)
    inside = max(r * s, 0.0)
    return 109.0 * k_ship * x1 * x2 * ktab * math.sqrt(inside)


def block_coefficient(delta_t: float) -> float:
    """Грубая оценка Cb = Δ/(ρ L B T) для погодного критерия."""
    t = draft_from_displacement(delta_t)
    rho = SHIP["rho_sea_t_m3"]
    l, b = SHIP["loa_m"], SHIP["beam_m"]
    return float(delta_t / (rho * l * b * max(t, 0.5)))
