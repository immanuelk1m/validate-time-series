#!/usr/bin/env python3
"""Executable regression checks. No API calls, model downloads, or paid compute."""
from __future__ import annotations

import copy
import csv
from datetime import datetime, timedelta, timezone
import math
import re
from pathlib import Path
import tempfile
import unittest

import jsonschema
import numpy as np

import metrics
import tsvalidate as v


class MetricTests(unittest.TestCase):
    def test_known_point_metrics(self):
        result=metrics.point_summary([1,2,3],[1,4,2])
        self.assertEqual(result['mae'],1)
        self.assertAlmostEqual(result['mse'],5/3)
        self.assertAlmostEqual(result['bias_me'],-1/3)

    def test_zero_scaling_is_not_epsilon(self):
        self.assertEqual(metrics.scaled_errors([5,5,5],1),(0,0))
        self.assertIsNone(metrics.ratio(1,0))
        self.assertIsNone(metrics.ratio(0,0))

    def test_short_seasonal_history(self):
        self.assertEqual(metrics.scaled_errors([1,2],2),(None,None))

    def test_mase_is_not_oos_naive_comparison(self):
        scale,_=metrics.scaled_errors([0,100,0,100],1)
        self.assertLess(10/scale,1)
        self.assertGreater(10/1,1)  # Candidate test AE=10, paired naive AE=1.

    def test_nonfinite_point_rejected(self):
        with self.assertRaises(ValueError):
            metrics.point_summary([1],[float('nan')])

    def test_shape_mismatch_rejected(self):
        with self.assertRaises(ValueError):
            metrics.point_summary([1,2],[1])

    def test_probability_scores(self):
        result=metrics.probabilistic_scores(10,{'0.1':8,'0.5':10,'0.9':12})
        self.assertEqual(result['coverage_0.8'],1)
        self.assertEqual(result['width_0.8'],4)
        self.assertEqual(result['interval_score_0.8'],4)
        self.assertAlmostEqual(result['wis'],0.4/1.5)

    def test_interval_miss_penalty(self):
        result=metrics.probabilistic_scores(15,{'0.1':8,'0.5':10,'0.9':12})
        self.assertEqual(result['interval_score_0.8'],34)

    def test_crossing_quantiles_rejected(self):
        with self.assertRaises(ValueError):
            metrics.probabilistic_scores(10,{'0.1':12,'0.9':8})

    def test_duplicate_numeric_quantiles_rejected(self):
        with self.assertRaises(ValueError):
            metrics.probabilistic_scores(10,{'0.1':8,'0.10':9})

    def test_no_wis_for_asymmetric_grid(self):
        self.assertNotIn('wis',metrics.probabilistic_scores(1,{'0.1':0,'0.5':1,'0.95':2}))

    def test_holm_known_values(self):
        np.testing.assert_allclose(metrics.holm([0.01,0.04,0.03]),[0.03,0.06,0.06])

    def test_holm_incomplete_family_conservative(self):
        self.assertEqual(metrics.holm([0.01,None]),[0.02,None])

    def test_dm_zero_difference(self):
        self.assertEqual(metrics.dm_hac([0]*50,3)['p_value'],1)

    def test_dm_degenerate_difference(self):
        self.assertIsNone(metrics.dm_hac([1]*50,3)['p_value'])

    def test_dm_small_sample(self):
        self.assertEqual(metrics.dm_hac([1,2,3],0)['status'],'insufficient_origins')

    def test_dm_known_lag_zero(self):
        d=np.tile([-1.,0.,1.,2.],20)
        result=metrics.dm_hac(d.tolist(),0)
        statistic=float(d.mean()/math.sqrt(d.var()/len(d)))
        self.assertAlmostEqual(result['statistic'],statistic)

    def test_dm_lags_validation(self):
        with self.assertRaises(ValueError):
            metrics.dm_hac([1]*50,-1)


