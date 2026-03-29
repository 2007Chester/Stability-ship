"""
Расчёт остойчивости баржи по буклету (РЕЙД-8): GZ, критерии ИМО A.749, уголь по осадке.
Запуск: streamlit run app.py
"""

from __future__ import annotations

import sys
from pathlib import Path

# Запуск из папки stability_app
sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np
import plotly.graph_objects as go
import streamlit as st

from ship_data import SHIP
from stability import (
    block_coefficient,
    coal_mass_from_draft,
    coal_mass_table,
    combine_masses,
    displacement_from_draft,
    draft_from_displacement,
    gm_metacentric,
    imo749_intact,
    kmt_from_displacement,
    roll_angle_theta1_deg,
    wind_heeling_levers,
)

st.set_page_config(page_title="Остойчивость — РЕЙД-8", layout="wide")

st.title("Остойчивость судна и груз (уголь)")
st.caption(SHIP["doc_note"])

with st.sidebar:
    st.header("Параметры судна")
    st.markdown(
        f"**{SHIP['name']}**  \n"
        f"L = {SHIP['loa_m']} м, B = {SHIP['beam_m']} м, D = {SHIP['depth_m']} м  \n"
        f"Летняя осадка (маркировка): {SHIP['draft_summer_m']} м  \n"
        f"ρ морской воды: {SHIP['rho_sea_t_m3']} т/м³"
    )
    theta_flood = st.number_input(
        "Угол заливания θзал (°) для критерия площади 30–40°",
        min_value=5.0,
        max_value=90.0,
        value=40.0,
        step=1.0,
        help="Если меньше 40°, верхняя граница интеграла — min(40°, θзал).",
    )
    fsc = st.number_input(
        "Поправка на ПВСВ (потеря GM), м",
        min_value=0.0,
        max_value=5.0,
        value=0.0,
        step=0.01,
    )

st.subheader("Массы и центры тяжести (от киля, м)")
st.markdown(
    "Задайте состав нагрузки. **KG** — аппликата центра тяжести каждой группы от основной плоскости (киль)."
)

c1, c2, c3 = st.columns(3)
with c1:
    m_light = st.number_input("Порожний корпус + постоянные вещи, т", value=SHIP["lightship_mass_t"], step=10.0)
    kg_light = st.number_input("KG порожнего, м", value=SHIP["lightship_vcg_m"], step=0.01)
with c2:
    m_fuel = st.number_input("Топливо / ДТ / масла, т", value=0.0, step=1.0)
    kg_fuel = st.number_input("KG топлива, м", value=3.6, step=0.05)
with c3:
    m_ballast = st.number_input("Балласт и пресная вода, т", value=0.0, step=10.0)
    kg_ballast = st.number_input("KG балласта, м", value=3.5, step=0.05)

c4, c5 = st.columns(2)
with c4:
    m_stores = st.number_input("Прочие припасы и снабжение, т", value=0.0, step=1.0)
    kg_stores = st.number_input("KG припасов, м", value=5.0, step=0.1)
with c5:
    m_coal = st.number_input("Уголь (или иной однородный груз), т", value=3500.0, step=50.0)
    kg_coal = st.number_input("KG угля, м", value=4.5, step=0.05)

items = [
    (m_light, kg_light),
    (m_fuel, kg_fuel),
    (m_ballast, kg_ballast),
    (m_stores, kg_stores),
    (m_coal, kg_coal),
]
delta_t, kg_total = combine_masses(items)
vcg_m = kg_total

if delta_t <= 0:
    st.error("Суммарная масса должна быть больше нуля.")
    st.stop()

t_mean = draft_from_displacement(delta_t)
gm = gm_metacentric(delta_t, kg_total, fsc)
kmt = kmt_from_displacement(delta_t)

m_wo_coal = m_light + m_fuel + m_ballast + m_stores

crit, meta = imo749_intact(delta_t, vcg_m, kg_total, fsc, theta_flood)
ok_all = all(c.ok for c in crit)

tab1, tab2, tab3 = st.tabs(["Сводка и критерии", "Диаграмма GZ", "Уголь по осадке"])

with tab1:
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Водоизмещение Δ", f"{delta_t:,.0f} т".replace(",", " "))
    k2.metric("Средняя осадка T", f"{t_mean:.3f} м")
    k3.metric("KG (общий)", f"{kg_total:.3f} м")
    k4.metric("GM (с ПВСВ)", f"{gm:.3f} м")
    st.caption(f"KMT ≈ {kmt:.3f} м при данном Δ (из гидростатики буклета).")
    st.subheader("Критерии остойчивости неповреждённого судна (ИМО A.749 / буклет)")
    for c in crit:
        icon = "✅" if c.ok else "❌"
        st.markdown(f"{icon} **{c.code}.** {c.description} — требуется {c.required}; **факт:** {c.actual}")
    if ok_all:
        st.success("Все пять критериев выполняются (по введённым данным и таблицам буклета).")
    else:
        st.warning("Есть невыполненные критерии — скорректируйте массы, KG или угол заливания.")

