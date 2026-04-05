# Документация проекта «Остойчивость» (РЕЙД-8)

Набор текстовых материалов для изучения судна и расчётов **без просмотра каждого растрового изображения** в корне репозитория. Содержание согласовано с кодом (`stability_app/`), встроенными таблицами (`_embedded.json`) и снимком Excel (`cargo_excel_data.py`).

## Порядок чтения

| № | Файл | Содержание |
|---|------|------------|
| 00 | [00-obzor.md](00-obzor.md) | Краткий обзор: что за судно, что считает приложение, откуда данные |
| 01 | [01-sudno-i-razmernosti.md](01-sudno-i-razmernosti.md) | Главные размерности, порожнее, тип судна, ссылка на буклет |
| 02 | [02-gidrostatika-i-krivye-gz.md](02-gidrostatika-i-krivye-gz.md) | Гидростатика, KB, KMT, таблица GZ₀, формула GZ(φ) |
| 03 | [03-cisterny-buklet-razdel-6.md](03-cisterny-buklet-razdel-6.md) | Цистерны буклета: LCG, KG, ориентиры масс |
| 04 | [04-kriterii-imo-a749.md](04-kriterii-imo-a749.md) | Критерии неповреждённого судна (ИМО A.749) в приложении |
| 05 | [05-excel-trim-i-presety.md](05-excel-trim-i-presety.md) | Таблица «В грузу», пресеты, согласование с полями формы |
| 06 | [06-prilozhenie-i-moduli.md](06-prilozhenie-i-moduli.md) | Streamlit-приложение, вкладки, сохранение расчёта |
| 07 | [07-fajly-v-korne-repo.md](07-fajly-v-korne-repo.md) | PDF, XLS, WEBP: что это и зачем смотреть оригиналы |
| 08 | [08-zamery-presnoj-vody.md](08-zamery-presnoj-vody.md) | Замеры пресной воды (мм) → тонны, файл `sounding_fresh.json` |
| 09 | [09-ghs-i-snimki-kalibracii.md](09-ghs-i-snimki-kalibracii.md) | Снимки GHS и РД.3036/3035: книга калибровок KIMTRANS, указатель `*.webp`, расчёты с обледенением |
| 10 | [10-chertezhi-ga-i-rina.md](10-chertezhi-ga-i-rina.md) | Новые PDF в корне: General Arrangement (ASL), план пожарной безопасности RINA для РЕЙД-8 |

**Полные численные таблицы** (все строки гидростатики и GZ) хранятся в `stability_app/_embedded.json` и в PDF буклета; в markdown приведены смысл и диапазоны, без дублирования каждой ячейки.

## Обновление документации

При изменении буклета, Excel или логики расчёта — править соответствующий раздел здесь и комментарии в `ship_data.py`, `cargo_excel_data.py`, `tank_booklet.py`.