class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.root=Path(self.temp.name)
        self.p=v.read_json(v.ROOT/'assets/protocol.example.json')
        self.p.update(series_ids=['s'],horizons=[1,2],seeds=[0,1],regimes=[])
        self.p['split'].update(min_train_size=8,stride=1,origin_start='2020-01-08T00:00:00Z',
          origin_end='2020-02-05T00:00:00Z',target_end='2020-02-09T00:00:00Z')
        self.p['metrics'].update(seasonal_period=2,fold_origins=3)
        start=datetime(2020,1,1,tzinfo=timezone.utc)
        self.data=[]
        for i in range(40):
            when=v.iso(start+timedelta(days=i))
            self.data.append({'series_id':'s','timestamp':when,'value':100+i+math.sin(i)})
        self.write_data()
        self.make_plan()
        self.paths=[]
        for method in ['naive','drift','seasonal-naive']:
            v.baseline_run(self.root/'plan',self.root/'data.csv',method,self.root/method)
            self.paths.append(self.root/method/'run.json')

    def tearDown(self):
        self.temp.cleanup()

    def write_data(self):
        with (self.root/'data.csv').open('w',newline='') as handle:
            writer=csv.DictWriter(handle,fieldnames=['series_id','timestamp','value'])
            writer.writeheader();writer.writerows(self.data)

    def make_plan(self, name='plan'):
        (self.root/'protocol.json').write_text(v.dump(self.p))
        v.lock_plan(self.root/'protocol.json',self.root/'data.csv',self.root/name)

    def mutate_forecasts(self, change, model='drift'):
        path=self.root/model/'forecasts.jsonl'
        rows=v.read_jsonl(path)
        change(rows)
        v.write_jsonl(path,rows)

    def mutate_manifest(self, change, model='drift'):
        path=self.root/model/'run.json'
        manifest=v.read_json(path)
        change(manifest)
        path.write_text(v.dump(manifest))

    def score(self, paths=None, plan='plan'):
        v.score_runs(self.root/plan,self.paths if paths is None else paths,self.root/'scores')
        return {r['model_id']:r for r in v.read_json(self.root/'scores/summary.json')['leaderboard']}

    def test_end_to_end_complete(self):
        rows=self.score()
        self.assertEqual(rows['naive']['status'],'ELIGIBLE')
        self.assertAlmostEqual(rows['naive']['macro_naive_skill'],0)
        self.assertEqual(rows['drift']['coverage'],1)
        self.assertEqual(rows['drift']['seed_skill_std'],0)

    def test_output_no_overwrite(self):
        self.score()
        with self.assertRaises(ValueError):
            v.score_runs(self.root/'plan',self.paths,self.root/'scores')

    def test_no_test_drop_last(self):
        self.mutate_forecasts(lambda rows: rows.pop())
        row=self.score()['drift']
        self.assertEqual(row['status'],'INCOMPLETE')
        self.assertIsNone(row['rank'])
        self.assertIsNone(row['macro_naive_skill'])

    def test_failed_forecast_not_hidden(self):
        self.mutate_forecasts(lambda rows: rows[0].update(status='failed',error='OOM'))
        self.assertEqual(self.score()['drift']['status'],'INCOMPLETE')

    def test_missing_registered_model_retained(self):
        self.assertEqual(self.score(self.paths[:1])['drift']['status'],'MISSING_RUN')

    def test_duplicate_forecast_rejected(self):
        self.mutate_forecasts(lambda rows: rows.append(copy.deepcopy(rows[0])))
        self.assertEqual(self.score()['drift']['status'],'INVALID')

    def test_unknown_horizon_rejected(self):
        self.mutate_forecasts(lambda rows: rows[0].update(horizon=9))
        self.assertEqual(self.score()['drift']['status'],'INVALID')

    def test_future_fit_cutoff_rejected(self):
        self.mutate_forecasts(lambda rows: rows[0].update(fit_cutoff='2025-01-01T00:00:00Z'))
        self.assertEqual(self.score()['drift']['status'],'INVALID')

    def test_future_preprocess_cutoff_rejected(self):
        self.mutate_forecasts(lambda rows: rows[0].update(preprocess_cutoff='2025-01-01T00:00:00Z'))
        self.assertEqual(self.score()['drift']['status'],'INVALID')

    def test_wrong_target_alignment_rejected(self):
        self.mutate_forecasts(lambda rows: rows[0].update(target_time='2020-02-09T00:00:00Z'))
        self.assertEqual(self.score()['drift']['status'],'INVALID')

    def test_unreviewed_outputs_not_ranked(self):
        self.mutate_manifest(lambda m:m['audit'].update(status='unreviewed'))
        self.assertEqual(self.score()['drift']['status'],'UNREVIEWED')

    def test_protocol_mismatch_rejected(self):
        self.mutate_manifest(lambda m:m.update(protocol_sha256='0'*64))
        self.assertEqual(self.score()['drift']['status'],'INVALID')

    def test_data_hash_mismatch_rejected(self):
        self.mutate_manifest(lambda m:m.update(data_sha256='0'*64))
        self.assertEqual(self.score()['drift']['status'],'INVALID')

    def test_tampered_locked_truth_blocked(self):
        with (self.root/'plan/expected.jsonl').open('a') as handle:handle.write('{}\n')
        with self.assertRaises(ValueError):self.score()

    def test_timezone_required(self):
        with self.assertRaises(ValueError):v.stamp('2020-01-01')

    def test_duplicate_observation_rejected(self):
        self.data.append(self.data[0]);self.write_data()
        with self.assertRaises(ValueError):v.load_data(self.root/'data.csv',['s'])

    def test_future_perturbation_does_not_change_history(self):
        data=v.load_data(self.root/'data.csv',['s'])['s']
        origin=v.stamp('2020-01-15T00:00:00Z')
        before=[r['value'] for r in v.history_at(data,origin,self.p['split'])[0]]
        for row in data:
            if row['timestamp']>origin:row['value']+=1000000
        after=[r['value'] for r in v.history_at(data,origin,self.p['split'])[0]]
        self.assertEqual(before,after)

    def test_final_without_selection_blocked(self):
        self.p['phase']='final'
        with self.assertRaises(ValueError):v.validate_protocol(self.p)

    def test_unselected_final_model_rejected(self):
        self.p['phase']='final'
        self.p['final_selection']={'model_spec_hashes':['0'*64],'approval_reference':'test-only',
                                  'locked_at':'2020-01-01T00:00:00Z'}
        self.make_plan('final-plan')
        self.mutate_manifest(lambda m:m.update(protocol_sha256=v.digest(self.p)))
        self.assertEqual(self.score(plan='final-plan')['drift']['status'],'INVALID')

    def test_selected_final_model_scores(self):
        m=v.read_json(self.root/'drift/run.json')
        self.p['phase']='final'
        self.p['final_selection']={'model_spec_hashes':[v.digest(m['model_spec'])],
                                  'approval_reference':'test-only','locked_at':'2020-01-01T00:00:00Z'}
        self.make_plan('final-plan')
        self.mutate_manifest(lambda m:m.update(protocol_sha256=v.digest(self.p)))
        self.assertEqual(self.score(plan='final-plan')['drift']['status'],'ELIGIBLE')

    def test_expanding_sliding_policy(self):
        self.p['split'].update(window='sliding',max_train_size=8)
        self.make_plan('sliding-plan')
        lock,_,origins=v.load_plan(self.root/'sliding-plan')
        self.assertNotEqual(origins[0]['train_start'],origins[-1]['train_start'])

    def test_inference_needs_assumption_review(self):
        self.p['inference'].update(enabled=True,assumptions_reviewed=False)
        with self.assertRaises(ValueError):v.validate_protocol(self.p)

    def test_hac_overlap_minimum(self):
        self.p['inference'].update(enabled=True,assumptions_reviewed=True,hac_lags=0)
        with self.assertRaises(ValueError):v.validate_protocol(self.p)

    def test_forecasts_seed_not_independent_n(self):
        self.p['inference'].update(enabled=True,assumptions_reviewed=True,hac_lags=1,min_origins=20)
        self.make_plan('inf-plan')
        for model in ['naive','drift','seasonal-naive']:
            self.mutate_manifest(lambda m:m.update(protocol_sha256=v.digest(self.p)),model)
        self.mutate_manifest(lambda m:m.update(comparison_to_naive='non_nested'))
        self.score(plan='inf-plan')
        with (self.root/'scores/statistical_tests.csv').open() as handle:stats=list(csv.DictReader(handle))
        drift=[r for r in stats if r['model_id']=='drift']
        self.assertEqual(int(drift[0]['n_origins']),29)
        self.assertEqual(int(drift[0]['family_size']),4)

    def quantile_plan(self):
        self.p['tracks']['history-fixed']['quantile_levels']=[0.1,0.5,0.9]
        self.make_plan('q-plan')
        self.mutate_manifest(lambda m:m.update(protocol_sha256=v.digest(self.p)))
        self.mutate_forecasts(lambda rows:[r.update(quantiles={'0.1':r['point']-2,'0.5':r['point'],'0.9':r['point']+2}) for r in rows])

    def test_quantile_pipeline(self):
        self.quantile_plan()
        self.assertEqual(self.score(plan='q-plan')['drift']['status'],'ELIGIBLE')
        with (self.root/'scores/horizon_metrics.csv').open() as f:rows=list(csv.DictReader(f))
        self.assertTrue(any(r.get('wis') for r in rows if r['model_id']=='drift'))

    def test_quantile_grid_mismatch(self):
        self.quantile_plan()
        self.mutate_forecasts(lambda rows:rows[0]['quantiles'].pop('0.1'))
        self.assertEqual(self.score(plan='q-plan')['drift']['status'],'INVALID')

    def test_median_alias_is_not_a_bypass(self):
        self.quantile_plan()
        def mutate(rows):
            row=rows[0]
            row['quantiles']['0.50']=row['quantiles'].pop('0.5')+1
        self.mutate_forecasts(mutate)
        self.assertEqual(self.score(plan='q-plan')['drift']['status'],'INVALID')

    def test_crossing_quantile_pipeline(self):
        self.quantile_plan()
        self.mutate_forecasts(lambda rows:rows[0]['quantiles'].update({'0.1':1e6}))
        self.assertEqual(self.score(plan='q-plan')['drift']['status'],'INVALID')

    def test_track_change_without_registration_rejected(self):
        self.mutate_manifest(lambda m:m.update(track_id='changed-after-results'))
        self.assertEqual(self.score()['drift']['status'],'INVALID')

    def test_ranks_only_within_track(self):
        self.p['tracks']['another-budget']=copy.deepcopy(self.p['tracks']['history-fixed'])
        self.p['tracks']['another-budget']['budget']='Different predeclared budget'
        next(c for c in self.p['candidates'] if c['model_id']=='drift')['track_id']='another-budget'
        self.make_plan('tracks-plan')
        for model in ['naive','drift','seasonal-naive']:
            self.mutate_manifest(lambda m:m.update(protocol_sha256=v.digest(self.p)),model)
        self.mutate_manifest(lambda m:m.update(track_id='another-budget'))
        result=self.score(plan='tracks-plan')
        self.assertEqual(result['drift']['rank'],1)
        self.assertEqual(sum(r['rank']==1 for r in result.values()),2)

    def test_unknown_pretraining_is_unranked_in_clean_track(self):
        self.p['tracks']['history-fixed'].update(learning_regime='zero_shot',pretraining_policy='documented_disjoint')
        self.make_plan('fm-plan')
        self.mutate_manifest(lambda m:m.update(protocol_sha256=v.digest(self.p)))
        self.mutate_manifest(lambda m:m['audit'].update(pretraining_overlap='unknown'))
        self.assertEqual(self.score(plan='fm-plan')['drift']['status'],'PRETRAINING_UNVERIFIED')

    def test_point_zero_baseline_scale_unranked(self):
        for row in self.data:row['value']=7.0
        self.write_data();self.make_plan('constant-plan')
        paths=[]
        for model in ['naive','drift','seasonal-naive']:
            v.baseline_run(self.root/'constant-plan',self.root/'data.csv',model,self.root/(model+'-constant'))
            paths.append(self.root/(model+'-constant')/'run.json')
        self.assertEqual(self.score(paths,plan='constant-plan')['drift']['status'],'UNDEFINED_BASELINE_SCALE')

    def test_schema_unknown_key_rejected(self):
        self.p['silently_ignored_typo']=1
        with self.assertRaises(jsonschema.ValidationError):v.validate_protocol(self.p)

    def test_nonfinite_json_rejected(self):
        with self.assertRaises(ValueError):v.loads('{"x": 1e999}')

    def test_duplicate_json_keys_rejected(self):
        with self.assertRaises(ValueError):v.loads('{"x":1,"x":2}')

    def test_seasonal_baseline_horizon_wrap(self):
        self.assertEqual(v.predict_baseline([1,2,3,4],[1,2,3,4],'seasonal-naive',2),[3,4,3,4])


