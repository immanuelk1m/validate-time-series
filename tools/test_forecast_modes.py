#!/usr/bin/env python3
"""Regression checks for the planning/validation boundary and their shared runtime."""
from __future__ import annotations

import csv
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
PLAN = ROOT / 'skills/plan-forecast'
VALIDATION = ROOT / 'skills/validation-forecast'
sys.path.insert(0, str(PLAN / 'scripts'))
import plan_forecast as planner
v = planner.v


class StageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.protocol = v.read_json(VALIDATION / 'assets/protocol.example.json')
        self.protocol.update(series_ids=['s'], horizons=[1, 2], seeds=[0, 1], regimes=[])
        self.protocol['split'].update(min_train_size=8, stride=1,
            origin_start='2020-01-08T00:00:00Z', origin_end='2020-02-05T00:00:00Z',
            target_end='2020-02-09T00:00:00Z')
        self.protocol['metrics'].update(seasonal_period=2, fold_origins=3)
        start = datetime(2020, 1, 1, tzinfo=timezone.utc)
        v.write_csv(self.root / 'target.csv', [
            {'series_id': 's', 'timestamp': v.iso(start + timedelta(days=i)), 'value': 100 + i}
            for i in range(40)
        ])
        self.write_protocol()

    def write_protocol(self):
        (self.root / 'protocol.json').write_text(v.dump(self.protocol), encoding='utf-8')

    def plan(self, expected_folds=None):
        planner.plan_forecast(self.root / 'protocol.json', self.root / 'target.csv',
                              self.root / 'experiment', expected_folds)
        with (self.root / 'experiment/fold_plan.csv').open() as handle:
            return list(csv.DictReader(handle))

    def cli(self, script, *arguments):
        return subprocess.run([sys.executable, str(script), *map(str, arguments)],
                              cwd=self.root, text=True, capture_output=True, timeout=30)

    def test_plan_does_not_fit_forecast_or_score(self):
        with patch.object(v, 'baseline_run', side_effect=AssertionError('no training')),\
             patch.object(v, 'predict_baseline', side_effect=AssertionError('no predictions')),\
             patch.object(v, 'score_runs', side_effect=AssertionError('no scoring')):
            self.plan(29)
        summary = v.read_json(self.root / 'experiment/planning_summary.json')
        self.assertFalse(summary['training_executed'])
        self.assertFalse(summary['forecast_results_generated'])
        self.assertFalse(list((self.root / 'experiment').rglob('forecasts.jsonl')))

    def test_fold_count_is_not_reporting_block_count(self):
        folds = self.plan(29)
        summary = v.read_json(self.root / 'experiment/planning_summary.json')
        self.assertEqual(summary['rolling_folds_per_series'], {'s': 29})
        self.assertEqual(summary['report_blocks_per_series'], {'s': 10})
        self.assertEqual(summary['expected_rows_per_candidate'], 116)
        self.assertEqual(len(folds), 29)
        self.assertEqual(summary['fold_plan_sha256'], v.file_hash(self.root / 'experiment/fold_plan.csv'))

    def test_expanding_window_grows(self):
        folds = self.plan()
        self.assertEqual(folds[0]['train_start'], folds[-1]['train_start'])
        self.assertEqual(int(folds[0]['n_train']), 8)
        self.assertEqual(int(folds[-1]['n_train']), 36)
        self.assertTrue(all(row['train_end'] == row['origin'] for row in folds))

    def test_sliding_window_moves_with_fixed_length(self):
        self.protocol['split'].update(window='sliding', max_train_size=8)
        self.write_protocol()
        folds = self.plan()
        self.assertNotEqual(folds[0]['train_start'], folds[-1]['train_start'])
        self.assertEqual({int(row['n_train']) for row in folds}, {8})

    def test_requested_fold_count_mismatch_leaves_no_output(self):
        with self.assertRaisesRegex(ValueError, 'actual counts'):
            self.plan(28)
        self.assertFalse((self.root / 'experiment').exists())

    def test_expected_fold_count_type_and_range(self):
        for count in (0, -1, True, 2.5):
            with self.subTest(count=count), self.assertRaises(ValueError):
                self.plan(count)
        self.assertFalse((self.root / 'experiment').exists())

    def test_warmup_and_horizon_boundary_count(self):
        self.protocol['split'].update(origin_start='2020-01-01T00:00:00Z',
                                      origin_end='2020-02-08T00:00:00Z')
        self.write_protocol()
        self.assertEqual(len(self.plan(31)), 31)
        self.assertEqual(len(v.read_jsonl(self.root / 'experiment/plan/omitted_origins.jsonl')), 8)

    def test_plan_does_not_overwrite(self):
        self.plan()
        with self.assertRaisesRegex(ValueError, 'already exists'):
            self.plan()

    def test_plan_runner_validation_handoff_preserves_lock(self):
        self.plan()
        lock_path = self.root / 'experiment/plan/lock.json'
        before = v.file_hash(lock_path)
        runs = []
        for method in ('naive', 'drift', 'seasonal-naive'):
            # Model execution is explicitly separate from both stage entrypoints.
            v.baseline_run(lock_path.parent, self.root / 'target.csv', method, self.root / method)
            runs.append(self.root / method / 'run.json')
        result = self.cli(VALIDATION / 'scripts/validation_forecast.py',
                          '--plan', lock_path.parent, '--runs', *runs, '--out', self.root / 'evaluation')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(v.file_hash(lock_path), before)
        rows = v.read_json(self.root / 'evaluation/summary.json')['leaderboard']
        self.assertEqual({row['status'] for row in rows}, {'ELIGIBLE'})
        self.assertEqual({row['coverage'] for row in rows}, {1})

    def test_validation_requires_existing_plan(self):
        result = self.cli(VALIDATION / 'scripts/validation_forecast.py',
                          '--plan', 'missing-plan', '--runs', 'missing-run.json', '--out', 'evaluation')
        self.assertEqual(result.returncode, 2)
        self.assertIn('VALIDATION_BLOCKED', result.stderr)
        self.assertFalse((self.root / 'evaluation').exists())

    def test_mode_cli_does_not_accept_other_stage_options(self):
        plan = self.cli(PLAN / 'scripts/plan_forecast.py', '--protocol', 'protocol.json',
                        '--data', 'target.csv', '--out', 'experiment', '--runs', 'run.json')
        validation = self.cli(VALIDATION / 'scripts/validation_forecast.py', '--plan', 'plan',
                              '--runs', 'run.json', '--out', 'evaluation', '--window', 'sliding')
        for result in (plan, validation):
            self.assertEqual(result.returncode, 2)
            self.assertIn('unrecognized arguments', result.stderr)

    def test_symlink_install_resolves_shared_runtime(self):
        link = self.root / 'installed-plan'
        link.symlink_to(PLAN, target_is_directory=True)
        result = self.cli(link / 'scripts/plan_forecast.py', '--protocol', 'protocol.json',
                          '--data', 'target.csv', '--out', 'from-link', '--expected-folds', '29')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((self.root / 'from-link/planning_summary.json').is_file())


