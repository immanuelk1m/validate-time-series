#!/usr/bin/env python3
"""Freeze a forecast protocol and export its planned rolling folds; never fit models."""
from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path
import sys

ENGINE = Path(__file__).resolve().parents[2] / 'validation-forecast' / 'scripts'
if not (ENGINE / 'tsvalidate.py').is_file():
    raise SystemExit('Install plan-forecast and validation-forecast together from the same checkout.')
sys.path.insert(0, str(ENGINE))
import jsonschema
import tsvalidate as v


def plan_forecast(protocol: Path, data: Path, out: Path, expected_folds: int | None = None) -> None:
    """Publish one plan bundle atomically, with one rolling fold per series/origin."""
    if expected_folds is not None and (isinstance(expected_folds, bool) or not isinstance(expected_folds, int) or expected_folds < 1):
        raise ValueError('expected_folds must be a positive integer')

    def writer(stage: Path) -> None:
        v.lock_plan(protocol, data, stage / 'plan')
        lock, _, origins = v.load_plan(stage / 'plan', include_expected=False)
        p = lock['protocol']
        observations = v.load_data(data, p['series_ids'])
        if v.file_hash(data) != lock['data_sha256']:
            raise ValueError('data changed while creating the plan')
        counts = Counter(row['series_id'] for row in origins)
        if expected_folds is not None and any(count != expected_folds for count in counts.values()):
            raise ValueError(f'expected {expected_folds} rolling folds per series; actual counts: {dict(counts)}')
        folds = []
        for request in origins:
            history, times = v.history_at(observations[request['series_id']], v.stamp(request['origin']), p['split'])
            folds.append({
                'series_id': request['series_id'], 'fold_id': request['origin_index'] + 1,
                'origin': request['origin'], 'window': p['split']['window'],
                'train_start': v.iso(times[0]), 'train_end': v.iso(times[-1]), 'n_train': len(history),
                'target_start': request['target_times'][0], 'target_end': request['target_times'][-1],
                'horizons': ';'.join(map(str, request['horizons'])),
                'report_block': request['origin_index'] // p['metrics']['fold_origins'] + 1,
                'expected_rows_per_candidate': len(request['horizons']) * len(p['seeds']),
            })
        v.write_csv(stage / 'fold_plan.csv', folds)
        summary = {
            'status': 'LOCKED', 'phase': p['phase'],
            'protocol_sha256': lock['protocol_sha256'], 'data_sha256': lock['data_sha256'],
            'fold_plan_sha256': v.file_hash(stage / 'fold_plan.csv'),
            'window': p['split']['window'], 'requested_folds_per_series': expected_folds,
            'rolling_folds_per_series': dict(counts),
            'report_blocks_per_series': {
                series: len({r['report_block'] for r in folds if r['series_id'] == series})
                for series in p['series_ids']
            },
            'expected_rows_per_candidate': sum(r['expected_rows_per_candidate'] for r in folds),
            'refit_policies': {name: track['refit_policy'] for name, track in p['tracks'].items()},
            'training_executed': False, 'forecast_results_generated': False,
            'warning': 'A rolling fold is one series/origin evaluation, not proof of a refit. '
                       'Report blocks are a separate grouping. expected.jsonl is evaluator-only. '
                       'A local lock does not prove that results were previously unseen.',
        }
        (stage / 'planning_summary.json').write_text(v.dump(summary), encoding='utf-8')
        (stage / 'protocol.json').write_text(v.dump(p), encoding='utf-8')
    v.publish(out, writer)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--protocol', type=Path, required=True)
    parser.add_argument('--data', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--expected-folds', type=int, help='Required rolling fold count per series, when specified')
    args = parser.parse_args()
    try:
        plan_forecast(args.protocol, args.data, args.out, args.expected_folds)
        print(v.dump({'status': 'LOCKED', 'output': str(args.out), 'training_executed': False}), end='')
    except (ValueError, KeyError, TypeError, OSError, jsonschema.ValidationError) as error:
        print(f'PLANNING_BLOCKED: {error}', file=sys.stderr)
        sys.exit(2)


if __name__ == '__main__':
    main()
