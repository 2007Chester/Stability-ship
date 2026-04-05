"""Данные баржи «РЕЙД-8» (буклет 3035-0006, дифферент 0, ρ воды 1,025 т/м³)."""

from __future__ import annotations

import json
from pathlib import Path

_SHIP = {
    "name": "РЕЙД-8 (тип Kimtrans SPB 3210)",
    "loa_m": 97.536,
    "lbp_m": 96.78,
    "beam_m": 24.384,
    "depth_m": 6.096,
    "draft_summer_m": 4.439,
    "grt": 3695,
    "rho_sea_t_m3": 1.025,
    "lightship_mass_t": 1770.67,
    "lightship_lcg_m": 44.635,
    "lightship_vcg_m": 6.069,
    "doc_note": (
        "Гидростатика и ПСО при VCG=0 — из разд. 10–11 буклета (дифферент 0). "
        "GZ(φ) = GZ₀(Δ,φ) − VCG·sin φ. Критерии — Резолюция ИМО A.749 (как в буклете)."
    ),
}
_SHIP.setdefault("lbp_m", 96.78)

with open(Path(__file__).resolve().parent / "_embedded.json", "r", encoding="utf-8") as f:
    _emb = json.load(f)

HYDRO_T: list[float] = [r[0] for r in _emb["hydro"]]
HYDRO_DISP: list[float] = [r[1] for r in _emb["hydro"]]
HYDRO_KB: list[float] = [r[2] for r in _emb["hydro"]]
HYDRO_KMT: list[float] = [r[3] for r in _emb["hydro"]]

GZ_DISPLACEMENTS: list[float] = [row[0] for row in _emb["gz_rows"]]
GZ_ANGLES_DEG: list[int] = list(_emb["angles"])
# матрица [i_disp][i_angle] — значения GZ₀ из буклета (м), VCG от КН
GZ0_TABLE: list[list[float]] = [row[1:] for row in _emb["gz_rows"]]

__all__ = [
    "SHIP",
    "HYDRO_T",
    "HYDRO_DISP",
    "HYDRO_KB",
    "HYDRO_KMT",
    "GZ_DISPLACEMENTS",
    "GZ_ANGLES_DEG",
    "GZ0_TABLE",
]

SHIP = dict(_SHIP)
SHIP.setdefault("lbp_m", 96.78)
