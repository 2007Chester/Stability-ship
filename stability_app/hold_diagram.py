"""Схема профиля: корпус, ватерлиния, трюм, секции, слой угля."""

from __future__ import annotations

import plotly.graph_objects as go

from hold_layout import (
    DEPTH_M,
    HOLD_LCG_AP_AFT_M,
    HOLD_LCG_AP_FWD_M,
    LBP_M,
    LOA_M,
    NUM_HOLD_SECTIONS,
    section_edges_from_ap_m,
    section_length_m,
    waterline_draft_at_x_from_ap_m,
)


def build_hold_profile_figure(
    *,
    t_fwd_m: float,
    t_aft_m: float,
    coal_mass_t: float,
    rho_coal_t_m3: float,
    coal_fill_height_m: float,
    tons_per_section: float,
) -> go.Figure:
    """
    Вид сбоку: базовая линия — килевая линия, X от кормы (м), Y — высота от киля (м).
    """
    D = DEPTH_M
    lbp = LBP_M
    ha = float(HOLD_LCG_AP_AFT_M)
    hf = float(HOLD_LCG_AP_FWD_M)

    fig = go.Figure()

    # Корпус между перпендикулярами (упрощённо прямоугольник; совпадает с осями расчёта осадки)
    hull_x = [0.0, lbp, lbp, 0.0, 0.0]
    hull_y = [0.0, 0.0, D, D, 0.0]
    fig.add_trace(
        go.Scatter(
            x=hull_x,
            y=hull_y,
            mode="lines",
            line=dict(color="#2c3e50", width=2),
            fill="toself",
            fillcolor="rgba(189, 195, 199, 0.35)",
            name="Корпус (LBP)",
            hoverinfo="skip",
        )
    )

    # Зона трюма (полупрозрачная подложка)
    fig.add_trace(
        go.Scatter(
            x=[ha, hf, hf, ha, ha],
            y=[0.0, 0.0, D, D, 0.0],
            mode="lines",
            line=dict(color="#2980b9", width=1, dash="dash"),
            fill="toself",
            fillcolor="rgba(52, 152, 219, 0.12)",
            name="Грузовой трюм (границы по длине)",
            hoverinfo="skip",
        )
    )

    # Ватерлиния (линейный дифферент)
    wl_y0 = waterline_draft_at_x_from_ap_m(0.0, t_aft_m, t_fwd_m, lbp)
    wl_y1 = waterline_draft_at_x_from_ap_m(lbp, t_aft_m, t_fwd_m, lbp)
    fig.add_trace(
        go.Scatter(
            x=[0.0, lbp],
            y=[wl_y0, wl_y1],
            mode="lines",
            line=dict(color="#1abc9c", width=3),
            name="Ватерлиния",
        )
    )

    # 20 секций — вертикали
    edges = section_edges_from_ap_m()
    for i, xe in enumerate(edges):
        fig.add_shape(
            type="line",
            x0=xe,
            x1=xe,
            y0=0.0,
            y1=D,
            line=dict(color="rgba(127, 140, 141, 0.7)", width=1 if 0 < i < len(edges) - 1 else 2),
            layer="below",
        )

    # Слой угля (ровная засыпка по дну трюма)
    h_fill = max(0.0, min(float(coal_fill_height_m), D))
    if h_fill > 0 and hf > ha:
        fig.add_trace(
            go.Scatter(
                x=[ha, hf, hf, ha, ha],
                y=[0.0, 0.0, h_fill, h_fill, 0.0],
                mode="lines",
                line=dict(color="#6d4c41", width=1),
                fill="toself",
                fillcolor="rgba(121, 85, 72, 0.55)",
                name=f"Уголь ~{coal_mass_t:.0f} т",
                hoverinfo="skip",
            )
        )

    # Подписи секций 1…20 у верхней кромки трюма
    centers = [0.5 * (edges[i] + edges[i + 1]) for i in range(NUM_HOLD_SECTIONS)]
    for i, xc in enumerate(centers):
        fig.add_annotation(
            x=xc,
            y=D * 0.98,
            text=str(i + 1),
            showarrow=False,
            font=dict(size=9, color="#34495e"),
            yanchor="top",
        )

    t_mean = 0.5 * (float(t_fwd_m) + float(t_aft_m))
    trim_cm = (float(t_aft_m) - float(t_fwd_m)) * 100.0

    fig.update_layout(
        title=dict(
            text=(
                f"Профиль (сбоку) · осадка нос/корма: {t_fwd_m:.2f} / {t_aft_m:.2f} м · "
                f"T<sub>ср</sub> ≈ {t_mean:.2f} м · дифферент {trim_cm:+.0f} см"
            ),
            font=dict(size=14),
        ),
        xaxis=dict(
            title="Расстояние от кормы (м)",
            range=[-2.0, max(LOA_M, lbp) + 2.0],
            zeroline=False,
        ),
        yaxis=dict(
            title="Высота от киля (м)",
            range=[-0.2, D * 1.08],
            zeroline=False,
        ),
        height=480,
        margin=dict(l=60, r=40, t=70, b=50),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5),
        template="plotly_white",
        hovermode="closest",
    )

    fig.add_annotation(
        xref="paper",
        yref="paper",
        x=0,
        y=-0.12,
        showarrow=False,
        align="left",
        font=dict(size=11, color="#555"),
        text=(
            f"Трюм по длине: {ha:.0f}…{hf:.0f} м от кормы · {NUM_HOLD_SECTIONS} секций по ~{section_length_m():.2f} м · "
            f"при равномерном распределении {coal_mass_t:.0f} т: <b>~{tons_per_section:.1f} т/секцию</b>. "
            f"Ориентир высоты ровного слоя по дну: <b>{coal_fill_height_m:.2f} м</b> (ρ={rho_coal_t_m3:.2f} т/м³, площадь L×B)."
        ),
    )

    return fig
