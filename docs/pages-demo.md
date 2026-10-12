# GitHub Pages: історична демонстрація

Основний Python-маршрут — `kse_latest` implementation-v2, медіана останніх 30 завершених зареєстрованих інтервалів Києва. Науковий метод, frozen protocol, джерело primary84 і попередні числові результати незмінні. Сайт — статичний додатковий артефакт у `web/`, без сервера прогнозування, live feed, T1, ймовірностей чи рекомендацій виходу з укриття. Версія pages-v1.1 додала локальний браузерний розрахунок manual START на справжній pinned історії; Python-ядро незмінне.

URL релізу: https://girbp.github.io/kse-air-alert-forecasting/. Фактичне розгортання й незалежне приймання прив'язуються до точного commit у приватному release handoff; посилання саме по собі не підтверджує deployment. Кінець зареєстрованого інтервалу не доведено як остаточний офіційний відбій.

## Інтерактивний калькулятор на справжній історії

Форма приймає тільки Київ UID31, дату і час Europe/Kyiv. Інші міста недоступні: київська історія для них не використовується. Браузер анонімно отримує pinned latest91 CSV безпосередньо з upstream; CORS `Access-Control-Allow-Origin: *`, фактичне завантаження й Web Crypto SHA-256 перевірено в браузері. На Pages не зберігається чужий CSV, API-ключів немає. Введені дата/час залишаються в браузері й не входять до URL/тіла запиту upstream. Помилка мережі/CORS, checksum/schema або конфлікту даних дає недоступність, без synthetic fallback. Справжня історія ніколи не береться з трьох UX-прикладів.

`forecast-core.mjs` переносить контракт `predict_at_start`: UID/type/identity, відкриті події, доступні версії/corrections, exact duplicates, overlap errors; порядок clear UTC потім numeric ID, мінімум30, current/future clear не входить. `calculator.mjs` відокремлює завантаження та UI. Формат source timestamps має явний UTC; субмілісекундні ненульові мітки браузер відхиляє, а не мовчки округлює. У pinned джерелі такої втрати точності немає.

Історичний origin до exclusive snapshot boundary отримує повну оцінку при початку. Справжнє існування/активність введеної події не перевіряється. Origin на/після межі знімка **не має звичайного прогнозу**: показується лише окремий історичний орієнтир за даними до межі, з поясненням невідомих пізніших завершень. Новий browser receipt не є новою версією файла: UI окремо показує receipt, commit/hash, snapshot boundary, останній registered CLEAR і247 source rows. На межі знімка прогнозований орієнтир приблизно54 хв; він не є прогнозом поточної події.

Дата/час перетворюється explicit Intl Europe/Kyiv і UTC arithmetic, не локальною зоною браузера. DST gap29.03.2026 03:30 і fold25.10.2026 03:30 відхиляються без вгадування; порожні/невалідні/future inputs також. Код не рахує залишок шляхом віднімання elapsed: перевищена початкова оцінка означає лише, що залишкова тривалість тут не прогнозується. MAE не показується як персональне ±40 хв.

[Незалежне порівняння JS з Python на справжньому input](../reports/pages-release/calculator-python-parity.json):248 origins (247START+snapshot boundary),218 forecasts/30 insufficient histories, last30IDs/clears exact, maxnumeric difference2.84e−14 хв. Окремий контрактний тест охоплює16 synthetic histories (не UX source для калькулятора), Python-reference, часові середовища JS UTC/New_York/Tokyo, DST, corrections/current-end/future-suffix/last30/otherUID. [Браузерні сценарії](../reports/pages-release/calculator-browser-checks.json), [controlled404 без числа](../reports/pages-release/calculator-fetch-failure.json). У браузері перевірено форму/Enter й320/360/390 px; жодного page overflow. JS timezone independence перевірено в Node process TZ; це окремо від фактично використаної браузерної зони. Спроба додаткового timezone override у native Chrome була перервана користувацькою роботою; actual overridden-browser pass не заявляється.

Калькулятор переносить event-clock реконструкцію; publication/received/correction times історичних версій невідомі. Він не є перевіреним live-сервісом чи доказом повноти archive. Отримана після введення історія могла бути виправлена пізніше.

