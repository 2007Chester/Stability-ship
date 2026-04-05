"""
Расчёт остойчивости баржи по буклету (РЕЙД-8): GZ, критерии ИМО A.749, уголь по осадке,
таблица загрузки и критерии в духе рабочих Excel (РМРС).

Данные пресета «В грузу (из Excel)» — в cargo_excel_data.py (обновляйте при смене книги Excel).

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

from rs_criteria import (
    block_cb_from_nabla,
    lw_wind_m,
    rs_acceleration_a_calc,
    rs_acceleration_k_star,
    rs_inertial_c,
    rs_k_theta_bd,
    theta1_roll_deg,
    weather_energy_areas,
)
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

LBP_M = float(SHIP.get("lbp_m", 96.78))
from stability import (
    cargo_mass_from_drafts,
    coal_mass_from_draft,
    coal_mass_table,
    combine_masses,
    displacement_from_draft,
    draft_from_displacement,
    drafts_fwd_aft_from_lcg,
    gm_metacentric,
    imo749_intact,
    kmt_from_displacement,
)

st.set_page_config(page_title="Остойчивость — РЕЙД-8", layout="wide")

st.title("Остойчивость судна и груз (уголь)")
st.caption(SHIP["doc_note"] + " Дополнительно: таблица как в «Trim calc», погодный критерий с площадями A/B, критерий ускорения РМРС 3.12.3.")

with st.expander("Что здесь происходит (если вы не судовой инженер)", expanded=False):
    st.markdown(
        """
**Остойчивость** — это способность судна после небольшого крена **самому вернуться** в вертикальное положение (как неваляшка, только законы физики и форма корпуса).

- **Водоизмещение** — масса воды, которую «вытеснил» корпус; по ней и таблицам буклета находят **осадку** (насколько судно погружено).
- **Центр тяжести G** и его высота **KG** важны: чем выше груз от киля, тем «легче» перевернуть судно в бок — хуже запас остойчивости.
- **GM** — краткая мера «жёсткости» крена в малых углах; **GZ(φ)** — **плечо статической остойчивости**: насколько сила, возвращающая судно, «сильнее» при данном угле крена φ.
- **Критерии ИМО** — проверки по цифрам из буклета: не «хорошо/плохо на глаз», а сравнение с нормами (площади под кривой GZ, углы и т.д.).
- Вкладки **«Уголь по осадке»** и **«Погода…»** — практические оценки: сколько угля вмещается при заданной осадке и как считаются **ветер + качка** в духе рабочих Excel.

Ниже вы вводите массы и положение груза; программа пересчитывает осадку, GZ и проверки автоматически.
        """
    )

with st.sidebar:
    st.header("Параметры судна")
    st.markdown(
        f"**{SHIP['name']}**  \n"
        f"L = {SHIP['loa_m']} м, LBP ≈ {LBP_M} м, B = {SHIP['beam_m']} м, D = {SHIP['depth_m']} м  \n"
        f"Летняя осадка (маркировка): {SHIP['draft_summer_m']} м  \n"
        f"ρ морской воды: {SHIP['rho_sea_t_m3']} т/м³"
    )
    with st.expander("Подсказки к полям ниже"):
        st.markdown(
            """
**Угол заливания θзал** — угол крена, при котором через открытые люки/борта может зайти вода. От него зависят пределы интегралов в критериях и «погодной» проверке: чем меньше угол «безопасен», тем строже требования.

**ПВСВ (FSC)** — поправка на неидеальность груза и свободные поверхности жидкостей; **уменьшает** эффективный GM. Если не уверены — оставьте 0 и уточните у класса/расчётчика.