class SkillPackageTests(unittest.TestCase):
    def test_frontmatter_and_size(self):
        text=(v.ROOT/'SKILL.md').read_text(encoding='utf-8')
        match=re.match(r'^---\nname: ([a-z0-9-]+)\ndescription: (.+)\n---',text)
        self.assertIsNotNone(match)
        self.assertEqual(match.group(1),v.ROOT.name)
        self.assertLessEqual(len(match.group(1)),64)
        self.assertLessEqual(len(v.loads(match.group(2))),1024)
        self.assertLess(len(text.splitlines()),500)

    def test_agent_metadata(self):
        text=(v.ROOT/'agents/openai.yaml').read_text(encoding='utf-8')
        fields={m.group(1):v.loads(m.group(2)) for m in re.finditer(r'^  ([a-z_]+): (.+)$',text,re.MULTILINE)}
        self.assertEqual(set(fields),{'display_name','short_description','default_prompt'})
        self.assertTrue(25<=len(fields['short_description'])<=64)
        self.assertIn('$validate-time-series',fields['default_prompt'])

    def test_resource_links_resolve(self):
        text=(v.ROOT/'SKILL.md').read_text(encoding='utf-8')
        for relative in re.findall(r'\]\(([^)]+)\)',text):
            self.assertTrue((v.ROOT/relative).is_file(),relative)

    def test_json_schemas_valid(self):
        for name in ['protocol','run']:
            jsonschema.Draft202012Validator.check_schema(v.read_json(v.ROOT/f'assets/{name}.schema.json'))


if __name__=='__main__':
    unittest.main(verbosity=2)