## Демонстраційні приклади та права

Права на перепоширення конкретних записів mirror CSV не встановлено. На сайті **немає справжніх event-level рядків**. Типовий, довгий і невдалий сценарії — явно синтетичні, з вигаданими датами 20–22 вересня 2026. Кожна попередня історія містить рівно 30 авторських завершених інтервалів до початку прикладу.

Правило задане в `scripts/build_pages_demo.py`: durations 8..37 хв / outcome24; 81..110 / outcome180; 5..34 / outcome240. Незмінний `predict_at_start` обчислює відповідно 22.5, 95.5 і 19.5 хв; outcome приєднується після forecast. Поточний відбій не передається. Це приклади взаємодії з інтерфейсом, **не оцінювання якості** на вигаданих даних і не справжні історичні події. Факт відкривається окремою кнопкою; зміна прикладу знову його приховує.

Справжня збережена ретроспективна оцінка primary84 наведена окремо: MAE40.894, RMSE62.620, medianAE24.008, p9076.708 хв. Межі `[01.10.2026 00:00+03:00, 11.10.2026 10:07:59Z)`, неповний край. [Незалежно перевірені агрегати](../reports/ml-diagnostics/diagnostic-evidence.json) і [primary report](../reports/latest-duration-results.md) — джерела цих чисел. Довгі події збережені. 11/84 занижень >60 хв, maxAE248.829; практичної корисності й допустимої ціни помилок не встановлено.

## Актуальна діагностика latest91

Окремий handoff незалежного аудитора містить [походження й агрегати](../reports/latest91/source-and-results.json), [таблицю](../reports/latest91/aggregate-evidence.csv) та portable stdlib script `scripts/recompute_latest91.py`. Перед інтеграцією SHA цих файлів звірено з приватним handoff manifest.

- Source commit: `c5b3bd012c7694e63115999a7bbd0b683eaa8d24`.
- CSV SHA256: `fe79c5726a1a9db9f560d6dad1de1b46f16d93b9b44ff54a2078228cf56cbc0d`.
- Отримано аудитором 12.10.2026 17:19:36.624689 UTC.
- Актуальність саме цього archive path перевірено 12.10.2026 18:28:38.797377 UTC; тоді останній file commit незмінний. Це часовий факт перевірки, не обіцянка freshness до пізнішого моменту.
- Права межа `[01.10.2026 00:00+03:00, 12.10.2026 10:51:36Z)` — час file commit, не доказ суцільного спостереження. Наявні Kyiv записи: 247; останній START07:27:41.346 UTC, CLEAR09:56:19 UTC 12 жовтня. Пізніших записів/днів не створено.
- 91 mature жовтнева подія, включно із 7 після primary edge; MAE40.869/RMSE61.640/medianAE24.272/p9080.352, 12 занижень >60 хв. Сім доданих мають MAE40.567/RMSE48.363.

Це **додаткова діагностика вже відкритого періоду** незмінним методом. Вона не замінює primary84, не є незалежним тестом і не використана для добору моделі. Історичні publication/received/correction times невідомі. Джерела не зливаються. Повний чужий CSV не включено до репозиторію.

Відтворення latest91 окремо, без запуску frozen primary evaluator з іншим checksum:

```sh
mkdir -p work
curl --fail --location 'https://raw.githubusercontent.com/JustJimer/ukraine-air-alert-stats/c5b3bd012c7694e63115999a7bbd0b683eaa8d24/archive/alerts_in_ua.csv' --output work/latest91-input.csv
PYTHONPATH=src PYTHONDONTWRITEBYTECODE=1 python3 scripts/recompute_latest91.py --input work/latest91-input.csv --output work/latest91-summary.json
```

Успішну незалежну перевірку цих незмінених чисел виконав аудитор; реліз не повторює всю наукову серію. Скрипт перевіряє SHA і cohort91/7, не дозволяє мовчки підмінити вхід.

## Межі локальних v3/v4 досліджень

[Конспект агрегованих доказів незалежного аудитора](../reports/latest91/research-audit-summary.json) вказує scope і SHA джерела findings, не замінює повний локальний study package.