**GG₀** — насколько **дополнительно подняли** центр тяжести (лёд на надстройках, учёт в таблице Excel). Фактически считаем **KG₀ = KG + GG₀** — выше G, ниже запас остойчивости.
            """
        )
    theta_flood = st.number_input(
        "Угол заливания θзал (°) для критериев и погоды",
        min_value=5.0,
        max_value=90.0,
        value=55.0,
        step=1.0,
        help="ИМО A.749: площадь 30–40°; погодный критерий: верхний предел энергии b.",
    )
    fsc = st.number_input(
        "Потеря GM от ПВСВ (FSC), м",
        min_value=0.0,
        max_value=5.0,
        value=0.0,
        step=0.01,
    )
    gg0 = st.number_input(
        "GG₀ — дополнительная аппликата G (лед, ПВСВ в таблице Excel), м",
        min_value=0.0,
        max_value=3.0,
        value=0.0,
        step=0.001,
        help="KG₀ = KG + GG₀ для кривой GZ, как на листе «weather criteria».",
    )
    lcf_ap_m = st.number_input(
        "LCF от шп. кормы (м), для осадок нос/корма",
        min_value=0.0,
        max_value=float(LBP_M),
        value=float(LBP_M) / 2.0,
        step=0.1,
        help="Центр плавания по длине; для симметричной баржи часто ≈ LBP/2. Нужен вместе с LCG.",
    )
    x_coord_mode = st.radio(
        "Координата Xг в таблице (режим «Excel»)",
        ["От шп. кормы (вперёд)", "От миделя (+ к носу, как в Trim Excel)"],
        index=1,
        key="x_coord_trim",
        help=(
            "На листе Excel X часто **от миделя** (к носу +). Тогда для LCG и дифферента нужно: "
            "X_от кормы = LBP/2 + X_от миделя. Если по ошибке считать отрицательные X от кормы, "
            "получается неверный LCG, отрицательная осадка носа и огромный дифферент."
        ),
    )
    x_from_midship = x_coord_mode.startswith("От миделя")

st.subheader("Ввод масс")
st.caption(
    "Укажите, что стоит на борту: массу (тонны) и высоту центра тяжести каждой группы (**KG** — высота **G** над килем, м). "
    "Сумма масс даёт **водоизмещение**; по нему определяется **осадка** и кривая **GZ**."
)
mode = st.radio(
    "Режим",
    ["По группам (упрощённо)", "Таблица загрузки (как в Excel)"],
    horizontal=True,
    index=1,
    key="stability_input_mode",
    help="По умолчанию — таблица как в Excel; данные «В грузу» подставляются из файла cargo_excel_data.py.",
)

if mode.startswith("По группам"):
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
    lcg_m = None
else:
    preset = st.selectbox(
        "Шаблон строк (можно править)",
        [
            "Пусто (одна строка)",
            "В грузу (из Excel)",
            "Без груза",
            "Балласт + обледенение",
        ],
        index=1,
        key="preset_trim",
        help="«В грузу» — строки из рабочей Excel, см. cargo_excel_data.py.",
    )
    defaults = {
        "Пусто (одна строка)": [
            {COL_NAME: "Груз / балласт", COL_MASS: 1000.0, COL_X: 0.0, COL_KG: 4.5},
        ],
        "В грузу (из Excel)": [dict(r) for r in ROWS_CARGO_IN_GRUZ],
        "Без груза": [
            {COL_NAME: "Судно порожнее", COL_MASS: 2210.0, COL_X: 4.133, COL_KG: 4.58},
            {COL_NAME: "Снабжение", COL_MASS: 9.0, COL_X: -46.0, COL_KG: 7.2},
            {COL_NAME: "Балласт Л/Б", COL_MASS: 51.0, COL_X: -37.8, COL_KG: 1.15},
            {COL_NAME: "Балласт ПР/Б", COL_MASS: 50.0, COL_X: -37.8, COL_KG: 1.15},
        ],
        "Балласт + обледенение": [
            {COL_NAME: "Судно порожнее", COL_MASS: 2210.0, COL_X: 4.133, COL_KG: 4.58},
            {COL_NAME: "Снабжение", COL_MASS: 9.0, COL_X: -46.0, COL_KG: 7.2},
            {COL_NAME: "Обледенение", COL_MASS: 78.0, COL_X: 45.67, COL_KG: 6.36},
            {COL_NAME: "Балласт Л/Б", COL_MASS: 30.0, COL_X: -37.8, COL_KG: 1.15},
            {COL_NAME: "Балласт ПР/Б", COL_MASS: 30.0, COL_X: -37.8, COL_KG: 1.15},
        ],
    }
    last = st.session_state.get("last_trim_preset")
    if last != preset or "load_df" not in st.session_state:
        st.session_state.load_df = pd.DataFrame(defaults[preset])
        st.session_state.last_trim_preset = preset
    else:
        st.session_state.load_df = normalize_load_columns(st.session_state.load_df)
    edited = st.data_editor(
        st.session_state.load_df,
        num_rows="dynamic",
        use_container_width=True,
        key="editor_load",
        column_config={
            COL_NAME: st.column_config.TextColumn(COL_NAME, width="large", required=True),
            COL_MASS: st.column_config.NumberColumn(COL_MASS, format="%.2f", min_value=0.0),
            COL_X: st.column_config.NumberColumn(COL_X, format="%.3f"),
            COL_KG: st.column_config.NumberColumn(COL_KG, format="%.3f"),
        },
    )
    edited = normalize_load_columns(edited)
    st.session_state.load_df = edited
    st.caption(
        f"Колонки как в Excel: **{COL_MASS}**, **{COL_X}**, **{COL_KG}** — для водоизмещения, LCG и KG; "
        "ниже — таблица с **моментами** и строкой **ИТОГО** (как на листе Trim)."
    )
    tbl_excel = trim_table_excel_with_total(
        edited, x_from_midship=x_from_midship, lbp_m=LBP_M
    )
    if not tbl_excel.empty:
        st.markdown("##### Таблица загрузки (как в Excel: моменты и итог)")
        st.dataframe(style_trim_excel(tbl_excel), use_container_width=True, hide_index=True)
    _x_note = (
        "**Xг в таблице — от миделя (+ к носу)**; моменты X и **LCG** в ИТОГО считаются с **приведением к корме** (LBP/2 + Xг)."
        if x_from_midship
        else "**Xг** — от шп. кормы вперёд; моменты и LCG без пересчёта."
    )
    st.caption(
        f"{_x_note} По **ИТОГО** в колонках **Xг** и **KG** — средние **LCG** (от кормы) и **KG**. "
        "Критерии ИМО — по **средней** осадке при дифференте 0 в буклете."
    )
    df = edited.dropna(subset=[COL_MASS])
    masses = df[COL_MASS].astype(float).values
    xgs = df[COL_X].fillna(0).astype(float).values
    kgs = df[COL_KG].astype(float).values
    delta_t = float(np.sum(masses))
    if delta_t <= 0:
        st.error("Сумма масс должна быть > 0.")
        st.stop()
    kg_total = float(np.sum(masses * kgs) / delta_t)
    x_ap = x_g_to_from_ap(xgs, LBP_M, from_midship=x_from_midship)
    lcg_m = float(np.sum(masses * x_ap) / delta_t)
    m_light = m_fuel = m_ballast = m_stores = m_coal = 0.0
    kg_light = kg_fuel = 0.0
    st.caption(
        f"Сумма масс = **{delta_t:,.0f} т**; **LCG** ≈ **{lcg_m:.2f} м** от шп. кормы "
        f"({'после приведения X из миделя' if x_from_midship else 'X уже от кормы'}).".replace(",", " ")
    )

if mode.startswith("По группам"):
    lcg_trim_ap = st.number_input(
        "LCG от шп. кормы для осадок нос/корма (м), 0 — не считать",
        min_value=0.0,
        max_value=200.0,
        value=0.0,
        step=0.1,
        help="Задайте продольный центр тяжести в той же системе, что Xг в таблице (от кормы вперёд). "
        "0 — только средняя осадка, без дифферента.",
        key="lcg_trim_group",
    )
    lcg_for_trim = float(lcg_trim_ap) if lcg_trim_ap > 1e-9 else None
else:
    lcg_for_trim = lcg_m

vcg_m = kg_total
kg0 = kg_total + gg0

if delta_t <= 0:
    st.error("Суммарная масса должна быть больше нуля.")
    st.stop()

t_mean = draft_from_displacement(delta_t)
gm = gm_metacentric(delta_t, kg0, fsc)
kmt = kmt_from_displacement(delta_t)

long_trim = None
if lcg_for_trim is not None:
    long_trim = drafts_fwd_aft_from_lcg(
        delta_t,
        t_mean,
        lcg_for_trim,
        lbp_m=LBP_M,
        beam_m=SHIP["beam_m"],
        lcf_from_ap_m=lcf_ap_m,
    )

m_wo_coal = 0.0
if mode.startswith("По группам"):
    m_wo_coal = m_light + m_fuel + m_ballast + m_stores
else:
    df0 = st.session_state.get("load_df")
    if df0 is not None and len(df0) > 0 and COL_NAME in df0.columns:
        df0 = normalize_load_columns(df0)
        coal_mask = df0[COL_NAME].astype(str).str.contains("Уголь", case=False, na=False)
        m_wo_coal = float(df0.loc[~coal_mask, COL_MASS].fillna(0).sum())

crit, meta = imo749_intact(delta_t, kg0, kg0, fsc, theta_flood)
ok_all = all(c.ok for c in crit)

tab1, tab2, tab3, tab4, tab5 = st.tabs(
    [
        "Сводка и критерии",
        "Диаграмма GZ",
        "Уголь по осадке",
        "Погода и ускорение (Excel)",
        "Груз в трюмах по осадкам",
    ]
)

with tab1:
    st.markdown(
        "**Сводка** показывает текущее состояние загрузки: сколько судно «весит» в воде, на какой **осадке** сидит, "
        "где проходит центр тяжести и каков **GM**. Ниже — пять стандартных **критериев неповреждённого судна** (ИМО A.749, как в буклете): "
        "каждый сравнивает расчётное значение с нормой (например, площадь под кривой GZ между углами или минимальный GZ на 30°)."
    )
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Водоизмещение Δ", f"{delta_t:,.0f} т".replace(",", " "))
    k2.metric("Средняя осадка T", f"{t_mean:.3f} м")
    k3.metric("KG / KG₀", f"{kg_total:.3f} / {kg0:.3f} м")
    k4.metric("GM (с ПВСВ)", f"{gm:.3f} м")
    st.caption(
        f"**KMT** ≈ {kmt:.3f} м — высота **поперечного метацентра** над килем при данном Δ (из гидростатики буклета). "
        "Чем выше **KG**, тем меньше **GM** при той же форме корпуса."
    )
    if long_trim is not None:
        lt = long_trim
        st.subheader("Осадка нос / корма (оценка по LCG)")
        d1, d2, d3, d4 = st.columns(4)
        d1.metric("T нос (передний ОП)", f"{lt.t_fwd_m:.3f} м")
        d2.metric("T корма (задний ОП)", f"{lt.t_aft_m:.3f} м")
        d3.metric("Дифферент", f"{lt.trim_cm:+.1f} см")
        d4.metric("MCTC (оценка)", f"{lt.mctc_t_m_per_cm:.1f} т·м/см")
        if (
            lt.t_fwd_m < 0.05
            or lt.t_aft_m < 0.05
            or lt.t_fwd_m > SHIP["depth_m"]
            or lt.t_aft_m > SHIP["depth_m"]
            or abs(lt.trim_cm) > 300.0
        ):
            st.warning(
                "Осадки нос/корма выходят за разумные пределы (или |дифферент| > 3 м): линейная оценка по LCG "
                "не соответствует реальному балансу — нужна гидростатика с LCB/LCF/MCT из буклета или Trim-расчёт."
            )
        st.caption(
            f"LCG = {lt.lcg_from_ap_m:.2f} м, LCF = {lt.lcf_from_ap_m:.2f} м от кормы; подгоночный момент ≈ {lt.trimming_moment_t_m:,.0f} т·м. "
            "Оценка MCTC по прямоугольной ватерлинии; T_нос/корма при линейном дифференте и LCF на заданной позиции. "
            "**Кривая GZ и критерии ИМО** в буклете — для **равных ватерлиний (дифферент 0)**; расчёт остойчивости выше — по **средней** осадке."
        )
    else:
        st.info(
            "Осадки **нос/корма** не считаются: в режиме «По группам» задайте **LCG от кормы** > 0 или переключитесь на **таблицу загрузки** с колонкой **Xг, м**."
        )

    st.subheader("Критерии остойчивости неповреждённого судна (ИМО A.749 / буклет)")
    st.caption(
        "Зелёная галочка — условие выполнено при ваших данных; красный крест — норма не достигнута "
        "(нужно менять загрузку, KG, угол заливания или сверять исходники с буклетом)."
    )
    for c in crit:
        icon = "✅" if c.ok else "❌"
        st.markdown(f"{icon} **{c.code}.** {c.description} — требуется {c.required}; **факт:** {c.actual}")
    if ok_all:
        st.success("Все пять критериев выполняются (по введённым данным и таблицам буклета).")
    else:
        st.warning("Есть невыполненные критерии — скорректируйте массы, KG или угол заливания.")

with tab2:
    with st.expander("Как читать диаграмму GZ"):
        st.markdown(
            """
