"""
Критерии в духе рабочих Excel (РМРС / ИМО): погодный (энергии A и B), ускорение п. 3.12.3.
Формулы r, C, T, X1, X2, S — как в буклете и на листе «weather criteria».
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Callable

import numpy as np

from stability import gz0_at, trapz_compat

G0 = 9.80665


def rs_inertial_c(lbp_m: float, beam_m: float, draft_m: float) -> float:
    """C = 0,373 + 0,023·B/d − 0,043·L/100 (как в Excel)."""
    d = max(draft_m, 0.01)
    return 0.373 + 0.023 * (beam_m / d) - 0.043 * (lbp_m / 100.0)


def rs_k_theta_bd(b_over_d: float) -> float:
    """Таблица 3.12.3 РМРС: kθ(B/d), линейная интерполяция."""
    xs = [2.5, 3.0, 3.5, 4.0, 4.5, 5.0, 5.5, 6.0]
    ys = [1.0, 1.08, 1.11, 1.11, 1.2, 1.3, 1.45, 1.56]
    x = float(b_over_d)
    return float(np.interp(x, xs, ys, left=ys[0], right=ys[-1]))


def rs_roll_period_sec(c: float, beam_m: float, gm_m: float) -> float:
    """T = 2·C·B / √GM (с) — как в Excel, строка «T = »."""
    gm = max(gm_m, 1e-6)
    return 2.0 * c * beam_m / math.sqrt(gm)


def rs_s_from_roll_period(t_sec: float) -> float:
    """Таблица 3 (период качки T → S), как в буклете."""
    xs = [6.0, 7.0, 8.0, 12.0, 14.0, 16.0, 18.0, 20.0]
    ys = [0.1, 0.098, 0.093, 0.065, 0.053, 0.044, 0.038, 0.035]
    return float(np.interp(t_sec, xs, ys, left=ys[0], right=ys[-1]))


def rs_r_parameter(kg_m: float, draft_m: float) -> float:
    """r = 0,73 + 0,60·(KG − d)/d."""
    d = max(draft_m, 0.01)
    return 0.73 + 0.60 * (kg_m - d) / d


def imo_x1_wind(bt: float) -> float:
    xs = [2.4, 2.5, 2.6, 2.7, 2.8, 2.9, 3.0, 3.2, 3.3, 3.4, 3.5]
    ys = [1.0, 0.98, 0.96, 0.95, 0.93, 0.91, 0.9, 0.86, 0.84, 0.82, 0.8]
    return float(np.interp(bt, xs, ys, left=ys[0], right=ys[-1]))


def imo_x2_wind(cb: float) -> float:
    xs = [0.45, 0.5, 0.55, 0.6, 0.65, 0.7]
    ys = [0.75, 0.82, 0.89, 0.95, 0.97, 1.0]
    return float(np.interp(cb, xs, ys, left=ys[0], right=ys[-1]))


def imo_k_tab(ratio_100ak_lb: float) -> float:
    xs = [0.0, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0]
    ys = [1.0, 0.98, 0.95, 0.88, 0.79, 0.74, 0.72, 0.7]
    return float(np.interp(ratio_100ak_lb, xs, ys, left=ys[0], right=ys[-1]))


def theta1_roll_deg(
    *,
    beam_m: float,
    draft_m: float,
    lbp_m: float,
    cb: float,
    gm_m: float,
    ak_m2: float,
    kg_m: float,
    k_ship: float = 0.7,
) -> float:
    """θ1r = 109·k·X1·X2·k_tab·√(r·S) — угол качки (градусы)."""
    d = max(draft_m, 0.01)
    bt = beam_m / d
    x1 = imo_x1_wind(bt)
    x2 = imo_x2_wind(cb)
    c = rs_inertial_c(lbp_m, beam_m, d)
    t_roll = rs_roll_period_sec(c, beam_m, gm_m)
    s = rs_s_from_roll_period(t_roll)
    r = rs_r_parameter(kg_m, d)
    ratio = 100.0 * ak_m2 / (lbp_m * beam_m)
    ktab = imo_k_tab(ratio)
    inside = max(r * s, 0.0)
    return 109.0 * k_ship * x1 * x2 * ktab * math.sqrt(inside)


def lw_wind_m(p_pa: float, a_m2: float, z_m: float, delta_t: float) -> tuple[float, float]:
    lw1 = (p_pa * a_m2 * z_m) / (1000.0 * G0 * max(delta_t, 1e-6))
    return lw1, 1.5 * lw1


def gz_at(
    delta_t: float,
    kg0_m: float,
    phi_deg: float,
) -> float:
    """GZ с поправкой на аппликату G (KG0), м (φ ≥ 0, таблица буклета)."""
    pr = math.radians(phi_deg)
    return gz0_at(delta_t, phi_deg) - kg0_m * math.sin(pr)


def gz_signed(delta_t: float, kg0_m: float, phi_deg: float) -> float:
    """GZ(φ) для произвольного знака крена: для симметричного корпуса GZ(−φ) = −GZ(φ)."""
    p = float(phi_deg)
    if abs(p) < 1e-12:
        return 0.0
    return math.copysign(gz_at(delta_t, kg0_m, abs(p)), p)


def find_phi_equilibrium_lw1(
    delta_t: float,
    kg0_m: float,
    lw1: float,
    phi_max: float = 30.0,
) -> float:
    """Угол θ0, где GZ(φ) ≈ lw1 (ветер постоянный), °."""
    phis = np.linspace(0.0, phi_max, 600)
    gz = np.array([gz_at(delta_t, kg0_m, p) for p in phis])
    diff = gz - lw1
    idx = np.where(diff >= 0)[0]
    if len(idx) == 0:
        return float(phi_max)
    i0 = int(idx[0])
    if i0 == 0:
        return 0.0
    p0, p1 = float(phis[i0 - 1]), float(phis[i0])
    g0, g1 = float(gz[i0 - 1]), float(gz[i0])
    if g1 == g0:
        return p1
    t = (lw1 - g0) / (g1 - g0)
    return p0 + t * (p1 - p0)


def find_second_crossing_lw2(
    delta_t: float,
    kg0_m: float,
    lw2: float,
    phi_start_deg: float,
    phi_max: float = 90.0,
) -> float:
    """Первое φ > φ_start, где GZ ≤ lw2 (потолок для площади B), °."""
    phis = np.linspace(phi_start_deg, phi_max, 600)
    gz = np.array([gz_at(delta_t, kg0_m, p) for p in phis])
    diff = gz - lw2
    idx = np.where(diff <= 0)[0]
    if len(idx) == 0:
        return float(phi_max)
    return float(phis[int(idx[0])])


@dataclass
class WeatherEnergyResult:
    theta0_deg: float
    theta2_deg: float
    area_a_m_rad: float
    area_b_m_rad: float
    ratio_b_over_a: float


def weather_energy_areas(
    delta_t: float,
    kg0_m: float,
    lw1: float,
    lw2: float,
    theta1_roll_deg: float,
    theta_flood_deg: float,
    step_deg: float = 0.25,
) -> WeatherEnergyResult:
    """
    Энергетический баланс погодного критерия (ИМО / лист «weather criteria»):
      θ₀ — равновесие под постоянным ветром: GZ(θ₀) = lw1;
      амплитуда качки θ₁ᵣ — крен к наветренной стороне относительно θ₀;
      **A** = ∫_{θ₀−θ₁}^{θ₀} (lw2 − GZ) dφ  — работа порыва;
      **B** = ∫_{θ₀}^{θ₂} (GZ − lw2) dφ , θ₂ = min(θзал, второе пересечение GZ с lw2).
    """
    theta0 = find_phi_equilibrium_lw1(delta_t, kg0_m, lw1)
    theta_a = theta0 - theta1_roll_deg
    theta_cap = min(theta_flood_deg, 90.0)
    theta2 = find_second_crossing_lw2(delta_t, kg0_m, lw2, theta0 + step_deg, phi_max=theta_cap)

    phis_a = np.arange(theta_a, theta0 + 1e-9, step_deg) if theta0 >= theta_a else np.array([theta_a, theta0])
    if len(phis_a) < 2:
        phis_a = np.array([theta_a, theta0])
    integr_a = []
    rad_a = []
    for p in phis_a:
        g = gz_signed(delta_t, kg0_m, float(p))
        integr_a.append(max(lw2 - g, 0.0))
        rad_a.append(math.radians(float(p)))
    area_a = trapz_compat(integr_a, rad_a)

    phis_b = np.arange(theta0, theta2 + 1e-9, step_deg)
    if len(phis_b) < 2:
        phis_b = np.array([theta0, theta2])
    integr_b = []
    rad_b = []
    for p in phis_b:
        g = gz_at(delta_t, kg0_m, float(p))
        integr_b.append(max(g - lw2, 0.0))
        rad_b.append(math.radians(float(p)))
    area_b = trapz_compat(integr_b, rad_b)

    ratio = area_b / area_a if area_a > 1e-9 else float("inf")
    return WeatherEnergyResult(
        theta0_deg=theta0,
        theta2_deg=theta2,
        area_a_m_rad=area_a,
        area_b_m_rad=area_b,
        ratio_b_over_a=ratio,
    )


def rs_acceleration_a_calc(k_theta: float, c: float, theta_r_deg: float) -> float:
    """
    Расчётное ускорение (доли g) по соответствию с рабочим Excel «В грузу»:
    a_расч ≈ kθ · C · (θ_r в радианах), где θ_r — амплитуда качки (как θ1r), град.
    """
    tr = math.radians(theta_r_deg)
    return k_theta * c * tr


def rs_acceleration_k_star(a_calc: float) -> float:
    """К* = 0,3 / a_расч (п. 3.12.3)."""
    if a_calc <= 1e-12:
        return float("inf")
    return 0.3 / a_calc


def block_cb_from_nabla(delta_t: float, lbp_m: float, beam_m: float, draft_m: float, rho: float) -> float:
    """Cb = ∇ / (L·B·d), ∇ = Δ/ρ."""
    vol = delta_t / max(rho, 1e-6)
    denom = lbp_m * beam_m * max(draft_m, 0.01)
    return float(vol / denom)
