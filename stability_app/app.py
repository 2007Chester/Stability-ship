"""
РЕЙД-8: остойчивость (ИМО A.749 + диаграмма GZ) и груз в трюмах по осадкам.

Запуск: python3 -m streamlit run app.py
"""

from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from calc_state import apply_calc_state, export_calc_state

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from cargo_excel_data import PRESET_V2_GRUZ
from tank_booklet import BOOKLET_TANKS, x_table_from_lcg_ap
from excel_ui import (
    COL_KG,
    COL_MASS,
    COL_NAME,
    COL_X,
    style_trim_excel,
    trim_table_excel_with_total,
    x_g_to_from_ap,
)
from ship_data import SHIP
from sounding_tables import load_fresh_sounding_tables, table_for_fresh_tank, tons_from_sounding_mm
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
    theta_flood = st.slider(
        "Угол заливания θзал, °", 5.0, 90.0, 55.0, 1.0, key="sb_theta_flood"
    )
    fsc = st.number_input("ПВСВ (потеря GM), м", 0.0, 5.0, 0.0, 0.01, key="sb_fsc")
    gg0 = st.number_input("GG₀ (лед и т.п.), м", 0.0, 3.0, 0.0, 0.001, key="sb_gg0")
    lcf_ap_m = st.number_input(
        "LCF от кормы, м",
        0.0,
        float(LBP_M),
        float(LBP_M) / 2.0,
        0.1,
        key="sb_lcf_ap_m",
    )
    x_from_midship = st.toggle(
        "Xг в таблице от миделя (+ к носу)",
        value=True,
        help="Как в Trim Excel: LCG считается через LBP/2 + X.",
        key="sb_x_from_midship",
    )

    with st.expander("Сохранение расчёта", expanded=False):
        st.caption("Скачайте JSON со всеми полями или загрузите ранее сохранённый файл.")
        payload = export_calc_state(st.session_state)
        ts = datetime.now().strftime("%Y%m%d-%H%M%S")
        fname = f"raid8-raschet-{ts}.json"
        st.download_button(
            label="Скачать расчёт (.json)",
            data=json.dumps(payload, ensure_ascii=False, indent=2),
            file_name=fname,
            mime="application/json",
            use_container_width=True,
        )
        up = st.file_uploader("Файл для загрузки", type=["json"], key="calc_state_upload")
        if st.button("Загрузить расчёт в форму", use_container_width=True):
            if up is None:
                st.warning("Выберите файл .json.")
            else:
                try:
                    data = json.loads(up.getvalue().decode("utf-8"))
                    apply_calc_state(data, st.session_state)
                    st.success("Параметры загружены.")
                    st.rerun()
                except (json.JSONDecodeError, ValueError, UnicodeDecodeError) as e:
                    st.error(f"Не удалось загрузить: {e}")

# ——— две страницы ———
tab_stab, tab_holds = st.tabs(["Остойчивость", "Груз в трюмах по осадкам"])


def _stab_preset_values(name: str) -> dict[str, float]:
    """Начальные значения полей вкладки остойчивости по шаблону."""
    if name == "В грузу (из Excel)":
        return dict(PRESET_V2_GRUZ)
    if name == "Пустая строка":
        return {
            "stab_m_stores": 0.0,
            "stab_x_stores": 0.0,
            "stab_kg_stores": 4.5,
            "stab_m_fuel_svc": 0.0,
            "stab_x_fuel_svc": 0.0,
            "stab_kg_fuel_svc": 4.5,
            **{f"stab_t{i}": 0.0 for i in range(9)},
            "stab_m_coal": 0.0,
            "stab_x_coal": 0.0,
            "stab_kg_coal": 4.5,
        }
    # Без груза (балласт)
    return {
        "stab_m_stores": 9.0,
        "stab_x_stores": -46.0,
        "stab_kg_stores": 7.2,
        "stab_m_fuel_svc": 0.0,
        "stab_x_fuel_svc": -46.0,
        "stab_kg_fuel_svc": 1.2,
        "stab_t0": 0.0,
        "stab_t1": 0.0,
        "stab_t2": 0.0,
        "stab_t3": 0.0,
        "stab_t4": 0.0,
        "stab_t5": 0.0,
        "stab_t6": 0.0,
        "stab_t7": 51.0,
        "stab_t8": 50.0,
        "stab_m_coal": 0.0,
        "stab_x_coal": 0.0,
        "stab_kg_coal": 4.5,
    }