По горизонтали — **угол крена φ** (сколько градусов судно наклонено). По вертикали — **GZ** в метрах: это **плечо**, на котором вес судна «давит», чтобы вернуть корпус в вертикаль (это **не** аппликата; **KG** и **KG₀** указаны в заголовке графика).

- Пока кривая **выше нуля**, остойчивость «в плюсе»: после крена есть возвращающий момент.
- **Площадь** под кривой между двумя углами связана с **работой** сил и входит в критерии ИМО (их вы видите на вкладке «Сводка»).
- Формула **GZ = GZ₀ − KG₀·sin φ** значит: чем выше поднят центр тяжести (**KG₀**), тем ниже вся кривая — запас остойчивости меньше.
- На буклете часто рисуют **красную касательную** начальной остойчивости: **GZ ≈ GM·φ** (угол φ в радианах); при **φ = 1 рад (57,3°)** ордината равна **GM** — так проверяют начальную метацентрическую высоту.
- **Зелёная горизонталь** — уровень максимума кривой **GZ_max** (и иногда вертикаль на **φ_max**).
            """
        )
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
            line=dict(width=2, color="#1a5f7a"),
            fill="tozeroy",
            fillcolor="rgba(26,95,122,0.15)",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=phis_tan,
            y=gz_tan,
            mode="lines",
            name=f"Касательная GM·φ (GM={gm:.2f} м)",
            line=dict(width=2, color="#d62728", dash="solid"),
            hovertemplate="φ=%{x:.1f}° · GM·φ_rad = %{y:.3f} м<extra></extra>",
        )
    )
    fig.add_hline(
        y=gz_max,
        line=dict(color="#2ca02c", width=2),
        annotation_text=f"GZ_max ≈ {gz_max:.2f} м",
        annotation_position="right",
        name="GZ_max",
    )
    fig.add_vline(
        x=phi_max_gz,
        line=dict(color="#2ca02c", width=1, dash="dot"),
        annotation_text=f"φ_max ≈ {phi_max_gz:.0f}°",
        annotation_position="top",
    )
    fig.add_hline(y=0, line_dash="dot", line_color="#666")
    for xv, lab in [(15, "15°"), (30, "30°"), (40, "40°")]:
        fig.add_vline(x=xv, line_dash="dot", line_color="#aaa", annotation_text=lab)
    fig.add_vline(
        x=57.3,
        line_dash="dash",
        line_color="rgba(214,39,40,0.6)",
        annotation_text="1 рад",
        annotation_position="top",
    )
    y_pad = max(0.15, float(np.nanmax(gzs_arr) - np.nanmin(gzs_arr)) * 0.08 + 0.05)
    y_min = float(np.nanmin([np.nanmin(gzs_arr), 0.0])) - y_pad
    y_max = max(float(np.nanmax(gzs_arr)), float(np.max(gz_tan))) + y_pad
    fig.update_layout(
        title=dict(
            text=(
                "Диаграмма статической остойчивости GZ(φ)<br>"
                "<span style='font-size:13px;font-weight:normal'>"
                f"Аппликата центра тяжести над килем: <b>KG = {kg_total:.3f} м</b>, "
                f"<b>KG₀ = {kg0:.3f} м</b> (KG + GG₀); вертикальная ось — плечо GZ, м"
                "</span>"
            ),
            x=0.5,
            xanchor="center",
        ),
        xaxis_title="Угол крена φ, °",
        yaxis_title="GZ, м (плечо остойчивости, не аппликата)",
        height=520,
        template="plotly_white",
        hovermode="x unified",
        margin=dict(t=100),
        xaxis=dict(range=[0, 60], dtick=10, zeroline=True),
        yaxis=dict(range=[y_min, y_max], zeroline=True, title_standoff=12),
    )
    st.plotly_chart(fig, use_container_width=True)
    st.caption(
        f"**Красная** — касательная **GM·φ** (φ в радианах), на **57,3°** (1 рад) по вертикали отмечают **GM ≈ {gm:.2f} м** как в буклете. "
        f"**Зелёные** — уровень **GZ_max** и **φ_max**. Рабочая **GZ(φ)** — синяя. "
        f"Формула кривой: GZ = GZ₀ − KG₀·sin φ; KG = {kg_total:.3f} м, KG₀ = {kg0:.3f} м."
    )

with tab3:
    st.markdown(
        "**Масса угля** по осадке: разность водоизмещения по средней осадке и массы всего остального (без угля)."
    )
    with st.expander("Простыми словами: осадка и уголь"):
        st.markdown(
            """