with tab2:
    phis = meta["phis_deg"]
    gzs = meta["gz_m"]
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=phis,
            y=gzs,
            mode="lines",
            name="GZ(φ)",
            line=dict(width=2, color="#1a5f7a"),
            fill="tozeroy",
            fillcolor="rgba(26,95,122,0.15)",
        )
    )
    fig.add_hline(y=0, line_dash="dot", line_color="#666")
    for xv, lab in [(15, "15°"), (30, "30°"), (40, "40°")]:
        fig.add_vline(x=xv, line_dash="dot", line_color="#aaa", annotation_text=lab)
    fig.update_layout(
        title="Диаграмма статической остойчивости (плечо GZ)",
        xaxis_title="Угол крена φ, °",
        yaxis_title="GZ, м",
        height=480,
        template="plotly_white",
        hovermode="x unified",
    )
    st.plotly_chart(fig, use_container_width=True)
    st.caption(
        "Кривая построена по интерполяционным данным буклета (дифферент 0, VCG=0) "
        "с поправкой GZ = GZ₀ − VCG·sin φ."
    )

with tab3:
    st.markdown(
        "**Масса погруженного/принятого угля** определяется как разность между "
        "водоизмещением по осадке и массой всего остального на борту (без угля)."
    )
    st.latex(r"M_{\text{уголь}} = \Delta(T) - M_{\text{прочее}}")
    m_fixed = st.number_input(
        "Масса на борту без угля (порожний + припасы + топливо + балласт), т",
        value=float(m_wo_coal),
        step=10.0,
        key="m_fixed_coal",
    )
    t_pick = st.slider("Средняя осадка T, м", 1.2, 4.4, float(round(t_mean, 2)), 0.01)
    d_at_t = displacement_from_draft(t_pick)
    coal_t = coal_mass_from_draft(t_pick, m_fixed)
    st.metric("При выбранной осадке", f"Δ = {d_at_t:,.0f} т; уголь ≈ {coal_t:,.0f} т".replace(",", " "))
    rho_coal = st.number_input("Плотность угля (для объёма), т/м³", value=0.85, min_value=0.5, max_value=1.2, step=0.05)
    if rho_coal > 0:
        st.caption(f"Ориентировочный занимаемый объём угля: **{coal_t / rho_coal:,.0f} м³**".replace(",", " "))

    st.subheader("Таблица: осадка → уголь")
    tbl = coal_mass_table(m_fixed, 1.2, 4.4, 0.1)
    st.dataframe(
        [
            {"T, м": a, "Δ, т": round(b, 1), "Уголь, т": round(c, 1)}
            for a, b, c in tbl[::2]
        ],
        use_container_width=True,
        hide_index=True,
    )

st.divider()
st.subheader("Погодный критерий (справочно)")
st.markdown(
    "По буклету требуется сравнение площадей **a** и **b** на диаграмме энергии с учётом "
    "ветра (LW1, LW2) и угла качки θ₁. Ниже — расчёт величин из текста буклета без графического интеграла."
)
wc1, wc2, wc3 = st.columns(3)
with wc1:
    a_proj = st.number_input("Проектируемая площадь боковой проекции A, м²", value=800.0, step=10.0)
    z_w = st.number_input("Z (от центра A до ~половины осадки), м", value=4.0, step=0.1)
with wc2:
    ak_sk = st.number_input("Площадь скуловых килей Ak, м²", value=0.0, step=1.0)
    og_m = st.number_input("OG (аппликата G относительно ватерлинии, + вверх), м", value=-1.0, step=0.1)
with wc3:
    p_wind = st.number_input("Давление ветра P, Па", value=504.0, step=1.0)

lw1, lw2 = wind_heeling_levers(p_wind, a_proj, z_w, delta_t)
cb_est = block_coefficient(delta_t)
theta1 = roll_angle_theta1_deg(
    b_m=SHIP["beam_m"],
    d_m=max(t_mean, 0.5),
    l_m=SHIP["loa_m"],
    cb=cb_est,
    gm_m=max(gm, 1e-6),
    ak_m2=ak_sk,
    og_m=og_m,
)
st.write(f"**LW1** = {lw1:.4f} м; **LW2** = {lw2:.4f} м; **θ₁** (качка) ≈ **{theta1:.2f}°**; **Cb** (оценка) ≈ **{cb_est:.3f}**.")
st.caption("Окончательное выполнение погодного критерия — по энергетической диаграмме из буклета (площади a и b).")
