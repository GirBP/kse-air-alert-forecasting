# KSE: ретроспективний прогноз повної тривалості тривоги Києва

Робочий Python-проєкт для нерегулярного часового ряду зареєстрованих закритих міських повітряних тривог. Ціль — **повна тривалість у хвилинах при зареєстрованому початку**. Залишкова тривалість під час активної тривоги, початок наступної тривоги, добове навантаження та кількість ракет — інші задачі.

Можлива практична гіпотеза: координатор групи планує перенесення заняття/зустрічі після оголошення. Цього користувача й рішення не перевірено; тривалість тривоги не вимірює фактичного переривання роботи. Ціна завищення й заниження невідома. MAE збережено як дослідницьку метрику симетричної абсолютної втрати, не як погоджений бізнес-критерій. [Методологія](docs/methodology.md).

Єдиний зафіксований метод — **медіана останніх 30 фактично завершених подій** цього джерела. Нових моделей, ознак, вікон чи налаштувань не шукали.

## Що показує експеримент

Окреме дзеркало alerts.in.ua, UID31 (м. Київ; API location_type=oblast), commit 7abc556ba5a0ff47a9e33c6abc136b8da3a9feb8. Повторне отримання/порівняння відомих джерел виконано 12.10.2026 до цього аудиту; це історично зафіксована перевірка актуальності, не live feed. [Походження](provenance/source-checks.json), [URL/час/SHA](provenance/retrieval-log.json).

Вересень: 156 подій власної історії, 30 первинних warmup. October evaluation: [01.10.2026 00:00, 11.10.2026 13:07:59), **Europe/Kyiv**. Останній відбій 11.10.2026 13:01:52. Край 11 жовтня неповний; відсутні записи/дні не zero-filled, повнота спостереження не доведена. У наявних 240 UID31 рядках 0 duplicates/conflicts/overlaps/open events; це не доказ відсутності пропущених/відкритих подій у джерелі.

| Метод | n | MAE, хв | RMSE, хв | Медіана AE | p90 AE |
|---|---:|---:|---:|---:|---:|
| Зафіксований rolling median 30 | 84 | 40.894 | 62.620 | 24.008 | 76.708 |

Виключень у жовтні 0. В межах ±15/±30/±60 хв — **25.0% / 54.8% / 85.7%**. 11/84 подій недооцінено >60 хв, середній shortfall цих випадків 139.265 хв. Сім подій >=120 хв дають 70.6% SSE; усі залишені. Найбільша AE 248.829 хв. Прийнятний поріг помилки не погоджено; користь планування не виміряна.

**Жовтень уже відкритий.** Додатковий audit comparison на тих самих 84 дає historical median MAE 37.826, last completed 53.408. Це post-evaluation діагностика, не новий blind test або підстава змінити final method. Rolling30 не доведено універсально кращим. Стара regression перевага була малою/непереконливою; це не доказ рівноцінності моделей. [Незалежний ML-аудит](docs/ml-audit.md), [таблиці та 3 графіки](reports/ml-diagnostics/README.md).

Історичний event-clock порядок підтверджено; **оперативна доступність саме тих версій рядків не доведена**. CSV не має updated_at/received_at; archive file history має коміти тільки 06–11 жовтня. Closed-only selection і правий край звужують оцінювану популяцію. Новий офіційний [ресурс Києва](https://data.kyivcity.gov.ua/dataset/statystyka-povitrianykh-tryvoh-u-misti-kyievi-dep-municipal/resource/cbf3758e-031c-42b0-a477-e731cd79b261) перевірено раніше, але його naive state timestamps не мають підтвердженої зони/парування; джерела не зливаються.

## Запуск

Python 3.10+ і IANA Europe/Kyiv; перевірено CPython 3.14.7, stdlib без pip-залежностей для forecast/evaluation/verification/tests. Matplotlib потрібен тільки для графіків аудиту. Мережа потрібна для pinned input один раз.

```sh
git clone https://github.com/GirBP/kse-air-alert-forecasting.git
cd kse-air-alert-forecasting
python3 -m venv .venv
.venv/bin/python scripts/fetch_latest_input.py --project-root .
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m unittest discover -s tests_latest -v
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m kse_latest evaluate --project-root .
.venv/bin/python scripts/verify_implementation_v2.py --project-root .
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m kse_latest demo --project-root . --show-actual
```

Default evaluation — **implementation v2**, результат у data/latest/implementation-v2/. Старий duration.py, protocol/lock/opening і data/latest/results/ збережені. Виправлено latent unordered-state leak, empty outputs/demo й input errors, додано target-free API. На 84 старих прикладах всі числа незмінні; сім lineage/numerical files побайтово однакові. [Перевірка](reports/ml-diagnostics/implementation-verification.json). Це перевірка виправлення, не новий незалежний тест. Frozen replay: `PYTHONPATH=src python3 -m kse_latest evaluate-frozen-v1 --project-root . --output-dir work/frozen-v1-replay`.

Новий begin можна передати без майбутнього відбою:

```sh
PYTHONPATH=src .venv/bin/python -m kse_latest predict --project-root . --start 2026-10-01T02:50:41.688+03:00
```

Це приклад історичного start; для нового start передайте його час та власну актуальну same-source history через --input. API використовує only prior completed records, повертає null/status при <30, код/input SHA та last30 IDs/clears/durations. В output є actual computed_at_utc і flag origin_after_pinned_snapshot: застарілий знімок не доводить повноти history до нового start. Знімок не є live source; optional available_at_utc clocks лише дотримуються, їхню достовірність не створює сам код. Прогнозні інтервали **відсутні**; forecast не є сигналом відбою чи перевіреною рекомендацією з безпеки.

[Повні інструкції](docs/latest-reproduce.md). Відтворення старого вибору з pinned Vadimkin CSV і збережених coefficients, без refit/search: `python3 scripts/replay_historical_selection.py --project-root .`. Це опціональна історична перевірка, не навчання нової моделі.

## Подання

[Матриця KSE](docs/kse-requirements.md), [ML criterion matrix](docs/ml-audit.md), [reflection 100 English words](reflection.txt). Реальні Codex texts підготовлено приватно through explicit cutoff; **повний AI-log ще потребує зовнішніх ChatGPT/Gemini/Antigravity експортів** та завершення поточного active-chat export. Decision logs їх не замінюють. Попередній timed closing exporter завершився timeout; closing text не вигадували.

Код/авторська документація MIT. Whole raw та event-level outputs gitignored: redistribution licence mirror CSV не встановлено; pinned download URL/SHA доступні. Збережено старі v1/v2/Vadimkin final і всі попередні inputs/protocols. Перші daily-load та broad collection напрями незавершені окремо. Комплексні моделі, всі регіони, media features та industrial deployment не є обов’язковими вимогами наведеного KSE завдання.
