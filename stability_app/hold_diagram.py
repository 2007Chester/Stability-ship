"""Схема профиля в духе GA: корпус, двойное дно, палуба, комингсы, груз, ВЛ."""

from __future__ import annotations

from typing import Any

import plotly.graph_objects as go

from hold_layout import (
    COAMING_HEIGHT_ABOVE_DECK_M,
    DEPTH_M,
    HOLD_LCG_AP_AFT_M,
    HOLD_LCG_AP_FWD_M,
    INNER_BOTTOM_ABOVE_KEEL_M,
    LBP_M,
    LOA_M,
    NUM_HOLD_SECTIONS,
    coal_uniform_stowage_m,
    coaming_top_above_keel_m,
    hold_stowage_height_limit_m,
    main_deck_above_keel_m,
    section_edges_from_ap_m,
    section_length_m,
    waterline_draft_at_x_from_ap_m,
)


def _hull_outline_ga_style(lbp: float, d: float) -> tuple[list[float], list[float]]:
    """Профиль между перпендикулярами (как на типовом GA)."""
    return [0.0, lbp, lbp, 0.0, 0.0], [0.0, 0.0, d, d, 0.0]


def build_hold_profile_figure(
    *,
    t_fwd_m: float,
    t_aft_m: float,
    coal_mass_t: float,
    rho_coal_t_m3: float,
) -> go.Figure:
    D = float(DEPTH_M)
    lbp = float(LBP_M)
    loa = float(LOA_M)
    ha = float(HOLD_LCG_AP_AFT_M)
    hf = float(HOLD_LCG_AP_FWD_M)
    y_tt = float(INNER_BOTTOM_ABOVE_KEEL_M)
    y_deck = main_deck_above_keel_m()
    y_coom = float(coaming_top_above_keel_m())
    h_coom = float(COAMING_HEIGHT_ABOVE_DECK_M)

    stow: dict[str, Any] = coal_uniform_stowage_m(coal_mass_t, rho_coal_t_m3)
    h_cargo = float(stow["h_from_inner_bottom_m"])
    depth_deck_to_cargo = float(stow["depth_from_main_deck_to_cargo_m"])
    hold_moulded = float(stow["hold_depth_moulded_m"])
    clearance = float(stow["clearance_cooming_m"])
    capped = bool(stow["capped_by_cooming"])
    tons_per_section = float(stow["tons_per_section"])
    y_cargo_top = y_tt + h_cargo

    fig = go.Figure()

    hx, hy = _hull_outline_ga_style(lbp, D)
    fig.add_trace(
        go.Scatter(
            x=hx,
            y=hy,
            mode="lines",
            line=dict(color="#1a252f", width=2.5),
            fill="toself",
            fillcolor="rgba(189, 195, 199, 0.45)",
            name="Корпус (профиль)",
            hoverinfo="skip",
        )
    )

    # Двойное дно / tank top нижняя зона
    fig.add_trace(
        go.Scatter(
            x=[0.0, lbp, lbp, 0.0, 0.0],
            y=[0.0, 0.0, y_tt, y_tt, 0.0],
            mode="lines",
            line=dict(color="#5d6d7e", width=1),
            fill="toself",
            fillcolor="rgba(93, 109, 126, 0.45)",
            name="Двойное дно (ориентир)",
            hoverinfo="skip",
        )
    )

    # Грузовой трюм: сверху ограничен главной палубой, снизу — внутренним дном
    fig.add_trace(
        go.Scatter(
            x=[ha, hf, hf, ha, ha],
            y=[y_tt, y_tt, y_deck, y_deck, y_tt],
            mode="lines",
            line=dict(color="#2874a6", width=1.5, dash="dot"),
            fill="toself",
            fillcolor="rgba(133, 193, 233, 0.2)",
            name="Грузовой трюм (от гл. палубы вниз)",
            hoverinfo="skip",
        )
    )

    # Комингсы люка (над главной палубой — продолжение люка вверх)
    fig.add_trace(
        go.Scatter(
            x=[ha, ha, hf, hf, ha],
            y=[y_deck, y_coom, y_coom, y_deck, y_deck],
            mode="lines",
            line=dict(color="#1f618d", width=2),
            fill="toself",
            fillcolor="rgba(31, 97, 141, 0.25)",
            name=f"Комингсы (~{h_coom:.2f} м над палубой)",
            hoverinfo="skip",
        )
    )

    # Главная палуба — акцент линией по длине
    fig.add_trace(
        go.Scatter(
            x=[0.0, lbp],
            y=[y_deck, y_deck],
            mode="lines",
            line=dict(color="#2c3e50", width=2, dash="solid"),
            name="Главная палуба (молдинг D)",
            hoverinfo="skip",
        )
    )

    # Ватерлиния
    wl_y0 = waterline_draft_at_x_from_ap_m(0.0, t_aft_m, t_fwd_m, lbp)
    wl_y1 = waterline_draft_at_x_from_ap_m(lbp, t_aft_m, t_fwd_m, lbp)
    fig.add_trace(
        go.Scatter(
            x=[0.0, lbp],
            y=[wl_y0, wl_y1],
            mode="lines",
            line=dict(color="#16a085", width=3),
            name="Ватерлиния",
        )
    )

    # Секции
    edges = section_edges_from_ap_m()
    for i, xe in enumerate(edges):
        fig.add_shape(
            type="line",
            x0=xe,
            x1=xe,
            y0=y_tt,
            y1=y_coom,
            line=dict(color="rgba(127, 140, 141, 0.65)", width=1 if 0 < i < len(edges) - 1 else 2),
            layer="below",
        )

    # Уголь от внутреннего дна
    if h_cargo > 0 and hf > ha:
        fig.add_trace(
            go.Scatter(
                x=[ha, hf, hf, ha, ha],
                y=[y_tt, y_tt, y_cargo_top, y_cargo_top, y_tt],
                mode="lines",
                line=dict(color="#5d4037", width=1),
                fill="toself",
                fillcolor="rgba(109, 76, 65, 0.65)",
                name=f"Уголь ~{coal_mass_t:.0f} т",
                hoverinfo="skip",
            )
        )

    # Линия поверхности груза + подпись зазора до комингсов
    if h_cargo > 0 and hf > ha:
        fig.add_trace(
            go.Scatter(
                x=[ha, hf],
                y=[y_cargo_top, y_cargo_top],
                mode="lines",
                line=dict(color="#3e2723", width=2, dash="dash"),
                name="Поверхность груза",
                hoverinfo="skip",
            )
        )
        if clearance > 0.02:
            fig.add_annotation(
                x=0.5 * (ha + hf),
                y=0.5 * (y_cargo_top + y_coom),
                text=f"Зазор до верха<br>комингсов<br><b>{clearance:.2f} м</b>",
                showarrow=False,
                font=dict(size=11, color="#1b2631"),
                bgcolor="rgba(255,255,255,0.85)",
                bordercolor="#abb2b9",
                borderwidth=1,
            )
        elif capped:
            fig.add_annotation(
                x=0.5 * (ha + hf),
                y=0.5 * (y_tt + y_coom),
                text="По высоте упирается<br>в комингсы",
                showarrow=False,
                font=dict(size=11, color="#c0392b"),
                bgcolor="rgba(255,235,230,0.95)",
                bordercolor="#e74c3c",
                borderwidth=1,
            )

    centers = [0.5 * (edges[i] + edges[i + 1]) for i in range(NUM_HOLD_SECTIONS)]
    for i, xc in enumerate(centers):
        fig.add_annotation(
            x=xc,
            y=y_coom * 1.01,
            text=str(i + 1),
            showarrow=False,
            font=dict(size=9, color="#2c3e50"),
            yanchor="bottom",
        )

    fig.add_annotation(
        x=lbp * 0.02,
        y=y_tt * 0.5,
        text="Внутр. дно трюма",
        showarrow=False,
        font=dict(size=10, color="#34495e"),
        xanchor="left",
    )
    fig.add_annotation(
        x=lbp * 0.02,
        y=y_deck + 0.05,
        text="Главная палуба — верх трюма",
        showarrow=False,
        font=dict(size=10, color="#34495e"),
        xanchor="left",
    )
    fig.add_annotation(
        x=hf + 0.8,
        y=y_coom,
        text="Верх комингсов",
        showarrow=True,
        arrowhead=2,
        ax=40,
        ay=-20,
        font=dict(size=10, color="#1f618d"),
    )

    t_mean = 0.5 * (float(t_fwd_m) + float(t_aft_m))
    trim_cm = (float(t_aft_m) - float(t_fwd_m)) * 100.0

    y_max = max(y_coom * 1.12, wl_y0, wl_y1, D * 1.05)

    fig.update_layout(
        title=dict(
            text=(
                f"Профиль (GA, упрощ.) · нос/корма: {t_fwd_m:.2f} / {t_aft_m:.2f} м · "
                f"T<sub>ср</sub> ≈ {t_mean:.2f} м · дифф. {trim_cm:+.0f} см · "
                f"насыпь от вн. дна: <b>{h_cargo:.2f} м</b>"
            ),
            font=dict(size=13),
        ),
        xaxis=dict(
            title="От шп. кормы (м)",
            range=[-1.5, max(loa, lbp) + 1.5],
            zeroline=False,
            constrain="domain",
        ),
        yaxis=dict(
            title="Высота от киля (м)",
            range=[-0.25, y_max],
            zeroline=False,
            # 1 м по длине судна = 1 м по высоте (как на чертеже с масштабом по осям)
            scaleanchor="x",
            scaleratio=1,
            constrain="domain",
        ),
        # Высота области графика: при L/D ≈ 16 корпус визуально «низкий» — это верные пропорции
        height=640,
        margin=dict(l=58, r=36, t=72, b=88),
        legend=dict(orientation="h", yanchor="bottom", y=1.03, xanchor="center", x=0.5, font=dict(size=10)),
        template="plotly_white",
        hovermode="closest",
    )

    sub = (
        "<b>Масштаб чертежа:</b> оси X и Y в одинаковых метрах (1:1), как на типовом GA. "
        f"Трюм — <b>ниже главной палубы</b>, глубина трюма (палуба → вн. дно): <b>{hold_moulded:.2f} м</b>. "
        f"От палубы вниз до поверхности груза: <b>{depth_deck_to_cargo:.2f} м</b>. "
        f"Вн. дно над килем: <b>{y_tt:.2f} м</b> · палуба (D): <b>{y_deck:.3f} м</b> · верх комингсов: <b>{y_coom:.2f} м</b> "
        f"(+{h_coom:.2f} м к палубе). Секции: ~{section_length_m():.2f} м. "
        f"Насыпь от <b>внутреннего дна</b>: <b>{h_cargo:.2f} м</b>"
    )
    if clearance > 0.01:
        sub += f" · <b>зазор до комингсов</b> (от поверхности груза): <b>{clearance:.2f} м</b>."
    else:
        sub += " · зазор до комингсов: ~0 (под завал)."
    sub += f" Равномерно: <b>~{tons_per_section:.1f} т/секцию</b>."
    if capped:
        sub += (
            f" <b>Внимание:</b> при ρ={rho_coal_t_m3:.2f} т/м³ нужна высота <b>{float(stow['h_if_unlimited_m']):.2f} м</b> "
            f"от вн. дна — больше, чем до верха комингсов (<b>{hold_stowage_height_limit_m():.2f} м</b>)."
        )

    fig.add_annotation(
        xref="paper",
        yref="paper",
        x=0,
        y=-0.18,
        showarrow=False,
        align="left",
        font=dict(size=10, color="#444"),
        text=sub,
    )

    return fig