**Средняя осадка** — насколько глубоко корпус погружён (по килю в среднем). Чем глубже, тем **больше водоизмещение** — судно «вытесняет» больше тонн воды = несёт больше груза.

Здесь вы задаёте массу всего **кроме угля** и выбираете желаемую осадку: программа смотрит в таблицу буклета «осадка → водоизмещение» и вычитает «прочее», получая **сколько тонн угля** теоретически вмещается. Таблица внизу — **навигационная ориентировка**, не замена штевенской освидетельствования.
            """
        )
    st.latex(r"M_{\text{уголь}} = \Delta(T) - M_{\text{прочее}}")
    m_fixed = st.number_input(
        "Масса на борту без угля, т",
        value=float(m_wo_coal) if m_wo_coal > 0 else 2500.0,
        step=10.0,
        key="m_fixed_coal",
    )
    t_pick = st.slider("Средняя осадка T, м", 1.2, 4.4, float(round(t_mean, 2)), 0.01)
    d_at_t = displacement_from_draft(t_pick)
    coal_t = coal_mass_from_draft(t_pick, m_fixed)
    st.metric("При выбранной осадке", f"Δ = {d_at_t:,.0f} т; уголь ≈ {coal_t:,.0f} т".replace(",", " "))
    rho_coal = st.number_input("Плотность угля (объём), т/м³", value=0.85, min_value=0.5, max_value=1.2, step=0.05)
    if rho_coal > 0:
        st.caption(f"Ориентировочный объём угля: **{coal_t / rho_coal:,.0f} м³**".replace(",", " "))
    st.subheader("Таблица: осадка → уголь")
    tbl = coal_mass_table(m_fixed, 1.2, 4.4, 0.1)
    st.dataframe(
        [{"T, м": a, "Δ, т": round(b, 1), "Уголь, т": round(c, 1)} for a, b, c in tbl[::2]],
        use_container_width=True,
        hide_index=True,
    )

with tab4:
    st.markdown(
        "Расчёт по структуре листов **weather criteria** и **acceleration criteria** "
        "(рабочие книги Excel). Плечи ветра LW1/LW2, угол качки θ₁ᵣ, площади **A** и **B**, "
        "критерий **K = B/A ≥ 1**; ускорение **К* = 0,3/a_расч** (РМРС 1 ч. IV п. 3.12.3)."
    )
    with st.expander("Погода и ускорение — что означают буквы"):
        st.markdown(
            """
