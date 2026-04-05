"""Таблица загрузки в оформлении, близком к рабочим листам Excel (Trim / Stability General)."""

from __future__ import annotations

import numpy as np
import pandas as pd

# Заголовки как в типичном Excel: запятая как разделитель «параметр — единица»
COL_NAME = "Наименование"
COL_MASS = "Масса, т"
COL_X = "Xг, м"
COL_KG = "KG, м"
COL_MX = "Момент X, т·м"
COL_MZ = "Момент KG, т·м"

EDIT_COLS = [COL_NAME, COL_MASS, COL_X, COL_KG]

LEGACY_RENAME = {
    "Масса_т": COL_MASS,
    "Xг_м": COL_X,
    "KG_м": COL_KG,
}


def normalize_load_columns(df: pd.DataFrame | None) -> pd.DataFrame:
    """Старые имена колонок (_т) → как в Excel (Масса, т)."""
    if df is None:
        return pd.DataFrame(columns=EDIT_COLS)
    out = df.copy()
    for old, new in LEGACY_RENAME.items():
        if old in out.columns and new not in out.columns:
            out = out.rename(columns={old: new})
    for c in EDIT_COLS:
        if c not in out.columns:
            out[c] = pd.NA
    return out[EDIT_COLS]


def x_g_to_from_ap(
    x: np.ndarray | pd.Series | list[float],
    lbp_m: float,
    *,
    from_midship: bool,
) -> np.ndarray:
    """
    Продольная координата Xг в метрах от шп. кормы вперёд.

    Если в Excel **от миделя** (часто «+ к носу»): x_корма = LBP/2 + x_мидель.
    Если уже **от кормы**: без изменения.
    """
    x = np.asarray(x, dtype=float)
    if not from_midship:
        return x
    return x + float(lbp_m) / 2.0


def trim_table_excel_with_total(
    df: pd.DataFrame,
    *,
    x_from_midship: bool = False,
    lbp_m: float | None = None,
) -> pd.DataFrame:
    """
    Строки загрузки + колонки моментов + строка ИТОГО (LCG = ΣMx/Σm, KG = ΣMz/Σm).

    Если x_from_midship=True, для момента X используется X от кормы: LBP/2 + X_в таблице.
    """
    df = normalize_load_columns(df)
    if COL_NAME not in df.columns or df.empty:
        return pd.DataFrame()
    w = df.dropna(subset=[COL_MASS]).copy()
    if w.empty:
        return pd.DataFrame()
    w[COL_MASS] = pd.to_numeric(w[COL_MASS], errors="coerce").fillna(0.0)
    w[COL_X] = pd.to_numeric(w[COL_X], errors="coerce").fillna(0.0)
    w[COL_KG] = pd.to_numeric(w[COL_KG], errors="coerce").fillna(0.0)
    lbp = float(lbp_m) if lbp_m is not None else 0.0
    x_ap = x_g_to_from_ap(w[COL_X].values, lbp, from_midship=x_from_midship)
    w[COL_MX] = w[COL_MASS].values * x_ap
    w[COL_MZ] = w[COL_MASS] * w[COL_KG]
    sm = float(w[COL_MASS].sum())
    total: dict[str, object] = {
        COL_NAME: "ИТОГО:",
        COL_MASS: sm,
        COL_MX: float(w[COL_MX].sum()),
        COL_MZ: float(w[COL_MZ].sum()),
    }
    if sm > 1e-12:
        total[COL_X] = float(w[COL_MX].sum() / sm)
        total[COL_KG] = float(w[COL_MZ].sum() / sm)
    else:
        total[COL_X] = float("nan")
        total[COL_KG] = float("nan")
    out = pd.concat([w, pd.DataFrame([total])], ignore_index=True)
    return out


def style_trim_excel(df: pd.DataFrame) -> pd.io.formats.style.Styler:
    """Синий заголовок, сетка, строка ИТОГО — в духе Excel."""
    if df.empty:
        return df.style
    disp = df.copy()
    fmt: dict[str, str] = {}
    if COL_MASS in disp.columns:
        fmt[COL_MASS] = "{:,.2f}"
    for c in (COL_X, COL_KG, COL_MX, COL_MZ):
        if c in disp.columns:
            fmt[c] = "{:,.3f}"
    sty = disp.style.format(fmt, na_rep="—")
    sty = sty.set_table_styles(
        [
            {
                "selector": "thead th",
                "props": (
                    "background-color: #4472C4; color: white; font-weight: bold; "
                    "border: 1px solid #306090; padding: 6px; text-align: center;"
                ),
            },
            {
                "selector": "tbody td",
                "props": (
                    "border: 1px solid #D0D0D0; padding: 4px 8px; text-align: right; "
                    "font-family: 'Segoe UI', 'Calibri', sans-serif;"
                ),
            },
        ]
    )

    def _total_row(_row: pd.Series) -> list[str]:
        if str(_row.get(COL_NAME, "")).strip() == "ИТОГО:":
            return ["background-color: #E2EFDA; font-weight: bold"] * len(_row)
        return [""] * len(_row)

    sty = sty.apply(_total_row, axis=1)
    sty = sty.set_properties(subset=[COL_NAME], **{"text-align": "left"})
    return sty
