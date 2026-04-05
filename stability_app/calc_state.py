"""Сохранение и загрузка параметров расчёта (JSON)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

STATE_VERSION = 2
APP_ID = "raid8-stability"

# Ключи session_state, которые участвуют в сохранении (сайдбар — явные key в app.py)
SIDEBAR_KEYS = (
    "sb_theta_flood",
    "sb_fsc",
    "sb_gg0",
    "sb_lcf_ap_m",
    "sb_x_from_midship",
)

STAB_KEYS = (
    "preset_v2",
    "last_preset_v2",
    "stab_m_stores",
    "stab_x_stores",
    "stab_kg_stores",
    "stab_m_fuel_svc",
    "stab_x_fuel_svc",
    "stab_kg_fuel_svc",
    "stab_t0",
    "stab_t1",
    "stab_t2",
    "stab_t3",
    "stab_t4",
    "stab_t5",
    "stab_t6",
    "stab_t7",
    "stab_t8",
    "stab_m_coal",
    "stab_x_coal",
    "stab_kg_coal",
    "stab_use_custom_tank_geometry",
    "stab_tank_lcg_0",
    "stab_tank_lcg_1",
    "stab_tank_lcg_2",
    "stab_tank_lcg_3",
    "stab_tank_lcg_4",
    "stab_tank_lcg_5",
    "stab_tank_lcg_6",
    "stab_tank_lcg_7",
    "stab_tank_lcg_8",
    "stab_tank_kg_0",
    "stab_tank_kg_1",
    "stab_tank_kg_2",
    "stab_tank_kg_3",
    "stab_tank_kg_4",
    "stab_tank_kg_5",
    "stab_tank_kg_6",
    "stab_tank_kg_7",
    "stab_tank_kg_8",
)

HOLDS_KEYS = (
    "holds_t_fwd",
    "holds_t_aft",
    "holds_fuel_tanks",
    "holds_fuel_svc",
    "holds_fresh_p",
    "holds_fresh_s",
    "holds_bw01_p",
    "holds_bw01_s",
    "holds_fore",
    "holds_bw02_p",
    "holds_bw02_s",
    "holds_m_other",
    "rho_holds",
)

ALL_KEYS: tuple[str, ...] = SIDEBAR_KEYS + STAB_KEYS + HOLDS_KEYS

BOOL_KEYS = ("sb_x_from_midship", "stab_use_custom_tank_geometry")


def _json_scalar(v: Any) -> Any:
    if v is None or isinstance(v, bool):
        return v
    if isinstance(v, str):
        return v
    if isinstance(v, (int, float)):
        return float(v)
    try:
        return float(v)
    except (TypeError, ValueError):
        return str(v)


def export_calc_state(session_state: Any) -> dict[str, Any]:
    """Собрать снимок для JSON (без чувствительных данных)."""
    state: dict[str, Any] = {}
    for k in ALL_KEYS:
        if k in session_state:
            state[k] = _json_scalar(session_state[k])
    return {
        "version": STATE_VERSION,
        "app": APP_ID,
        "saved_at": datetime.now(timezone.utc).isoformat(),
        "state": state,
    }


def apply_calc_state(payload: dict[str, Any], session_state: Any) -> None:
    """Записать значения в session_state; вызывать до st.rerun()."""
    if payload.get("app") != APP_ID:
        raise ValueError("Файл не от этого приложения (поле app).")
    ver = int(payload.get("version", 0))
    if ver > STATE_VERSION:
        raise ValueError("Файл новее версии приложения — обновите приложение.")
    raw = payload.get("state")
    if not isinstance(raw, dict):
        raise ValueError("В файле нет объекта state.")
    for k, v in raw.items():
        if k not in ALL_KEYS:
            continue
        if k in BOOL_KEYS:
            session_state[k] = bool(v)
            continue
        if k in ("preset_v2", "last_preset_v2"):
            session_state[k] = str(v) if v is not None else ""
            continue
        if v is None:
            session_state[k] = None
        elif isinstance(v, bool):
            session_state[k] = v
        elif isinstance(v, (int, float)):
            session_state[k] = float(v)
        elif isinstance(v, str):
            try:
                session_state[k] = float(v)
            except ValueError:
                session_state[k] = v
        else:
            session_state[k] = _json_scalar(v)
