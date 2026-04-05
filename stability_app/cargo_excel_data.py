"""
Строки таблицы загрузки «В грузу» из рабочей книги Excel (Stability General / Trim).
Единственный источник для пресета и тестов; при обновлении Excel — править здесь.
"""

from __future__ import annotations

from excel_ui import COL_KG, COL_MASS, COL_NAME, COL_X

# Снимок с листа «В грузу»: наименование, масса, Xг (как в Excel — обычно от миделя, + к носу), KG над килем.
# В приложении по умолчанию включено «X от миделя»; тогда LCG и дифферент считаются с приведением к корме.
ROWS_CARGO_IN_GRUZ: list[dict[str, str | float]] = [
    {COL_NAME: "Судно порожнее", COL_MASS: 2210.0, COL_X: 4.133, COL_KG: 4.58},
    {COL_NAME: "Судовое снабжение", COL_MASS: 15.0, COL_X: -46.0, COL_KG: 7.2},
    {COL_NAME: "Топливо", COL_MASS: 6.0, COL_X: -46.0, COL_KG: 1.2},
    {COL_NAME: "Уголь", COL_MASS: 6500.0, COL_X: 0.5, COL_KG: 6.1},
    {COL_NAME: "Балласт ПР/Б", COL_MASS: 69.0, COL_X: -37.8, COL_KG: 1.15},
    {COL_NAME: "Балласт Л/Б", COL_MASS: 67.0, COL_X: -37.8, COL_KG: 1.15},
]

# Пресет «В грузу (из Excel)» на вкладке остойчивости — поля session_state / stab_*.
# Соответствие ROWS_CARGO_IN_GRUZ:
#   • Судовое снабжение → stab_m/x/kg_stores (X, KG как в Excel, от миделя).
#   • Топливо 6 т → расходные цистерны (не FUEL-PTS/STB разд. 6): те же X/KG, что строка «Топливо».
#   • Уголь → stab_m/x/kg_coal.
#   • Балласт Л/Б 67 т → BW-02 PTS-AFT.P (танк 7); Балласт ПР/Б 69 т → BW-02 STB-AFT.S (танк 8).
#     В расчёте LCG/KG жидкости берутся из буклета (разд. 6), не из -37.8 Excel.
# Порожнее судно в приложении — из ship_data (буклет), не из строки Excel 2210 т.
PRESET_V2_GRUZ: dict[str, float] = {
    "stab_m_stores": 15.0,
    "stab_x_stores": -46.0,
    "stab_kg_stores": 7.2,
    "stab_m_fuel_svc": 6.0,
    "stab_x_fuel_svc": -46.0,
    "stab_kg_fuel_svc": 1.2,
    "stab_t0": 0.0,
    "stab_t1": 0.0,
    "stab_t2": 0.0,
    "stab_t3": 0.0,
    "stab_t4": 0.0,
    "stab_t5": 0.0,
    "stab_t6": 0.0,
    "stab_t7": 67.0,
    "stab_t8": 69.0,
    "stab_m_coal": 6500.0,
    "stab_x_coal": 0.5,
    "stab_kg_coal": 6.1,
}
