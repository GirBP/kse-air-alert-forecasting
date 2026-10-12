# KSE: ретроспективний прогноз тривалості зареєстрованих інтервалів тривог Києва

Робочий Python-проєкт для нерегулярного часового ряду закритих інтервалів тривог Києва, зареєстрованих джерелом. Ціль основного методу — **повна тривалість інтервалу у хвилинах при зареєстрованому початку**. Кінець такого інтервалу не підтверджено як остаточний офіційний відбій. Залишкова тривалість під час активної тривоги досліджувалася окремо; прогноз початку наступної тривоги, добового навантаження та кількості ракет не входить до цього релізу.

Можлива практична гіпотеза: координатор групи планує перенесення заняття/зустрічі після оголошення. Цього користувача й рішення не перевірено; тривалість тривоги не вимірює фактичного переривання роботи. Ціна завищення й заниження невідома. MAE збережено як дослідницьку метрику симетричної абсолютної втрати, не як погоджений бізнес-критерій. [Методологія](docs/methodology.md).

Основний відтворюваний метод релізу — **медіана останніх 30 подій цього джерела, зареєстроване завершення яких відбулося не пізніше моменту прогнозу**. Метод збережено після відкриття основного оцінюваного періоду. Окремі локальні дослідження v3/v4 охопили інші вікна, календарні ознаки, складніші моделі, перенесення навчання та міжрегіональний контекст. Їх не слід плутати з основним маршрутом запуску чи незалежним підтвердженням переваги нової моделі. Стійкої переваги просторових моделей і перенесення навчання аудит не встановив; це не доводить відсутності корисного сигналу взагалі.

[Історична демонстрація на GitHub Pages](https://girbp.github.io/kse-air-alert-forecasting/) · [Сценарій і походження](docs/pages-demo.md). Сайт містить київський калькулятор дати/часу початку на справжній pinned історії, явно синтетичні UX-приклади та справжні агрегати. Час завжди Europe/Kyiv. Після межі знімка звичайний прогноз недоступний; є лише позначений історичний орієнтир. Це не live-сервіс.

## Що показує експеримент

Основний зафіксований експеримент використовує дзеркало alerts.in.ua, UID31 (м. Київ; API location_type=oblast), commit 7abc556ba5a0ff47a9e33c6abc136b8da3a9feb8. Наведені нижче 84 події належать саме до цього знімка. [Походження](provenance/source-checks.json), [URL/час/SHA](provenance/retrieval-log.json). Перевірка джерела має власну часову межу; вона не є live feed або гарантією відсутності пізніших записів. Нові знімки й додаткову діагностику потрібно подавати окремо, з власними версією, періодом та кількістю подій.

Вересень: 156 подій власної історії, 30 первинних warmup. October evaluation: [01.10.2026 00:00, 11.10.2026 13:07:59), **Europe/Kyiv**. Останній відбій 11.10.2026 13:01:52. Край 11 жовтня неповний; відсутні записи/дні не zero-filled, повнота спостереження не доведена. У наявних 240 UID31 рядках 0 duplicates/conflicts/overlaps/open events; це не доказ відсутності пропущених/відкритих подій у джерелі.

| Метод | n | MAE, хв | RMSE, хв | Медіана AE | p90 AE |
|---|---:|---:|---:|---:|---:|
| Зафіксований rolling median 30 | 84 | 40.894 | 62.620 | 24.008 | 76.708 |

**Окрема актуальна діагностика latest91:** знімок `c5b3bd012c7694e63115999a7bbd0b683eaa8d24` до 12.10.2026 10:51:36 UTC; отримано 17:19:36 UTC, актуальність цього шляху перевірено 18:28:38 UTC. 91 закрита жовтнева подія: MAE **40.869**, RMSE **61.640**, медіана AE **24.272**, p90 **80.352** хв; 12 занижень >60 хв. Додано 7 подій. Це діагностика відкритого періоду, не новий незалежний тест і не заміна primary84. [URL, SHA та докази](reports/latest91/source-and-results.json), [відтворення](docs/pages-demo.md#актуальна-діагностика-latest91).

Виключень у жовтні primary84 0. В межах ±15/±30/±60 хв — **25.0% / 54.8% / 85.7%**. 11/84 подій недооцінено >60 хв, середній shortfall цих випадків 139.265 хв. Сім подій >=120 хв дають 70.6% SSE; усі залишені. Найбільша AE 248.829 хв. Прийнятний поріг помилки не погоджено; користь планування не виміряна.

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

Default evaluation — **implementation v2**, результат у data/latest/implementation-v2/. Старий duration.py, protocol/lock/opening і data/latest/results/ збережені. Виправлено latent unordered-state leak, empty outputs/demo й input errors, додано target-free API. На 84 старих прикладах всі числа незмінні; сім lineage/numerical files побайтово однакові. [Перевірка](reports/ml-diagnostics/implementation-verification.json), [чистий Git clone із stdlib venv](reports/ml-diagnostics/clean-copy-verification.json). Це перевірка виправлення, не новий незалежний тест. Frozen replay: `PYTHONPATH=src python3 -m kse_latest evaluate-frozen-v1 --project-root . --output-dir work/frozen-v1-replay`.

Новий begin можна передати без майбутнього відбою:

```sh
PYTHONPATH=src .venv/bin/python -m kse_latest predict --project-root . --start 2026-10-01T02:50:41.688+03:00
```

Це приклад історичного start; для нового start передайте його час та власну актуальну same-source history через --input. API використовує only prior completed records, повертає null/status при <30, код/input SHA та last30 IDs/clears/durations. В output є actual computed_at_utc і flag origin_after_pinned_snapshot: застарілий знімок не доводить повноти history до нового start. Знімок не є live source; optional available_at_utc clocks лише дотримуються, їхню достовірність не створює сам код. Прогнозні інтервали **відсутні**; forecast не є сигналом відбою чи перевіреною рекомендацією з безпеки.

[Повні інструкції](docs/latest-reproduce.md). Відтворення старого вибору з pinned Vadimkin CSV і збережених coefficients, без refit/search: `python3 scripts/replay_historical_selection.py --project-root .`. Це опціональна історична перевірка, не навчання нової моделі.

## Подання

[Матриця KSE](docs/kse-requirements.md), [ML criterion matrix](docs/ml-audit.md), [reflection 100 English words](reflection.txt). Справжні тексти Codex готуються окремим приватним пакетом із реєстром джерел, хешами та часовими межами експорту. Обраний користувачем склад пакета: **виконавець, незалежний аудитор і Gemini**; чат організатора виключено. Підготовлено прямі експорти двох Codex-чатів із заключними відповідями; зовнішній Gemini/Antigravity-експорт ще потрібен. Точний стан визначає маніфест приватного пакета. Журнали рішень і короткі перекази не замінюють повних розмов; заключні повідомлення не реконструюються.

Код/авторська документація MIT. Whole raw та event-level outputs gitignored: redistribution licence mirror CSV не встановлено; pinned download URL/SHA доступні. Збережено старі v1/v2/Vadimkin final і всі попередні inputs/protocols. Перші daily-load та broad collection напрями незавершені окремо. Комплексні моделі, всі регіони, media features та industrial deployment не є обов’язковими вимогами наведеного KSE завдання.
