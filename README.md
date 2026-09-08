# Forecast Skills

Separate pre-forecast planning from post-forecast validation.

[한국어](README.ko.md) · [plan-forecast](skills/plan-forecast/SKILL.md) · [validation-forecast](skills/validation-forecast/SKILL.md) · [Stage contract](skills/validation-forecast/references/stage-contract.md)

| Topic | plan-forecast — before execution | validation-forecast — after execution |
|---|---|---|
| TSCV | Choose periods, fold count and the split schedule | Verify actual TSCV execution and matching folds/periods |
| Window | Choose expanding/sliding and training lengths | Check actual training ranges and window movement |
| Training | Freeze preprocessing, refit and tuning rules | Inspect fit, preprocessing and tuning evidence |
| Evaluation | Choose baselines, metrics, aggregation and uncertainty policy | Score matched results and report uncertainty and failures |
| Output | Protocol, planned folds and lock | Plan-compliance report, audit and leaderboard |

Model fitting and forecasting belong to a separate execution stage. A planning-only request must not train or score models. A validation request must not change the plan to fit the observed scores. An explicitly requested end-to-end workflow is plan → model execution → validation.

A rolling fold means one series/origin evaluation. `metrics.fold_origins` groups origins into reporting blocks; it is neither the TSCV fold count nor proof of a model refit.

## Install both skills

Use the two directories from the same checkout. The shared evaluator, schemas and methodological references remain in `skills/validation-forecast/`; plan-forecast references that sibling instead of duplicating it. Copying plan-forecast alone is not supported.

From the repository root, without overwriting existing installations:

```bash
for name in plan-forecast validation-forecast; do
  test -f "$PWD/skills/$name/SKILL.md" || exit 1
  dest="$HOME/.agents/skills/$name"
  if [ -e "$dest" ] || [ -L "$dest" ]; then
    printf 'Existing installation: %s\n' "$dest"
    exit 1
  fi
done
mkdir -p "$HOME/.agents/skills"
for name in plan-forecast validation-forecast; do
  ln -s "$PWD/skills/$name" "$HOME/.agents/skills/$name"
done
```

Invoke `$plan-forecast` to choose and lock the design, or `$validation-forecast` to audit existing forecasts against it. The old `$validate-time-series` combined entrypoint has been replaced; old user installations are not automatically deleted. The plugin keeps its repository identifier and discovers both skills under `skills/`. Host installation/invocation has not been certified by the Python checks.

## Run

Python 3.11 or newer is required. Prepare a protocol and a target CSV with exactly `series_id,timestamp,value`. Data availability-time and vintage checks remain outside both skills' scope.

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r skills/validation-forecast/scripts/requirements.txt

# Before execution: freeze and export the planned folds.
.venv/bin/python skills/plan-forecast/scripts/plan_forecast.py \
  --protocol ./protocol.json --data ./target.csv --out ./experiment-v1

# Separate execution stage: generate a registered baseline or run a model adapter.
.venv/bin/python skills/validation-forecast/scripts/tsvalidate.py baseline \
  --plan ./experiment-v1/plan --data ./target.csv --method naive --out ./runs/naive

# After execution: score existing predictions against the existing lock.
.venv/bin/python skills/validation-forecast/scripts/validation_forecast.py \
  --plan ./experiment-v1/plan --runs ./runs/naive/run.json --out ./evaluation-v1
```

Other registered candidates remain MISSING_RUN until submitted. Add `--expected-folds K` to planning to require K rolling folds per series. A mismatch fails without dropping evaluation rows or changing the settings.

Planning produces `protocol.json`, `fold_plan.csv`, `planning_summary.json`, and the existing `plan/` contract. `plan/expected.jsonl` contains evaluator-only truth; do not pass it to model code. The bundled lock is for offline benchmarks with observed truth. An authorized evaluator must handle a protected holdout; planning future forecasts without truth remains a draft.

The validation CLI performs ledger and metric checks, not an automatic audit of arbitrary model internals. Fill the [compliance table](skills/validation-forecast/assets/compliance-template.csv) from actual fold/fit/code evidence. Missing evidence is UNKNOWN even when ledger coverage is complete. An absent pre-existing plan is a retrospective audit, not prospective validation. `ELIGIBLE` is not proof that TSCV ran, that leakage is absent, or that deployment is approved.

## Checks and scope

```bash
.venv/bin/python skills/validation-forecast/scripts/test_validation.py
.venv/bin/python tools/test_forecast_modes.py
.venv/bin/python tools/test_repository.py
.venv/bin/python skills/validation-forecast/scripts/demo.py --out ./demo-output
```

The synthetic demo needs no GPU, model downloads or paid API calls. Outputs are never overwritten. CI runs Python 3.11/3.12/3.13 and retains a `forecast-skills-source` artifact containing only checked-in source.

The existing evaluator still provides three baselines, point and submitted-quantile metrics, optional DM-HAC/Holm, failure retention, and within-track leaderboards. Individual ARIMA/ML/DL/foundation-model training adapters, full HPO, arbitrary K-fold/nested split execution, gap/purge execution, CRPS, conformal training, MCS, SPA, Clark-West and Giacomini–White are not bundled. See the [runtime contract](skills/validation-forecast/references/runtime.md) for implementation boundaries.

## License

[MIT License](LICENSE).

## References

| Authors | Year | Paper | Journal |
|---|---|---|---|
| Hewamalage, H., Ackermann, K., Bergmeir, C. | 2023 | [Forecast evaluation for data scientists: common pitfalls and best practices](https://doi.org/10.1007/s10618-022-00894-5) | Data Mining and Knowledge Discovery, 37, 788–832 |
| Qiu, X. et al. | 2024 | [TFB: Towards Comprehensive and Fair Benchmarking of Time Series Forecasting Methods](https://doi.org/10.14778/3665844.3665863) | PVLDB, 17(9) |
| Bracher, J., Ray, E. L., Gneiting, T., Reich, N. G. | 2021 | [Evaluating epidemic forecasts in an interval format](https://doi.org/10.1371/journal.pcbi.1008618) | PLOS Computational Biology, 17(2), e1008618 |
| Diebold, F. X., Mariano, R. S. | 1995 | [Comparing Predictive Accuracy](https://doi.org/10.1080/07350015.1995.10524599) | Journal of Business & Economic Statistics, 13(3), 253–263 |

See [research sources and implementation scope](skills/validation-forecast/references/sources.md) for how each paper informs this project. TFB was published in 2024; the consulted version is [arXiv v4 (2025)](https://arxiv.org/abs/2403.20150v4).
