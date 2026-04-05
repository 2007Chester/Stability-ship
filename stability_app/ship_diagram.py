"""План судна: контур и положение масс по длине (LCG от кормы)."""

from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go

from excel_ui import COL_MASS, COL_NAME, COL_X, x_g_to_from_ap


def _color_for_name(name: str) -> str:
    n = name.lower()
    if "порожн" in n or "light" in n:
        return "#78909C"
    if "снабж" in n or "store" in n:
        return "#43A047"
    if "уголь" in n or "coal" in n:
        return "#6D4C41"
    if "расход" in n or "fuel_svc" in n or "топливо расход" in n:
        return "#FB8C00"
    if "fuel" in n or "топлив" in n:
        return "#E65100"
    if "fresh" in n or "пресн" in n:
        return "#039BE5"
    if "bw" in n or "fore" in n or "пик" in n or "балласт" in n:
        return "#1565C0"
    return "#5C6BC0"


def load_plan_figure(
    df: pd.DataFrame,
    lbp_m: float,
    loa_m: float,
    beam_m: float,
    *,
    from_midship: bool,
    title: str = "План: положение масс (ось X — от шп. кормы вперёд, м)",
) -> go.Figure:
    """
    Вид сверху: прямоугольник корпуса, линия миделя, точки масс по LCG от кормы.
    Координаты таблицы (COL_X) переводятся в LCG от кормы для отображения.
    """
    loa = float(loa_m)
    b = float(beam_m)
    lbp = float(lbp_m)

    fig = go.Figure()

    # Корпус (прямоугольник по LOA, симметрично к диаметральной плоскости)
    hx = [0.0, loa, loa, 0.0, 0.0]
    hy = [-b / 2, -b / 2, b / 2, b / 2, -b / 2]
    fig.add_trace(
        go.Scatter(
            x=hx,
            y=hy,
            fill="toself",
            fillcolor="rgba(30, 136, 229, 0.12)",
            line=dict(color="#1976D2", width=2),
            name="Корпус (план)",
            hoverinfo="skip",
            showlegend=True,
        )
    )

    mid = lbp / 2.0
    fig.add_trace(
        go.Scatter(
            x=[mid, mid],
            y=[-b / 2, b / 2],
            mode="lines",
            line=dict(color="#C62828", width=2, dash="dash"),
            name="Мидель (LBP/2)",
            hoverinfo="skip",
        )
    )

    if df is None or df.empty or COL_X not in df.columns:
        fig.update_layout(title=title, template="plotly_white", height=420)
        return fig

    names = df[COL_NAME].astype(str).tolist()
    masses = pd.to_numeric(df[COL_MASS], errors="coerce").fillna(0.0).values
    x_tab = pd.to_numeric(df[COL_X], errors="coerce").fillna(0.0).values
    x_ap = np.asarray(
        x_g_to_from_ap(x_tab, lbp, from_midship=from_midship),
        dtype=float,
    )

    # Вертикальное смещение подписей, чтобы не накладывались
    n = len(names)
    jitter = np.linspace(-0.35, 0.35, n) * min(b, 8.0)

    sizes = np.sqrt(np.maximum(masses, 0.0))
    smax = float(np.nanmax(sizes)) if sizes.size else 1.0
    smax = max(smax, 1e-6)
    marker_size = 12.0 + 28.0 * (sizes / smax)

    for i in range(n):
        if masses[i] <= 0:
            continue
        nm = names[i]
        fig.add_trace(
            go.Scatter(
                x=[x_ap[i]],
                y=[jitter[i]],
                mode="markers+text",
                marker=dict(
                    size=min(float(marker_size[i]), 36.0),
                    color=_color_for_name(nm),
                    line=dict(width=1, color="#333"),
                ),
                text=[f"{nm}<br>{masses[i]:,.1f} т".replace(",", " ")],
                textposition="top center",
                textfont=dict(size=11),
                name=nm[:40] + ("…" if len(nm) > 40 else ""),
                hovertemplate=(
                    nm
                    + "<br>LCG от кормы: %{x:.3f} м<br>масса: "
                    + f"{masses[i]:.2f}".replace(",", " ")
                    + " т<extra></extra>"
                ),
                showlegend=False,
            )
        )

    # Без фиксации осей колесо мыши и рамка Zoom в Plotly перехватывают жесты вместо клика по палубе.
    fig.update_xaxes(
        title="Расстояние от шп. кормы вперёд, м (нос справа)",
        range=[-loa * 0.02, loa * 1.02],
        gridcolor="#eeeeee",
        zeroline=False,
        fixedrange=True,
    )
    fig.update_yaxes(
        title="Поперечник (схема), м",
        range=[-b / 2 - 2.5, b / 2 + 2.5],
        scaleanchor="x",
        scaleratio=1,
        gridcolor="#eeeeee",
        zeroline=False,
        fixedrange=True,
    )

    fig.add_annotation(
        x=0,
        y=-b / 2 - 1.2,
        text="Корма",
        showarrow=False,
        font=dict(size=12, color="#37474F"),
    )
    fig.add_annotation(
        x=loa,
        y=-b / 2 - 1.2,
        text="Нос",
        showarrow=False,
        font=dict(size=12, color="#37474F"),
        xanchor="right",
    )

    fig.update_layout(
        title=dict(text=title, font=dict(size=15)),
        template="plotly_white",
        height=440,
        margin=dict(l=52, r=24, t=48, b=40),
        hovermode="closest",
        dragmode=False,
    )
    return fig