Публічний запуск відтворює **default median30**, а не весь локальний v3/v4 study. Досліджені базові/регуляризовані, нелінійні, neural, transfer та spatial варіанти не замінили основний метод. Незалежний аудит збережених v4 прогнозів перевірив 375 наборів /97104 рядки з max numeric discrepancy3.98e−13, v3 — 868 наборів /75594 прогнозів без розбіжностей. Це арифметика умовного replay, не доказ історичної доступності архіву чи практичної користі. Міжрегіональний контекст і transfer не показали стійкої універсальної переваги; це не доводить рівноцінність усіх моделей або відсутність сигналу.

Додаткове оновлення context архіву змінило 5 medians конкретної **HistGB/C** моделі на тих самих84 origins (max25.660 хв, MAE+0.513). Це не автоматична зміна rolling30 і не вимір реального історичного publication leakage. T1 AFT/C aggregate MAE20.625 хв є event-balanced landmark loss, **onset MAE38.238**, n84events/333landmarks; сайт цей окремий estimand не показує. Старі benchmark outputs збережено локально. Їх не оголошено повністю відтворюваними через цей public clone: великі моделі/дані/geo й code packages з окремими маніфестами залишаються зовнішніми локальними артефактами.

### Prospective logger — incomplete, виключений із релізу

`kse_spatial_v4.demo` simulated collector/logger не входить до public Python package чи сайтового маршруту. Відомі дефекти repeated poll/dedup, namespace/version/order, own receipt maturity, issued/outcome linkage і вільного historical helper cutoff з незалежного аудиту F03–F07/F16 **не перебудовували** в цьому спринті. Не називаємо їх виправленими чи operational-ready. Виправлення й реальний prospective stream — наступне окреме завдання. На сайті немає historical inference викликів із model checkpoints. Є збережені синтетичні приклади, справжні агрегати та браузерний rolling30 за реально отриманим pinned CSV. Learned model cutoff/source/cohort bypass через вільний v4 helper неможливий: він не викликається.

## Локальний запуск і перевірки

Сайт не потребує встановлення Python/Node у користувача чи сторонніх CDN. Для developer calculator tests потрібен Node22+ (локально перевірено25.9.0, CI22), без npm dependencies. Основний Python stdlib route Node не потребує. Не відкривайте `index.html` через `file://`: JSON завантажується відносним HTTP-шляхом.

```sh
PYTHONPATH=src PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests_latest -v
PYTHONPATH=src PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests_web -v
PYTHONDONTWRITEBYTECODE=1 python3 scripts/build_pages_demo.py
python3 -m http.server 8000 --bind 127.0.0.1 --directory web
# http://127.0.0.1:8000/
python3 scripts/check_public_artifact.py
# Parity on locally obtained pinned CSV; never commit work/
PYTHONDONTWRITEBYTECODE=1 python3 scripts/verify_pages_calculator.py --input work/latest91-input.csv --output work/calculator-parity.json
```

Builder відтворює synthetic forecasts actual default API та копіює перевірені агрегати; не запускає historical helper, search чи retraining. Public data file містить source/evidence/code hashes. Контрактні тести перевіряють prediction/outcome boundary, fixture values, aggregate binding, relative asset paths і відсутність v4 inference. Браузерний release check: desktop1440×900, mobile320/360/390 px, перемикання трьох сценаріїв, Enter/Space/Tab, відсутність page overflow/console errors, project base path `/kse-air-alert-forecasting/`. Горизонтальний scroll лише всередині широкої таблиці.

Workflow `.github/workflows/pages.yml` перевіряє core і site contracts, завантажує **тільки web/**, деплоїть GitHub Pages. Не додає raw, AI exports чи секрети. Для manual deploy: `gh workflow run pages.yml --ref main`. Якщо Pages ще не увімкнено, owner-authorized API create: `gh api --method POST repos/GirBP/kse-air-alert-forecasting/pages -f build_type=workflow`. Жодної зміни repository visibility, платної інфраструктури чи KSE form submission.

Робочий сайт не закриває вимогу повного AI-log. Приватний комплект організатора явно містить прогалини зовнішніх ChatGPT/Gemini/Antigravity експортів і ще потребує заключних повідомлень активних чатів. Reflection — окремий файл на100 English words.
