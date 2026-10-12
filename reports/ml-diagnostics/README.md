# Компактні ML-діагностики

Усе для opened October має статус **post-evaluation**. Три методи й групи записані до їхнього додаткового порівняння в audit/diagnostic-plan.json; no new winner.

- method-comparison-posthoc.csv, paired-comparison-posthoc.csv: однакові 84 події, загальні/парні descriptive metrics.
- calendar-errors.csv: місцеві дні та лише 2 неповні weekly groups; n обов’язкове.
- duration-errors.csv: bands за фактом лише для діагностики, не features.
- group-errors.csv: stored red/yellow (red n=3) і start-hour groups; час historical level assignment невідомий.
- large-underpredictions.csv: частоти та величини shortfall >30/60/120, без trimming.
- source-distribution.csv, error-dependence.csv: descriptive shift/irregular-event correlations, не normality/stationarity tests.
- historical-* tables/evidence: незмінні Vadimkin v1/v2 aggregates, CV/scalers/bootstrap origin hashes. 27/14 calendar clusters; 30000 saved replicas audited; не p-values, не model equivalence.
- actual-vs-prediction.png, errors-in-time.png, absolute-error-ecdf.png: три scientific plots, повний хвіст і явні scope/n.

Відтворюваний код: scripts/ml_diagnostics.py. У повному проєкті він читає retained historical artifacts; у clean clone використовуються опубліковані historical aggregates без удавання нового аудиту відсутніх приватних файлів. Після цього додатковий raw replay: scripts/replay_historical_selection.py; frozen coefficients і pinned source URL/SHA в audit/.

CSV/JSON діагностики — stdlib, графіки — Matplotlib із requirements-ml-audit.txt. Прогнозний проєкт Matplotlib не потребує. Raw і event-level входи не публікуються; ці таблиці/фігури — авторські descriptive aggregates з attribution.

implementation-verification.json перевіряє 210 числових прогнозів та 207 audit-protected files; audit-run.json також фіксує 219 старих preservation checks. clean-copy-verification.json і corrected-demo.txt — фактичний запуск clean Git clone, не незалежна нова оцінка якості. implementation-tests.txt — 40 змістовних runtime tests; їхній count не є прогнозною метрикою.
