# Working on this repository

The two canonical skills are `skills/plan-forecast/` and `skills/validation-forecast/`. Read the selected skill and the affected code before editing. Plan-forecast decides and locks the pre-execution design; validation-forecast audits existing execution evidence and scores existing forecasts. Model training is a separate, explicitly requested stage.

Keep exactly these two skill entrypoints. The shared evaluator, schemas and methodological references live once in validation-forecast; plan-forecast imports/references that sibling directory. Install both from the same checkout. Do not duplicate the evaluator or keep the old combined SKILL.md.

Reuse the existing evaluator, standard library, and installed dependencies. Add only the code needed for the task. Keep validation, error handling, privacy boundaries, and numerical correctness even when simplifying code. This maintenance approach follows the user's Ponytail preference; the reference is recorded in `docs/repository-notes.md`.

Preserve protocol locking, chronological train/test boundaries, complete evaluation keys, matched naive comparison, failure retention, and separate final evaluation. Do not invent observations, scores, execution results, or implementation support. Agent model configuration and forecast-model candidates are different concerns.

Run a focused check for the change. For numerical or shared pipeline changes, run `python skills/validation-forecast/scripts/test_validation.py`. For mode boundaries and planned-fold exports, run `python tools/test_forecast_modes.py`. For repository metadata and publication changes, run `python tools/test_repository.py`. Use a new output path for a smoke demo. Never send private data to CI.

Write Korean documentation plainly; keep established statistical terminology and factual qualifications. Follow the original package's source notes rather than silently attributing new behavior to its papers.

`tools/publish_github.py --execute` creates a remote private repository and pushes commits. Do not execute it without an explicit publication request. Do not change visibility, choose a distribution license, expose credentials, force-push, or overwrite existing outputs as part of unrelated maintenance.

`repository-files.json` is the initial-publication allowlist. It is not a signature or a security boundary. `docs/import-provenance.json` describes the original import, not a promise that future versions stay unchanged.

Rolling Fold counts, report blocks (`metrics.fold_origins`) and actual refit counts are distinct. Preserve this distinction in code, prompts and tests. Missing fit logs mean UNKNOWN, not proof of TSCV execution. Never rebuild a retrospective plan and call it prospectively frozen.