На море судно **кренит ветер** (постоянный наклон) и **качка** (крен туда‑сюда). Расчёт сравнивает **запас энергии** остойчивости с «работой», которую нужно затратить, чтобы перекинуть судно через опасный диапазон углов.

- **LW1, LW2** — расчётные **плечи** силы ветра (в метрах), переведённые к тому же масштабу, что и кривая GZ. Они задают **угол равновесия под ветром** θ₀.
- **θ₁ᵣ** — характерный **угол качки** (по формуле из правил): насколько сильно судно раскачивается при волнении.
- Площадь **A** — «недостаток» энергии в опасном интервале углов; **B** — запас справа. Отношение **K = B/A** должно быть **не меньше 1**: запас больше «долга» по энергии.
- **a_расч** и **К*** — проверка **инерционных ускорений** (РМРС): при сильной качке груз и конструкции испытывают нагрузки; **К* > 1** означает, что по этой упрощённой модели норма ускорения соблюдается.

Цифры могут чуть отличаться от вашего Excel из‑за таблиц GZ и выбора θзал — это нормально для сопоставления, а не для юридического класса без сверки.
            """
        )
    w1, w2, w3 = st.columns(3)
    with w1:
        a_proj = st.number_input("Площадь боковой проекции A, м²", value=663.0, step=10.0, key="a_proj")
        z_w = st.number_input("z (центр A — ~½ осадки), м", value=2.49, step=0.05, key="z_w")
    with w2:
        ak_sk = st.number_input("Площадь килей Ak, м²", value=0.0, step=1.0, key="ak_sk")
        p_wind = st.number_input("Давление ветра P, Па", value=504.0, step=1.0, key="p_wind")
    with w3:
        rho_w = SHIP["rho_sea_t_m3"]
        cb_ship = block_cb_from_nabla(delta_t, LBP_M, SHIP["beam_m"], t_mean, rho_w)

    lw1, lw2 = lw_wind_m(p_wind, a_proj, z_w, delta_t)
    c_rs = rs_inertial_c(LBP_M, SHIP["beam_m"], t_mean)
    t_roll = 2.0 * c_rs * SHIP["beam_m"] / max(gm, 1e-6) ** 0.5
    theta1r = theta1_roll_deg(
        beam_m=SHIP["beam_m"],
        draft_m=t_mean,
        lbp_m=LBP_M,
        cb=cb_ship,
        gm_m=max(gm, 1e-6),
        ak_m2=ak_sk,
        kg_m=kg0,
    )
    bd = SHIP["beam_m"] / max(t_mean, 0.01)
    k_theta = rs_k_theta_bd(bd)
    a_calc = rs_acceleration_a_calc(k_theta, c_rs, theta1r)
    k_star = rs_acceleration_k_star(a_calc)
    wx = weather_energy_areas(delta_t, kg0, lw1, lw2, theta1r, theta_flood)

    st.markdown("### Ветер и качка")
    st.caption(
        "Ветер давит на боковую проекцию судна и создаёт крен; период качки зависит от ширины, осадки и GM. "
        "Ниже — промежуточные величины для погодного критерия и ускорения."
    )
    st.write(
        f"**Cb** ≈ {cb_ship:.3f} · **C** (инерц.) = {c_rs:.3f} · **T** (качка) ≈ {t_roll:.2f} с · "
        f"**B/d** = {bd:.2f} · **kθ** = {k_theta:.3f}"
    )
    st.write(
        f"**LW1** = {lw1:.4f} м · **LW2** = {lw2:.4f} м · **θ₁ᵣ** = {theta1r:.2f}° "
        "(по формуле буклета/ИМО, как на листе «weather criteria»)."
    )

    st.markdown("### Погодный критерий (энергии)")
    st.caption(
        "Смысл: **A** характеризует «трудный» участок диаграммы GZ, **B** — запас после него; **B/A ≥ 1** значит, что запас энергии достаточен."
    )
    st.write(
        f"**θ₀** (равновесие GZ = LW1) ≈ **{wx.theta0_deg:.2f}°** · "
        f"**θ₂** (предел интеграла) ≈ **{wx.theta2_deg:.2f}°**"
    )
    st.write(
        f"Площадь **A** ≈ **{wx.area_a_m_rad:.3f}** м·рад · Площадь **B** ≈ **{wx.area_b_m_rad:.3f}** м·рад · "
        f"**B/A** = **{wx.ratio_b_over_a:.3f}** (норма **≥ 1**)"
    )
    if wx.ratio_b_over_a >= 1.0:
        st.success("Критерий K = B/A выполняется (по упрощённой схеме интегрирования).")
    else:
        st.warning("K = B/A < 1 — по этой модели погодный критерий не выполняется.")

    st.markdown("### Критерий ускорения (РМРС 3.12.3)")
    st.caption(
        "Сравнивают расчётное горизонтальное ускорение (доли g) с допустимым; **К*** — безразмерный запас: чем больше 1, тем лучше по этой проверке."
    )
    st.write(
        f"**a_расч** ≈ kθ·C·θ₁ᵣ(rad) = **{a_calc:.4f}** (доли g) · **К*** = 0,3/a_расч = **{k_star:.2f}** (норма **> 1**)"
    )
    if k_star > 1.0:
        st.success("Критерий ускорения выполняется (К* > 1).")
    else:
        st.info("Критерий ускорения не выполняется или на грани — сверьте с Excel.")

    st.caption(
        "Числа могут отличаться от Excel из‑за другой таблицы KN/GZ₀ и угла заливания; "
        "для совпадения подгоните A, z, θзал и GG₀."
    )

with tab5:
    st.markdown(
        "### Груз в трюмах по измеренным осадкам и массам на борту  \n"
        "Введите **осадки носа и кормы**, **топливо** (танки и расходные цистерны), **пресную воду**, "
        "**балласт** и массу **всего остального** (порожний корпус, снабжение — всё, что **не** относится к грузу в трюмах). "
        "Расчёт: **водоизмещение** по таблице буклета от **средней** осадки минус сумма введённых масс (без трюмного груза) = **оценка массы груза в трюмах**."
    )
    with st.expander("Как это считается и ограничения"):
        st.markdown(
            f"""
