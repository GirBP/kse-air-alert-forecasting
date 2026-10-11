# Відтворення актуального експерименту

Python 3.10+ і системна IANA Europe/Kyiv; перевірене ізольоване середовище — CPython 3.14.7. Вхід завантажується один раз із зафіксованого GitHub-коміту; API-токен не потрібен. Обчислення, демо, тести й незалежний verifier використовують лише стандартну бібліотеку. requirements-latest.txt фіксує це. Для documented PYTHONPATH запусків pip install не потрібен. На системі без Europe/Kyiv спочатку встановіть базу IANA; не призначайте довільний UTC-зсув.

З чистої копії репозиторію:

```sh
python3 -m venv .venv
.venv/bin/python scripts/fetch_latest_input.py --project-root .
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m unittest discover -s tests_latest -v
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m kse_latest evaluate --project-root .
.venv/bin/python scripts/verify_latest.py --project-root .
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m kse_latest demo --project-root . --show-actual
```

Fetch перевіряє SHA-256 і не замінює існуючий інший вхід. Він читає pinned URL із protocol/latest-v1.json, а не рухому main-гілку. Провенанс першого повторного отримання — provenance/retrieval-log.json; нова локальна квитанція download — data/latest/inputs/retrieval-receipt.json. Відмова upstream у доступі є явною помилкою, не приводом змінити джерело або вхід мовчки.

Evaluate перевіряє протокол, SHA входу й хеш прогнозного коду проти першого відкриття. Змінювати method/window/відбір після тесту не можна. За однакових входів і коду CSV/JSON повторюються побайтово, без нових моделей чи підбору. `--output-dir work/repeated-latest` дозволяє окремий повтор; каталоги старих даних і експериментів захищено.

Результати: data/latest/results/metrics.csv, evaluation-predictions.csv, all-forecasts.csv, exclusions.csv, exclusion-counts.csv, largest-errors.csv, summary.json, demo-example.json, checksums.json. Повні event-level входи й виходи залишаються локальними та gitignored. Вони відтворюються після отримання pinned input. У GitHub є звіт з агрегатами, джерелами й великими прикладами.

В оригінальному повному проєкті додатково перевірте всі попередні файли:

```sh
python3 scripts/verify_latest.py --project-root . --verify-previous
```

У чистому GitHub clone старих приватних архівів немає, тому прапорець --verify-previous там не потрібен. Збережений звіт повної перевірки містить фактичні 219 файлів; стандартний verifier клону не видає це за повторний аудит відсутніх оригіналів.

Демо відбирає тільки вересневі події. Без --show-actual воно показує прогноз та число історії; з прапорцем додає факт окремим блоком. Це історичне відтворення, не live API й не доведена тогочасна публікація.
