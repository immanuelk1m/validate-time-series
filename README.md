# Validate Time Series

Lock the evaluation protocol first. Connect forecasting models to one evaluator.

[한국어](README.ko.md) · [Skill](skills/validate-time-series/SKILL.md) · [Runtime](skills/validate-time-series/references/runtime.md)

A repository distribution of the existing `validate-time-series v1.1.0-astra` Agent Skill. It contains the Korean skill, GPT-6 Astra workflow guidance, reference documents, JSON contracts, a Python evaluator, three baselines, and runnable checks. The host selects the language model; installing the skill does not select or change it.

## Run locally

Python 3.11 or newer is required. From the repository root:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r skills/validate-time-series/scripts/requirements.txt
.venv/bin/python skills/validate-time-series/scripts/test_validation.py
.venv/bin/python tools/test_repository.py
.venv/bin/python skills/validate-time-series/scripts/demo.py --out ./demo-output
```

The demo uses synthetic data, with no GPU, model downloads, or paid API calls. Choose a new output directory for every run. See the [generated example leaderboard](docs/example-output/leaderboard.csv); it is not evidence of commodity-market forecasting performance.

## Included

Rolling-origin evaluation; naive, drift, and seasonal-naive baselines; point metrics; submitted-quantile scoring; opt-in DM-style HAC diagnostics; matched-sample, within-track leaderboards; retained failures; leakage cutoff checks; and provenance hashes.

The single skill source is `skills/validate-time-series/`. The Codex plugin manifest references this directory. For local installation, link that directory under `$HOME/.agents/skills` without replacing an existing installation; see the Korean README for a guarded command. Invoke `$validate-time-series` in Codex.

## Not included

Individual ARIMA, XGBoost, deep-learning, or foundation-model training adapters; full hyperparameter search; distributed execution; point-in-time availability or data-vintage validation; CRPS; conformal training; MCS; SPA; Clark-West; or Giacomini–White implementation. Output cutoff and hash checks do not certify arbitrary training code as leakage-free. `ELIGIBLE` means comparable under the recorded protocol, not deployment approval.

## License

This project is licensed under the [MIT License](LICENSE).

## References

| Authors | Year | Paper | Journal |
|---|---|---|---|
| Hewamalage, H., Ackermann, K., Bergmeir, C. | 2023 | [Forecast evaluation for data scientists: common pitfalls and best practices](https://doi.org/10.1007/s10618-022-00894-5) | Data Mining and Knowledge Discovery, 37, 788–832 |
| Qiu, X. et al. | 2024 | [TFB: Towards Comprehensive and Fair Benchmarking of Time Series Forecasting Methods](https://doi.org/10.14778/3665844.3665863) | PVLDB, 17(9) |
| Bracher, J., Ray, E. L., Gneiting, T., Reich, N. G. | 2021 | [Evaluating epidemic forecasts in an interval format](https://doi.org/10.1371/journal.pcbi.1008618) | PLOS Computational Biology, 17(2), e1008618 |
| Diebold, F. X., Mariano, R. S. | 1995 | [Comparing Predictive Accuracy](https://doi.org/10.1080/07350015.1995.10524599) | Journal of Business & Economic Statistics, 13(3), 253–263 |

See [research sources and implementation scope](skills/validate-time-series/references/sources.md) for how each paper informs this project. TFB was published in 2024; the consulted version is [arXiv v4 (2025)](https://arxiv.org/abs/2403.20150v4).
