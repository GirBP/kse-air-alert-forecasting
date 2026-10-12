# Вимоги KSE та фактичний стан

Підстава — перелік вимог, наданий користувачем у цьому чаті. Дедлайн: 12.10.2026 23:59 Europe/Kyiv.

| Вимога | Доказ | Стан |
|---|---|---|
| Робочий Python-проєкт про часові ряди тривог | src/kse_latest/, README.md, reports/ml-diagnostics/clean-copy-verification.json | Виконано; часовий ряд закритих подій, не добова задача |
| Найсвіжіші придатні дані | provenance/source-checks.json, provenance/retrieval-log.json, protocol/latest-v1.json | Виконано серед перевірених відомих джерел; 11 жовтня часткове, повнота не доведена |
| Перевірка офіційного ресурсу Києва | docs/latest-data-and-limits.md, provenance/source-checks.json | Виконано; сигнали не використано без підтвердженої зони/парування |
| Останній період без майбутніх навчальних даних/ознак | protocol/latest-v1.json, scripts/verify_implementation_v2.py, reports/ml-diagnostics/implementation-verification.json | Виконано за годинником подій; 84 жовтневі прогнози, час історичної публікації невідомий |
| Зафіксований метод і незмінні старі експерименти | protocol/latest-opening.json, protocol/preserved-previous-files.json, reports/latest-validation.json | Виконано: rolling30; 219 попередніх файлів незмінні |
| Метрики, довгі помилки, демо | reports/latest-duration-results.md, reports/latest-demo.txt | Виконано; всі довгі події залишені |
| Чистий відтворюваний запуск | docs/latest-reproduce.md, reports/ml-diagnostics/clean-copy-verification.json, reports/ml-diagnostics/implementation-tests.txt | Виконано для corrected v2: чистий Git clone, ізольований stdlib venv; 40 runtime tests, 8 однакових diagnostic CSV. Це не доказ прогнозної якості. |
| GitHub-репозиторій | [https://github.com/GirBP/kse-air-alert-forecasting](https://github.com/GirBP/kse-air-alert-forecasting), provenance/github-publication.json | Виконано; PUBLIC, main, push підтверджено |
| Перевірка матеріалів для поширення | docs/latest-data-and-limits.md, .gitignore, scripts/fetch_latest_input.py | Виконано: без чужих raw/детальних таблиць; pinned отримання замість перепоширення невідомої ліцензії |
| Повний текст усіх AI-розмов | Приватне submission/ai-conversations/, export-manifest.json, AI-EXPORT-GAPS.md | Прогалина: зовнішні ChatGPT/Gemini/Antigravity-експорти; native Codex має cutoff і після реального завершення потребує нового export |
| Reflection ~100 слів англійською | reflection.txt | Виконано, рівно 100 слів |
| Текстові/медійні ознаки | Не використовуються | Необов’язкові, не потрібні для зафіксованого методу |

Матеріали для форми: GitHub URL (https://github.com/GirBP/kse-air-alert-forecasting), повний AI-лог (зовнішні експорти ще відсутні), reflection.txt. Попередня добова задача й широкий збір — окремі незавершені напрями, не приховані за результатом цього пілота.

Технічний ML-аудит — docs/ml-audit.md. Він відрізняє правильність event-clock обчислень від publication-time availability та практичної користі. Default runner виправлено окремою implementation-v2 без зміни числового результату; додаткові жовтневі порівняння post-evaluation, final method залишився rolling30.