with tab_stab:
    st.markdown("## Расчёт остойчивости")
    st.caption(
        "Массы **по цистернам буклета** — **LCG и KG жидкости** только из **разд. 6** (`tank_booklet.py`); **порожнее** из буклета (фикс.), снабжение, расходные, **уголь**. "
        "Сумма масс → Δ и осадка; ниже — **GM**, **ИМО A.749**, диаграмма **GZ**."
    )

    preset = st.selectbox(
        "Шаблон",
        ["В грузу (из Excel)", "Пустая строка", "Без груза (балласт)"],
        index=0,
        key="preset_v2",
    )
    if st.session_state.get("last_preset_v2") != preset:
        for k, v in _stab_preset_values(preset).items():
            st.session_state[k] = v
        st.session_state.last_preset_v2 = preset

    _pf = st.session_state.pop("_pending_fresh_mass", None)
    if isinstance(_pf, dict):
        if "stab_t2" in _pf:
            st.session_state["stab_t2"] = float(_pf["stab_t2"])
        if "stab_t3" in _pf:
            st.session_state["stab_t3"] = float(_pf["stab_t3"])

    x_note = "**X** — от миделя (+ к носу)" if x_from_midship else "**X** — от шп. кормы вперёд"

    _ls_lcg_ap = float(SHIP["lightship_lcg_m"])
    m_light = float(SHIP["lightship_mass_t"])
    kg_light = float(SHIP["lightship_vcg_m"])
    x_light = x_table_from_lcg_ap(_ls_lcg_ap, LBP_M, x_from_midship=x_from_midship)

    with st.container(border=True):
        st.markdown("##### Порожнее судно и снабжение")
        st.caption(
            f"{x_note} · Порожнее судно **из буклета** (постоянно): **{m_light:,.2f}** т, "
            f"LCG от кормы **{_ls_lcg_ap:.3f}** м → X в таблице **{x_light:.3f}** м, KG **{kg_light:.3f}** м."
        )
        m_stores = st.number_input("Судовое снабжение, т", 0.0, 5000.0, key="stab_m_stores", step=1.0)
        x_stores = st.number_input("X снабжения, м", -200.0, 200.0, key="stab_x_stores", step=0.01)
        kg_stores = st.number_input("KG снабжения, м", 0.0, 30.0, key="stab_kg_stores", step=0.01)

    with st.container(border=True):
        st.markdown("##### Топливо и пресная вода (LCG/KG из буклета)")
        st.caption("Масса в тоннах; положение центра тяжести жидкости — по таблице вместимости (100%).")
        tf1, tf2 = st.columns(2)
        with tf1:
            st.markdown("**Дизельное топливо**")
            st.caption(
                "**LCG/KG** — из разд. 6 буклета (как при полной вместимости); при частичном заполнении модель такая же, как в методике буклета."
            )
            m_t0 = st.number_input(
                BOOKLET_TANKS[0][0].replace(" (топливо, лев)", ""),
                0.0,
                500.0,
                key="stab_t0",
                step=0.5,
                help=f"Макс. ≈ {BOOKLET_TANKS[0][3]:.2f} т",
            )
            m_t1 = st.number_input(
                BOOKLET_TANKS[1][0].replace(" (топливо, прав)", ""),
                0.0,
                500.0,
                key="stab_t1",
                step=0.5,
                help=f"Макс. ≈ {BOOKLET_TANKS[1][3]:.2f} т",
            )
            m_fuel_svc = st.number_input("Расходные цистерны (не из табл. буклета), т", 0.0, 200.0, key="stab_m_fuel_svc", step=0.5)
            x_fuel_svc = st.number_input("X расходных, м", -200.0, 200.0, key="stab_x_fuel_svc", step=0.01)
            kg_fuel_svc = st.number_input("KG расходных, м", 0.0, 15.0, key="stab_kg_fuel_svc", step=0.01)
        with tf2:
            st.markdown("**Пресная вода**")
            _ftbl = load_fresh_sounding_tables()
            _has_snd = bool(_ftbl.get("FRESH")) or bool(_ftbl.get("FRESH-PTS.P")) or bool(_ftbl.get("FRESH-STB.S"))
            with st.expander("Замер глубины (sounding) → тонны", expanded=False):
                st.caption(
                    "Таблица **мм → т** из GHS/буклета: файл `stability_app/data/sounding_fresh.json`. "
                    "Ключ **FRESH** — одна кривая на оба борта; иначе **FRESH-PTS.P** и **FRESH-STB.S**."
                )
                if not _has_snd:
                    st.info("Таблица не заполнена — введите массу вручную выше или добавьте JSON (см. docs/08-zamery-presnoj-vody.md).")
                else:
                    _tp = table_for_fresh_tank("P", _ftbl)
                    _ts = table_for_fresh_tank("S", _ftbl)
                    sp = st.number_input("Замер левого танка (мм)", 0.0, 50000.0, 0.0, 1.0, key="snd_fresh_mm_p")
                    ss = st.number_input("Замер правого танка (мм)", 0.0, 50000.0, 0.0, 1.0, key="snd_fresh_mm_s")
                    wp = tons_from_sounding_mm(sp, _tp)
                    ws = tons_from_sounding_mm(ss, _ts)
                    if wp is not None:
                        st.caption(f"Лев: **≈ {wp:.2f} т** по таблице")
                    if ws is not None:
                        st.caption(f"Прав: **≈ {ws:.2f} т** по таблице")
                    b1, b2 = st.columns(2)
                    with b1:
                        if st.button("Подставить массу левого", key="apply_snd_fresh_p", disabled=wp is None):
                            st.session_state["_pending_fresh_mass"] = {"stab_t2": float(wp)}
                            st.rerun()
                    with b2:
                        if st.button("Подставить массу правого", key="apply_snd_fresh_s", disabled=ws is None):
                            st.session_state["_pending_fresh_mass"] = {"stab_t3": float(ws)}
                            st.rerun()
            m_t2 = st.number_input(
                BOOKLET_TANKS[2][0].replace(" (пресная, лев)", ""),
                0.0,
                500.0,
                key="stab_t2",
                step=0.5,
                help=f"Макс. ≈ {BOOKLET_TANKS[2][3]:.2f} т",
            )
            m_t3 = st.number_input(
                BOOKLET_TANKS[3][0].replace(" (пресная, прав)", ""),
                0.0,
                500.0,
                key="stab_t3",
                step=0.5,
                help=f"Макс. ≈ {BOOKLET_TANKS[3][3]:.2f} т",
            )

    with st.container(border=True):
        st.markdown("##### Балластная вода (разд. 6 буклета)")
        b1, b2, b3 = st.columns(3)
        with b1:
            m_t4 = st.number_input(BOOKLET_TANKS[4][0], 0.0, 500.0, key="stab_t4", step=1.0, help=f"Макс. ≈ {BOOKLET_TANKS[4][3]:.2f} т")
            m_t5 = st.number_input(BOOKLET_TANKS[5][0], 0.0, 500.0, key="stab_t5", step=1.0, help=f"Макс. ≈ {BOOKLET_TANKS[5][3]:.2f} т")
        with b2:
            m_t6 = st.number_input(BOOKLET_TANKS[6][0], 0.0, 500.0, key="stab_t6", step=1.0, help=f"Макс. ≈ {BOOKLET_TANKS[6][3]:.2f} т")
        with b3:
            m_t7 = st.number_input(BOOKLET_TANKS[7][0], 0.0, 500.0, key="stab_t7", step=1.0, help=f"Макс. ≈ {BOOKLET_TANKS[7][3]:.2f} т")
            m_t8 = st.number_input(BOOKLET_TANKS[8][0], 0.0, 500.0, key="stab_t8", step=1.0, help=f"Макс. ≈ {BOOKLET_TANKS[8][3]:.2f} т")

    with st.container(border=True):
        st.markdown("##### Уголь (насыпной груз в трюмах)")
        st.caption(x_note)
        u1, u2 = st.columns(2)
        with u1:
            m_coal = st.number_input("Масса угля, т", 0.0, 20000.0, key="stab_m_coal", step=50.0)
        with u2:
            kg_coal = st.number_input("KG угля, м", 0.0, 20.0, key="stab_kg_coal", step=0.01)
        if x_from_midship:
            _coal_x_rng = (-float(LBP_M) / 2.0 - 5.0, float(LBP_M) / 2.0 + 5.0)
        else:
            _coal_x_rng = (-1.0, float(LBP_M) + 2.0)
        x_coal = st.slider(
            "X угля, м",
            float(_coal_x_rng[0]),
            float(_coal_x_rng[1]),
            key="stab_x_coal",
            step=0.05,
            help="Совпадает с колонкой X в таблице ниже (LCG от кормы при отображении в числах таблицы).",
        )

    tank_mass = [float(st.session_state.get(f"stab_t{i}", 0.0)) for i in range(9)]

    rows: list[dict[str, str | float]] = [
        {COL_NAME: "Судно порожнее", COL_MASS: m_light, COL_X: x_light, COL_KG: kg_light},
        {COL_NAME: "Судовое снабжение", COL_MASS: m_stores, COL_X: x_stores, COL_KG: kg_stores},
    ]
    for i, tm in enumerate(tank_mass):
        if tm <= 0:
            continue
        name, lcg_ap, kg_t, _mx = BOOKLET_TANKS[i]
        xg = x_table_from_lcg_ap(lcg_ap, LBP_M, x_from_midship=x_from_midship)
        rows.append({COL_NAME: name, COL_MASS: tm, COL_X: xg, COL_KG: kg_t})
    if float(m_fuel_svc) > 0:
        rows.append(
            {
                COL_NAME: "Топливо расходные",
                COL_MASS: float(m_fuel_svc),
                COL_X: float(x_fuel_svc),
                COL_KG: float(kg_fuel_svc),
            }
        )
    if float(m_coal) > 0:
        rows.append({COL_NAME: "Уголь", COL_MASS: m_coal, COL_X: x_coal, COL_KG: kg_coal})

    edited = pd.DataFrame(rows)

    tbl_excel = trim_table_excel_with_total(
        edited, x_from_midship=x_from_midship, lbp_m=LBP_M
    )
    if not tbl_excel.empty:
        with st.container(border=True):
            st.markdown("##### Итог (моменты, LCG, KG)")
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
    crit, meta = imo749_intact(delta_t, kg0, fsc, theta_flood)
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
        "Введите **осадки**, массы **топлива**, **пресной воды**, **балласта** (все — **тонны**). "
        "**Порожнее судно** и **снабжение** берутся с вкладки «Остойчивость» (буклет + ваш ввод) — оценка **массы насыпного груза в трюмах**."
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

    m_light = float(SHIP["lightship_mass_t"])
    m_stores = float(st.session_state.get("stab_m_stores", 0.0))
    m_other = m_light + m_stores
    st.markdown("##### Порожнее и снабжение (фиксировано по буклету и вкладке «Остойчивость»)")
    st.caption(
        "Сумма **массы порожнего судна** из буклета и **судового снабжения** с первой вкладки — без насыпного груза в трюмах и без топлива/пресной/балласта ниже."
    )
    st.metric(
        "Порожнее + снабжение, т",
        f"{m_other:,.2f}".replace(",", " "),
        help=f"Порожнее {m_light:,.2f} т + снабжение {m_stores:,.2f} т (поле «Судовое снабжение» на вкладке «Остойчивость»).".replace(",", " "),
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
- **M_груз_трюмы** = Δ − (топливо + пресная вода + **сумма пяти балластных цистерн** + порожнее + снабжение).
- Кривые **GZ** в буклете для **дифферента 0**; при большом дифференте оценка **приближённая**.
- Глубина по маркировке: **{SHIP["depth_m"]}** м.
            """
        )

    st.caption(
        f"Без трюмного груза учтено: **{m_wo_hold:,.1f}** т "
        f"(топливо {m_fuel_tanks + m_fuel_svc:.1f} + пресная {m_fw:.1f} т — FRESH-P {m_fresh_p:.1f} + FRESH-S {m_fresh_s:.1f} + "
        f"балласт **{m_ballast_sum:.1f}** + порожнее/снабжение {m_other:.1f}).".replace(",", " ")
    )