class SkillRoutingTests(unittest.TestCase):
    def test_both_skill_metadata_and_prompts(self):
        for skill in (PLAN, VALIDATION):
            with self.subTest(skill=skill.name):
                text = (skill / 'SKILL.md').read_text(encoding='utf-8')
                match = re.match(r'^---\nname: ([a-z0-9-]+)\ndescription: (.+)\n---', text)
                self.assertIsNotNone(match)
                self.assertEqual(match[1], skill.name)
                self.assertLessEqual(len(json.loads(match[2])), 1024)
                self.assertLess(len(text.splitlines()), 500)
                fields = {m[1]: json.loads(m[2]) for m in re.finditer(
                    r'^  ([a-z_]+): (.+)$', (skill / 'agents/openai.yaml').read_text(), re.MULTILINE)}
                self.assertEqual(set(fields), {'display_name', 'short_description', 'default_prompt'})
                self.assertTrue(25 <= len(fields['short_description']) <= 64)
                self.assertIn('$' + skill.name, fields['default_prompt'])
                self.assertNotIn('$validate-time-series', fields['default_prompt'])

    def test_all_skill_reference_links_resolve(self):
        for document in (ROOT / 'skills').rglob('*.md'):
            for link in re.findall(r'\]\(([^)]+)\)', document.read_text(encoding='utf-8')):
                if '://' not in link and not link.startswith('#'):
                    self.assertTrue((document.parent / link.split('#')[0]).is_file(), (str(document), link))

    def test_behavior_cases_have_explicit_routing(self):
        behavior = v.read_json(VALIDATION / 'assets/behavior-evals.json')
        self.assertEqual(behavior['status'], 'NOT_EXECUTED_AGENT_EVALUATIONS')
        for case in behavior['cases']:
            self.assertIn(case['skill'], {'plan-forecast', 'validation-forecast'})
        ids = {case['id'] for case in behavior['cases']}
        self.assertTrue({'plan-fold-count', 'validate-tscv-evidence', 'validate-no-replanning',
                         'no-preexisting-plan', 'combined-request'}.issubset(ids))

    def test_removed_data_checks_remain_removed(self):
        schema = v.read_json(VALIDATION / 'assets/protocol.schema.json')
        self.assertNotIn('truth_as_of', schema['properties'])
        engine = (VALIDATION / 'scripts/tsvalidate.py').read_text()
        self.assertNotIn('available_at', engine)
        self.assertNotIn('snapshot(', engine)


if __name__ == '__main__':
    unittest.main(verbosity=2)