- **T_ср** = (T_нос + T_корма) / 2 → по гидростатике буклета находится **Δ** (т).
- **M_груз_трюмы** = Δ − M_топл_танки − M_топл_расход − M_пресн − M_балл_лб − M_балл_прб − M_прочее.
- Таблица **KN/GZ** в буклете дана для **дифферента 0**; при большом дифференте оценка по одной средней осадке **приближённая** (как в навигационных расчётах).
- Глубина судна (маркировка): **{SHIP["depth_m"]}** м — не превышайте осадку без сверки с допуском.
            """
        )

    c_a, c_b = st.columns(2)
    with c_a:
        st.subheader("Осадки")
        t_fwd = st.number_input(
            "Осадка носом T_нос, м",
            min_value=0.5,
            max_value=float(SHIP["depth_m"]) + 0.5,
            value=3.5,
            step=0.01,
            format="%.2f",
            key="holds_t_fwd",
        )
        t_aft = st.number_input(
            "Осадка кормой T_корма, м",
            min_value=0.5,
            max_value=float(SHIP["depth_m"]) + 0.5,
            value=3.5,
            step=0.01,
            format="%.2f",
            key="holds_t_aft",
        )
    with c_b:
        st.subheader("Жидкости и балласт, т")
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
        m_fw = st.number_input(
            "Пресная вода в танках, т",
            min_value=0.0,
            value=0.0,
            step=0.5,
            key="holds_fw",
        )
        m_ball_ps = st.number_input(
            "Балласт левый борт, т",
            min_value=0.0,
            value=0.0,
            step=1.0,
            key="holds_ball_ps",
        )
        m_ball_sb = st.number_input(
            "Балласт правый борт, т",
            min_value=0.0,
            value=0.0,
            step=1.0,
            key="holds_ball_sb",
        )

    m_other = st.number_input(
        "Прочее (порожний корпус, снабжение, экипаж, запасные части — всё без груза в трюмах), т",
        min_value=0.0,
        value=2225.0,
        step=10.0,
        help="По умолчанию ориентир 2210 + 15 т (корпус + снабжение); подставьте свои фактические массы.",
        key="holds_m_other",
    )

    m_wo_hold = (
        float(m_fuel_tanks)
        + float(m_fuel_svc)
        + float(m_fw)
        + float(m_ball_ps)
        + float(m_ball_sb)
        + float(m_other)
    )
    delta_holds, t_mean_holds, cargo_holds = cargo_mass_from_drafts(t_fwd, t_aft, m_wo_hold)
    trim_m = float(t_aft) - float(t_fwd)
    trim_cm = trim_m * 100.0

    st.divider()
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Средняя осадка T_ср", f"{t_mean_holds:.3f} м")
    m2.metric("Дифферент (корма − нос)", f"{trim_cm:+.1f} см")
    m3.metric("Водоизмещение Δ (по буклету)", f"{delta_holds:,.0f} т".replace(",", " "))
    m4.metric("Оценка груза в трюмах", f"{cargo_holds:,.0f} т".replace(",", " "))

    if cargo_holds <= 0:
        st.warning(
            "Масса «прочего» и жидкостей **не меньше** водоизмещения по осадке — "
            "проверьте осадки и введённые массы (или уточните «Прочее»)."
        )
    else:
        st.success(
            f"При заданных данных масса **погруженного груза в трюмах** (уголь и т.п.) оценивается как **{cargo_holds:,.1f} т**.".replace(
                ",", " "
            )
        )

    st.caption(
        f"Сумма масс без трюмного груза: **{m_wo_hold:,.1f} т** "
        f"(топливо {m_fuel_tanks + m_fuel_svc:.1f} + пресная {m_fw:.1f} + балласт {m_ball_ps + m_ball_sb:.1f} + прочее {m_other:.1f}).".replace(
            ",", " "
        )
    )
