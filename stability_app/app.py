"""
РЕЙД-8: остойчивость (ИМО A.749 + диаграмма GZ) и груз в трюмах по осадкам.

Запуск: python3 -m streamlit run app.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from cargo_excel_data import ROWS_CARGO_IN_GRUZ
from excel_ui import (
    COL_KG,
    COL_MASS,
    COL_NAME,
    COL_X,
    normalize_load_columns,
    style_trim_excel,
    trim_table_excel_with_total,
    x_g_to_from_ap,
)
from ship_data import SHIP
from stability import (
    cargo_mass_from_drafts,
    draft_from_displacement,
    drafts_fwd_aft_from_lcg,
    gm_metacentric,
    imo749_intact,
    kmt_from_displacement,
)

LBP_M = float(SHIP.get("lbp_m", 96.78))

# Ориентир макс. массы при 100% (буклет, разд. 6) — только для подсказок «?»
M_MAX_BW01 = 221.76
M_MAX_BW02 = 212.31
M_MAX_FORE = 101.62
M_MAX_FW_SIDE = 110.29

st.set_page_config(
    page_title="Остойчивость — РЕЙД-8",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
<style>
    div[data-testid="stMetricValue"] { font-size: 1.35rem; font-weight: 600; }
    .block-container { padding-top: 1.2rem; }
</style>
""",
    unsafe_allow_html=True,
)

st.markdown("# РЕЙД-8")
st.caption("Остойчивость по буклету · оценка насыпного груза в трюмах по осадкам")

# ——— боковая панель ———
with st.sidebar:
    st.markdown(f"### {SHIP['name']}")
    st.caption(
        f"L ≈ {SHIP['loa_m']} м · B = {SHIP['beam_m']} м · D = {SHIP['depth_m']} м · "
        f"ρ = {SHIP['rho_sea_t_m3']} т/м³"
    )
    st.divider()
    theta_flood = st.slider("Угол заливания θзал, °", 5.0, 90.0, 55.0, 1.0)
    fsc = st.number_input("ПВСВ (потеря GM), м", 0.0, 5.0, 0.0, 0.01)
    gg0 = st.number_input("GG₀ (лед и т.п.), м", 0.0, 3.0, 0.0, 0.001)
    lcf_ap_m = st.number_input("LCF от кормы, м", 0.0, float(LBP_M), float(LBP_M) / 2.0, 0.1)
    x_from_midship = st.toggle(
        "Xг в таблице от миделя (+ к носу)",
        value=True,
        help="Как в Trim Excel: LCG считается через LBP/2 + X.",
    )

# ——— две страницы ———
tab_stab, tab_holds = st.tabs(["Остойчивость", "Груз в трюмах по осадкам"])

