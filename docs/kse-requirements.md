# Вимоги KSE та фактичний стан

Підстава — перелік вимог, наданий користувачем у цьому чаті. Дедлайн: 12.10.2026 23:59 Europe/Kyiv.

| Вимога | Доказ | Стан |
|---|---|---|
| Робочий Python-проєкт про часові ряди тривог | src/kse_latest/, README.md, reports/ml-diagnostics/clean-copy-verification.json | Виконано; часовий ряд закритих подій, не добова задача |
| Найсвіжіші придатні дані | reports/latest91/source-and-results.json, docs/pages-demo.md | Окремий latest91 знімок c5b3bd0 від12.10 10:51:36UTC, отримано17:19:36UTC; same-path актуальність перевірено18:28:38UTC. Primary84 незмінний; повнота не доведена |
| Перевірка офіційного ресурсу Києва | docs/latest-data-and-limits.md, provenance/source-checks.json | Виконано; сигнали не використано без підтвердженої зони/парування |
| Останній період без майбутніх навчальних даних/ознак | protocol/latest-v1.json, scripts/verify_implementation_v2.py, reports/ml-diagnostics/implementation-verification.json | Підтверджено частково: 84 прогнози причинні за годинником подій; історична доступність публікацій/виправлень не доведена |
| Зафіксований метод і незмінні старі експерименти | protocol/latest-opening.json, protocol/preserved-previous-files.json, reports/latest-validation.json | Виконано: rolling30; 219 попередніх файлів незмінні |
| Метрики, довгі помилки, демо | reports/latest-duration-results.md, reports/latest91/, web/, docs/pages-demo.md | Primary84 і latest91 окремі; довгі події збережено. На сайті manual-START калькулятор із upstream history, синтетичні UX-приклади та справжні агрегати; real CSV не хоститься |
| Чистий відтворюваний запуск | docs/latest-reproduce.md, reports/ml-diagnostics/clean-copy-verification.json, reports/pages-release/ | Base default перевірено у чистому stdlib venv; core незмінний. Поточні40 core (ядро незмінне) і7 site contract tests PASS, JS↔Python на248 origins; остаточне version-bound приймання — приватний handoff аудитора. Це не доказ прогнозної якості. |
| GitHub-репозиторій | [https://github.com/GirBP/kse-air-alert-forecasting](https://github.com/GirBP/kse-air-alert-forecasting), provenance/github-publication.json | Виконано; PUBLIC, main, push підтверджено |
| Перевірка матеріалів для поширення | docs/latest-data-and-limits.md, .gitignore, scripts/fetch_latest_input.py | Виконано: без чужих raw/детальних таблиць; pinned отримання замість перепоширення невідомої ліцензії |
| Повний текст усіх AI-розмов | Окремий приватний комплект організатора:9 Codex exports, export-manifest.json, submission-readiness.txt | Прогалина: зовнішні ChatGPT/Gemini/Antigravity-експорти; native Codex має cutoff і після реального завершення потребує нового export |
| Reflection ~100 слів англійською | reflection.txt | Виконано, рівно 100 слів |
| Текстові/медійні ознаки | Не використовуються | Необов’язкові, не потрібні для зафіксованого методу |

Матеріали для форми: GitHub URL (https://github.com/GirBP/kse-air-alert-forecasting), повний AI-лог (зовнішні експорти ще відсутні), reflection.txt. Попередня добова задача й широкий збір — окремі незавершені напрями, не приховані за результатом цього пілота.

Технічний ML-аудит — docs/ml-audit.md. Він відрізняє правильність event-clock обчислень від publication-time availability та практичної користі. Default runner виправлено окремою implementation-v2 без зміни числового результату; додаткові жовтневі порівняння post-evaluation, final method залишився rolling30.
