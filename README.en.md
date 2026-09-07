# Validate Time Series

Lock the evaluation protocol first. Connect forecasting models to one evaluator.

[한국어](README.md) · [Skill](skills/validate-time-series/SKILL.md) · [Runtime](skills/validate-time-series/references/runtime.md)

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

As-of observation selection; rolling-origin evaluation; naive, drift, and seasonal-naive baselines; point metrics; submitted-quantile scoring; opt-in DM-style HAC diagnostics; matched-sample, within-track leaderboards; retained failures; and provenance hashes.

The single skill source is `skills/validate-time-series/`. The Codex plugin manifest references this directory. For local installation, link that directory under `$HOME/.agents/skills` without replacing an existing installation; see the Korean README for a guarded command. Invoke `$validate-time-series` in Codex.

## Not included

Individual ARIMA, XGBoost, deep-learning, or foundation-model training adapters; full hyperparameter search; distributed execution; CRPS; conformal training; MCS; SPA; Clark-West; or Giacomini–White implementation. Timestamp and hash checks do not certify arbitrary training code as leakage-free. `ELIGIBLE` means comparable under the recorded protocol, not deployment approval.

## Repository checks and publication

A GitHub Actions matrix is configured for Python 3.11, 3.12, and 3.13. Local execution and hosted CI are reported separately in [verification.json](docs/verification.json). Codex runtime activation and hosted GitHub Actions were not exercised during packaging.

`python3 tools/publish_github.py` previews the initial publication. `--execute` requires authenticated GitHub CLI access and a configured Git identity; it creates **a private repository** at `immanuelk1m/validate-time-series` and pushes an initial commit. It refuses an existing Git checkout or existing remote repository and stages only the packaged file manifest. Read [publication instructions](docs/publish.md) before execution.

## Provenance and license

The imported skill is byte-for-byte preserved; [import-provenance.json](docs/import-provenance.json) records hashes. The existing Astra reference has not been revalidated against live API documentation during repository packaging. See [research sources](skills/validate-time-series/references/sources.md) and [repository references](docs/repository-notes.md).

No project distribution license has been selected. No third-party logos, screenshots, source code, paper PDFs, private data, or credentials are included.
