# Saved experiment aggregates for the website

These files are copied aggregate outputs, not raw event data. `sources.json` records their original project-relative paths and SHA-256 values. `v3-selected-parameters.json` contains only selected configuration parameter objects extracted from the original registry. No new training or model selection was performed to build the website.

Run `python3 scripts/build_pages_experiments.py` to reproduce `web/assets/experiments.json`. It retains source metric precision, separates targets/cohorts/conditional levels, averages neural seeds using the existing mean table, and isolates the incomplete K0 cohort. See [site documentation](../../docs/pages-demo.md) for scope, datasets, scientific limitations and the distinct website remaining-time adaptation.

The v3 registry had 1,684 tasks and 215 configurations; its selected comparison table contains 87 eligible family rows and two unidentifiable daily-SARIMA cases. The v4 primary table contains per-seed results; the website uses the saved three-seed mean table. These are exploratory evaluations on previously inspected periods, not a fresh holdout competition. Local research checkpoints and complete training environments are not part of this public release.
