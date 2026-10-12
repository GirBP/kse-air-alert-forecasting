# Відтворення актуального експерименту

Python 3.10+ і системна IANA Europe/Kyiv; перевірене ізольоване середовище — CPython 3.14.7. Вхід завантажується один раз із зафіксованого GitHub-коміту; API-токен не потрібен. Обчислення, демо, тести й незалежний verifier використовують лише стандартну бібліотеку. requirements-latest.txt фіксує це. Для documented PYTHONPATH запусків pip install не потрібен. На системі без Europe/Kyiv спочатку встановіть базу IANA; не призначайте довільний UTC-зсув.

З чистої копії репозиторію:

```sh
python3 -m venv .venv
.venv/bin/python scripts/fetch_latest_input.py --project-root .
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m unittest discover -s tests_latest -v
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m kse_latest evaluate --project-root .
.venv/bin/python scripts/verify_implementation_v2.py --project-root .
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m kse_latest demo --project-root . --show-actual
```

Fetch перевіряє SHA-256 і не замінює існуючий інший вхід. Він читає pinned URL із protocol/latest-v1.json, а не рухому main-гілку. Провенанс першого повторного отримання — provenance/retrieval-log.json; нова локальна квитанція download — data/latest/inputs/retrieval-receipt.json. Відмова upstream у доступі є явною помилкою, не приводом змінити джерело або вхід мовчки.

Evaluate перевіряє протокол/SHA входу та незмінність оригінального frozen duration.py; хеші нового versioned forecast/evaluation записує окремо у summary. Змінювати method/window/відбір після тесту не можна. За однакових входів і коду CSV/JSON повторюються побайтово, без нових моделей чи підбору. `--output-dir work/repeated-latest` дозволяє окремий повтор; каталоги старих даних і експериментів захищено.

Результати: data/latest/implementation-v2/metrics.csv, evaluation-predictions.csv, all-forecasts.csv, exclusions.csv, exclusion-counts.csv, largest-errors.csv, summary.json, demo-example.json, checksums.json. Повні event-level входи й виходи залишаються локальними та gitignored. Вони відтворюються після отримання pinned input. У GitHub є звіт з агрегатами, джерелами й великими прикладами.

В оригінальному повному проєкті додатково перевірте всі попередні файли:

```sh
python3 scripts/verify_implementation_v2.py --project-root . --verify-previous
```

У чистому GitHub clone старих приватних архівів немає, тому прапорець --verify-previous там не потрібен. Збережений звіт повної перевірки містить фактичні 219 файлів; стандартний verifier клону не видає це за повторний аудит відсутніх оригіналів.

Демо відбирає тільки вересневі події. Без --show-actual воно показує прогноз та число історії; з прапорцем додає факт окремим блоком. Це історичне відтворення, не live API й не доведена тогочасна публікація.

## Виправлена реалізація після ML-аудиту

Default evaluate пише у data/latest/implementation-v2/, попереднє data/latest/results/ не перезаписує. Оригінальні frozen protocols та duration.py збережено; у CLI є evaluate-frozen-v1, який за замовчуванням пише у work/frozen-v1-replay/. Новий predict --start потребує лише початку та supplied history; поточний відбій не передається. Тип прогнозу — повна тривалість при новому початку. API не надає автоматичного live збору чи доведеної історичної publication availability.

```sh
mkdir -p work
PYTHONPATH=src python3 -m kse_latest predict --project-root . --start 2026-10-01T02:50:41.688+03:00 > work/example-prediction.json
python3 scripts/verify_implementation_v2.py --project-root . --verify-previous
python3 scripts/replay_historical_selection.py --project-root .
python3 scripts/ml_diagnostics.py --project-root . --no-plots
```

--verify-previous тільки для повного початкового проєкту з 207 retained files, не для clean clone. Незалежний checker порівнює original files тільки якщо вони наявні; у clean clone він не видає це за аудит відсутніх старих raw. Historical replay завантажує pinned official CSV при його відсутності; параметри 20 CV fits і selected model уже frozen, нове навчання/пошук не виконуються.

За відсутності Matplotlib --no-plots відтворює CSV/JSON. Для трьох PNG: окремо встановіть requirements-ml-audit.txt та запустіть ml_diagnostics без --no-plots. Diagnostic historical/private-artifact audit виконується лише де збережені old artifacts; у public clone доступні агреговані докази плюс raw replay selected/CV parameters. Це post-evaluation; жоден запуск не робить October знову untouched test.
