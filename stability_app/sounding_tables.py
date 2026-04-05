"""Таблицы замер (sounding) → масса, т — по данным GHS/буклета (JSON)."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

_DATA = Path(__file__).resolve().parent / "data" / "sounding_fresh.json"


def load_fresh_sounding_tables() -> dict[str, list[tuple[float, float]]]:
    """
    Загрузка калибровок пресных танков.

    Формат sounding_fresh.json:
    {
      "FRESH-PTS.P": [[мм_замера, масса_т], ...],
      "FRESH-STB.S": [[...], ...]
    }
    Строки по возрастанию мм; можно задать только один ключ — тогда он используется для обоих бортов.
    """
    if not _DATA.is_file():
        return {}
    with open(_DATA, encoding="utf-8") as f:
        raw: dict = json.load(f)
    out: dict[str, list[tuple[float, float]]] = {}
    for k, v in raw.items():
        if not isinstance(v, list):
            continue
        rows: list[tuple[float, float]] = []
        for row in v:
            if isinstance(row, (list, tuple)) and len(row) >= 2:
                rows.append((float(row[0]), float(row[1])))
        rows.sort(key=lambda t: t[0])
        if rows:
            out[str(k)] = rows
    return out


def tons_from_sounding_mm(sounding_mm: float, points: list[tuple[float, float]]) -> float | None:
    """
    Линейная интерполяция массы (т) по замеру (мм).

    За пределами [min мм, max мм] — значение ограничивается (без экстраполяции).
    """
    if len(points) < 2:
        return None
    xs = np.asarray([p[0] for p in points], dtype=float)
    ys = np.asarray([p[1] for p in points], dtype=float)
    x = float(np.clip(sounding_mm, xs[0], xs[-1]))
    return float(np.interp(x, xs, ys))


def table_for_fresh_tank(side: str, tables: dict[str, list[tuple[float, float]]]) -> list[tuple[float, float]]:
    """side: 'P' | 'S' — лев/прав по буклету."""
    fr = tables.get("FRESH", [])
    if len(fr) >= 2:
        return fr
    k = "FRESH-PTS.P" if side == "P" else "FRESH-STB.S"
    return tables.get(k, [])