with tab_stab:
    st.markdown("## Расчёт остойчивости")
    st.caption(
        "Заполните таблицу загрузки. Сумма масс → водоизмещение и осадка; ниже — **GM**, критерии **ИМО A.749** и диаграмма **GZ**."
    )

    preset = st.selectbox(
        "Шаблон",
        ["В грузу (из Excel)", "Пустая строка", "Без груза (балласт)"],
        index=0,
        key="preset_v2",
    )
    defaults = {
        "В грузу (из Excel)": [dict(r) for r in ROWS_CARGO_IN_GRUZ],
        "Пустая строка": [{COL_NAME: "Груз / балласт", COL_MASS: 1000.0, COL_X: 0.0, COL_KG: 4.5}],
        "Без груза (балласт)": [
            {COL_NAME: "Судно порожнее", COL_MASS: 2210.0, COL_X: 4.133, COL_KG: 4.58},
            {COL_NAME: "Снабжение", COL_MASS: 9.0, COL_X: -46.0, COL_KG: 7.2},
            {COL_NAME: "Балласт Л/Б", COL_MASS: 51.0, COL_X: -37.8, COL_KG: 1.15},
            {COL_NAME: "Балласт ПР/Б", COL_MASS: 50.0, COL_X: -37.8, COL_KG: 1.15},
        ],
    }
    if st.session_state.get("last_preset_v2") != preset or "load_df_v2" not in st.session_state:
        st.session_state.load_df_v2 = pd.DataFrame(defaults[preset])
        st.session_state.last_preset_v2 = preset
    st.session_state.load_df_v2 = normalize_load_columns(st.session_state.load_df_v2)

    edited = st.data_editor(
        st.session_state.load_df_v2,
        num_rows="dynamic",
        use_container_width=True,
        key="editor_v2",
        column_config={
            COL_NAME: st.column_config.TextColumn(COL_NAME, width="large", required=True),
            COL_MASS: st.column_config.NumberColumn(COL_MASS, format="%.2f", min_value=0.0),
            COL_X: st.column_config.NumberColumn(COL_X, format="%.3f"),
            COL_KG: st.column_config.NumberColumn(COL_KG, format="%.3f"),
        },
        height=280,
    )
    edited = normalize_load_columns(edited)
    st.session_state.load_df_v2 = edited

    tbl_excel = trim_table_excel_with_total(
        edited, x_from_midship=x_from_midship, lbp_m=LBP_M
    )
    if not tbl_excel.empty:
        with st.container(border=True):
            st.markdown("##### Итог по таблице (моменты, LCG, KG)")
            st.dataframe(style_trim_excel(tbl_excel), use_container_width=True, hide_index=True)

    df = edited.dropna(subset=[COL_MASS])
    masses = df[COL_MASS].astype(float).values
    xgs = df[COL_X].fillna(0).astype(float).values
    kgs = df[COL_KG].astype(float).values
    delta_t = float(np.sum(masses))
    if delta_t <= 0:
        st.error("Сумма масс должна быть больше нуля.")
        st.stop()
    kg_total = float(np.sum(masses * kgs) / delta_t)
    x_ap = x_g_to_from_ap(xgs, LBP_M, from_midship=x_from_midship)
    lcg_m = float(np.sum(masses * x_ap) / delta_t)
    kg0 = kg_total + gg0

    coal_mask = df[COL_NAME].astype(str).str.contains("Уголь", case=False, na=False)
    m_wo_coal = float(df.loc[~coal_mask, COL_MASS].fillna(0).sum())
    st.session_state["m_wo_coal_v2"] = m_wo_coal

    t_mean = draft_from_displacement(delta_t)
    gm = gm_metacentric(delta_t, kg0, fsc)
    kmt = kmt_from_displacement(delta_t)
    crit, meta = imo749_intact(delta_t, kg0, kg0, fsc, theta_flood)
    ok_all = all(c.ok for c in crit)

    long_trim = drafts_fwd_aft_from_lcg(
        delta_t,
        t_mean,
        lcg_m,
        lbp_m=LBP_M,
        beam_m=SHIP["beam_m"],
        lcf_from_ap_m=lcf_ap_m,
    )

    # Карточки результатов
    with st.container(border=True):
        st.markdown("##### Состояние по загрузке")
        r1, r2, r3, r4 = st.columns(4)
        r1.metric("Водоизмещение Δ", f"{delta_t:,.0f} т".replace(",", " "))
        r2.metric("Средняя осадка T", f"{t_mean:.3f} м")
        r3.metric("KG → KG₀", f"{kg_total:.2f} → {kg0:.2f} м")
        r4.metric("GM", f"{gm:.3f} м")
        st.caption(f"KMT ≈ {kmt:.3f} м · Осадка нос / корма: **{long_trim.t_fwd_m:.3f}** / **{long_trim.t_aft_m:.3f}** м · дифферент **{long_trim.trim_cm:+.0f}** см")

    with st.container(border=True):
        st.markdown("##### Критерии ИМО A.749 (неповреждённое судно)")
        crit_rows = [
            {
                "№": c.code,
                "Условие": c.description,
                "Норма": c.required,
                "Фактически": c.actual,
                "": "✓" if c.ok else "✗",
            }
            for c in crit
        ]
        st.dataframe(
            pd.DataFrame(crit_rows),
            use_container_width=True,
            hide_index=True,
            column_config={"": st.column_config.TextColumn(" ", width="small")},
        )
        if ok_all:
            st.success("Все критерии выполняются.")
        else:
            st.warning("Есть невыполненные критерии — скорректируйте загрузку или KG.")

    # Диаграмма GZ — внизу страницы
    st.markdown("---")
    st.markdown("##### Диаграмма статической остойчивости GZ(φ)")
    phis = meta["phis_deg"]
    gzs = meta["gz_m"]
    gzs_arr = np.asarray(gzs, dtype=float)
    phis_tan = np.linspace(0.0, 60.0, 181)
    gz_tan = gm * np.radians(phis_tan)
    gz_max = float(np.nanmax(gzs_arr))
    i_max = int(np.nanargmax(gzs_arr))
    phi_max_gz = float(np.asarray(phis, dtype=float)[i_max])

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=phis,
            y=gzs,
            mode="lines",
            name="GZ(φ)",
            line=dict(width=2.5, color="#0d47a1"),
            fill="tozeroy",
            fillcolor="rgba(13,71,161,0.12)",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=phis_tan,
            y=gz_tan,
            mode="lines",
            name=f"GM·φ (рад) · GM={gm:.2f} м",
            line=dict(width=2, color="#c62828"),
            hovertemplate="φ=%{x:.1f}° · %{y:.3f} м<extra></extra>",
        )
    )
    fig.add_hline(
        y=gz_max,
        line=dict(color="#2e7d32", width=2),
        annotation_text=f"GZ max {gz_max:.2f} м",
        annotation_position="right",
    )
    fig.add_vline(
        x=phi_max_gz,
        line=dict(color="#2e7d32", width=1, dash="dot"),
        annotation_text=f"φ max {phi_max_gz:.0f}°",
        annotation_position="top",
    )
    fig.add_hline(y=0, line_color="#9e9e9e", line_dash="dot")
    for xv, lab in [(15, "15°"), (30, "30°"), (57.3, "1 рад")]:
        fig.add_vline(
            x=xv,
            line_dash="dot",
            line_color="#bdbdbd",
            annotation_text=lab,
            annotation_position="top",
        )
    y_pad = max(0.15, float(np.nanmax(gzs_arr) - np.nanmin(gzs_arr)) * 0.08 + 0.05)
    y_min = float(np.nanmin([np.nanmin(gzs_arr), 0.0])) - y_pad
    y_max = max(float(np.nanmax(gzs_arr)), float(np.max(gz_tan))) + y_pad
    fig.update_layout(
        title=dict(
            text=f"GZ(φ) · KG₀ = {kg0:.3f} м",
            font=dict(size=16),
        ),
        xaxis_title="Угол крена φ, °",
        yaxis_title="GZ, м",
        height=480,
        template="plotly_white",
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=1, xanchor="right"),
        margin=dict(t=56, b=48),
        xaxis=dict(range=[0, 60], dtick=10, gridcolor="#eeeeee"),
        yaxis=dict(range=[y_min, y_max], gridcolor="#eeeeee"),
    )
    st.plotly_chart(fig, use_container_width=True)
    st.caption(
        "Синяя зона — плечо остойчивости; красная — начальная касательная GM·φ (φ в радианах); зелёные линии — максимум GZ и угол при нём."
    )

