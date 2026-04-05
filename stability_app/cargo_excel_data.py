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