with tab_holds:
    st.markdown("## Груз в трюмах по осадкам")
    st.caption(
        "Введите **осадки**, массы **топлива**, **пресной воды**, **балласта** (все значения — **тонны**) и **прочее** без насыпного груза в трюмах — "
        "оценка **массы погруженного груза в трюмах**."
    )

    col_d, col_f = st.columns(2)
    with col_d:
        with st.container(border=True):
            st.markdown("##### Осадки (по перпендикулярам)")
            t_fwd = st.number_input(
                "Осадка носом, м",
                min_value=0.5,
                max_value=float(SHIP["depth_m"]) + 0.5,
                value=3.50,
                step=0.01,
                format="%.2f",
                key="holds_t_fwd",
            )
            t_aft = st.number_input(
                "Осадка кормой, м",
                min_value=0.5,
                max_value=float(SHIP["depth_m"]) + 0.5,
                value=3.50,
                step=0.01,
                format="%.2f",
                key="holds_t_aft",
            )
    with col_f:
        with st.container(border=True):
            st.markdown("##### Топливо, т")
            m_fuel_tanks = st.number_input(
                "Топливо в танках, т",
                min_value=0.0,
                value=6.0,
                step=0.5,
                key="holds_fuel_tanks",
            )
            m_fuel_svc = st.number_input(
                "Топливо в расходных цистернах, т",
                min_value=0.0,
                value=0.0,
                step=0.5,
                key="holds_fuel_svc",
            )
            st.markdown("##### Пресная вода, т (FRESH-PTS / FRESH-STB)")
            m_fresh_p = float(
                st.number_input(
                    "FRESH-PTS.P (лев), т",
                    min_value=0.0,
                    value=0.0,
                    step=0.5,
                    help=f"Ориентир макс. ≈ {M_MAX_FW_SIDE:.2f} т при 100%",
                    key="holds_fresh_p",
                )
            )
            m_fresh_s = float(
                st.number_input(
                    "FRESH-STB.S (прав), т",
                    min_value=0.0,
                    value=0.0,
                    step=0.5,
                    help=f"Ориентир макс. ≈ {M_MAX_FW_SIDE:.2f} т",
                    key="holds_fresh_s",
                )
            )
            m_fw = m_fresh_p + m_fresh_s

    with st.container(border=True):
        st.markdown("##### Балластная вода по цистернам (разд. 6 буклета), т")
        st.caption(
            "Пять цистерн: нос **BW-01** лев/прав, корма **BW-02** лев/прав, **носовой пик**. "
            "Подсказки «?» — ориентир макс. при 100% из буклета."
        )
        ba1, ba2, ba3 = st.columns(3)
        with ba1:
            m_bw01_p = float(
                st.number_input(
                    "BW-01 PTS-FWD.P (нос, лев), т",
                    min_value=0.0,
                    value=0.0,
                    step=1.0,
                    help=f"Макс. ≈ {M_MAX_BW01:.2f} т",
                    key="holds_bw01_p",
                )
            )
        with ba2:
            m_bw01_s = float(
                st.number_input(
                    "BW-01 STB-FWD.S (нос, прав), т",
                    min_value=0.0,
                    value=0.0,
                    step=1.0,
                    help=f"Макс. ≈ {M_MAX_BW01:.2f} т",
                    key="holds_bw01_s",
                )
            )
        with ba3:
            m_fore = float(
                st.number_input(
                    "FORE PEAK SW.C (носовой пик), т",
                    min_value=0.0,
                    value=0.0,
                    step=1.0,
                    help=f"Макс. ≈ {M_MAX_FORE:.2f} т",
                    key="holds_fore",
                )
            )
        ba4, ba5, _ = st.columns([1, 1, 1])
        with ba4:
            m_bw02_p = float(
                st.number_input(
                    "BW-02 PTS-AFT.P (корма, лев), т",
                    min_value=0.0,
                    value=0.0,
                    step=1.0,
                    help=f"Макс. ≈ {M_MAX_BW02:.2f} т",
                    key="holds_bw02_p",
                )
            )
        with ba5:
            m_bw02_s = float(
                st.number_input(
                    "BW-02 STB-AFT.S (корма, прав), т",
                    min_value=0.0,
                    value=0.0,
                    step=1.0,
                    help=f"Макс. ≈ {M_MAX_BW02:.2f} т",
                    key="holds_bw02_s",
                )
            )

    m_ballast_sum = m_bw01_p + m_bw01_s + m_fore + m_bw02_p + m_bw02_s

    m_other = st.number_input(
        "Прочее без груза в трюмах (корпус порожний, снабжение, экипаж и т.д.), т",
        min_value=0.0,
        value=2225.0,
        step=10.0,
        help="Всё, кроме насыпного груза в трюмах: вместе с балластом и жидкостями выше даёт «массу без трюмного груза».",
        key="holds_m_other",
    )

    m_wo_hold = (
        float(m_fuel_tanks)
        + float(m_fuel_svc)
        + float(m_fw)
        + m_ballast_sum
        + float(m_other)
    )
    delta_h, t_mean_h, cargo_h = cargo_mass_from_drafts(t_fwd, t_aft, m_wo_hold)
    trim_cm = (float(t_aft) - float(t_fwd)) * 100.0

    st.markdown("---")
    r1, r2, r3, r4 = st.columns(4)
    r1.metric("Средняя осадка T_ср", f"{t_mean_h:.3f} м")
    r2.metric("Дифферент (корма − нос)", f"{trim_cm:+.1f} см")
    r3.metric("Водоизмещение Δ", f"{delta_h:,.0f} т".replace(",", " "))
    r4.metric("Погруженный груз в трюмах (оценка)", f"{cargo_h:,.0f} т".replace(",", " "))

    if cargo_h <= 0:
        st.warning(
            "Сумма масс **без трюмного груза** получается не меньше **Δ** по осадке — проверьте осадки и введённые массы."
        )
    else:
        with st.container(border=True):
            st.success(
                f"Оценка массы **насыпного груза в трюмах** (уголь и т.п.): **{cargo_h:,.1f} т**.".replace(",", " ")
            )
            rho_h = st.number_input("Плотность груза для объёма, т/м³", 0.5, 1.3, 0.85, 0.05, key="rho_holds")
            if rho_h > 0:
                st.caption(f"Ориентировочный объём: **{cargo_h / rho_h:,.0f} м³**".replace(",", " "))

    with st.expander("Как считается"):
        st.markdown(
            f"""
- **T_ср** = (T_нос + T_корма) / 2 → по гидростатике буклета **Δ** (т).
- **M_груз_трюмы** = Δ − (топливо + пресная вода + **сумма пяти балластных цистерн** + прочее).
- Кривые **GZ** в буклете для **дифферента 0**; при большом дифференте оценка **приближённая**.
- Глубина по маркировке: **{SHIP["depth_m"]}** м.
            """
        )

    st.caption(
        f"Без трюмного груза учтено: **{m_wo_hold:,.1f}** т "
        f"(топливо {m_fuel_tanks + m_fuel_svc:.1f} + пресная {m_fw:.1f} т — FRESH-P {m_fresh_p:.1f} + FRESH-S {m_fresh_s:.1f} + "
        f"балласт **{m_ballast_sum:.1f}** + прочее {m_other:.1f}).".replace(",", " ")
    )
