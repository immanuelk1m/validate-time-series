#!/usr/bin/env python3
"""Lock an evaluation plan, generate simple baselines, and score forecast ledgers.

The script checks declarations and observable artifacts, not arbitrary model internals.
Use an isolated trusted evaluator for a genuinely hidden final holdout.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
from datetime import datetime, timezone
import csv
import hashlib
import json
import math
import platform
from time import perf_counter
from pathlib import Path
import sys
import tempfile
from typing import Any, Iterable

import jsonschema
import numpy as np

from metrics import dm_hac, holm, point_summary, probabilistic_scores, ratio, scaled_errors

ROOT = Path(__file__).resolve().parents[1]
VERSION = '1.0.0'


def fail(message: str) -> None:
    raise ValueError(message)


def unique_object(pairs: list[tuple]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            fail(f'duplicate JSON key: {key}')
        result[key] = value
    return result


def loads(text: str) -> Any:
    def parse_float(text: str) -> float:
        value = float(text)
        if not math.isfinite(value):
            fail('nonfinite JSON number')
        return value
    return json.loads(text, object_pairs_hook=unique_object, parse_float=parse_float,
                      parse_constant=lambda s: fail(f'nonfinite JSON constant: {s}'))


def read_json(path: Path) -> Any:
    return loads(path.read_text(encoding='utf-8'))


def read_jsonl(path: Path) -> list[dict]:
    rows = [loads(line) for line in path.read_text(encoding='utf-8').splitlines() if line.strip()]
    if any(not isinstance(row, dict) for row in rows):
        fail(f'{path}: each JSONL line must be an object')
    return rows


def dump(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n'


def digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                     separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def file_hash(path: Path) -> str:
    with path.open('rb') as handle:
        return hashlib.file_digest(handle, 'sha256').hexdigest()


def stamp(value: str) -> datetime:
    if not isinstance(value, str):
        fail('timestamp must be a timezone-aware ISO-8601 string')
    dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if dt.tzinfo is None:
        fail(f'timezone required: {value}')
    return dt.astimezone(timezone.utc)


def iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace('+00:00', 'Z')


def number(value: Any, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        fail(f'{name}: finite JSON number required')
    return float(value)


def validate_schema(value: Any, name: str) -> None:
    schema = read_json(ROOT / 'assets' / f'{name}.schema.json')
    jsonschema.Draft202012Validator(schema, format_checker=jsonschema.FormatChecker()).validate(value)


def validate_protocol(p: dict) -> None:
    validate_schema(p, 'protocol')
    split = p['split']
    start, end, target_end, truth_end = map(stamp, [split['origin_start'], split['origin_end'], split['target_end'], p['truth_as_of']])
    if not start <= end < target_end <= truth_end:
        fail('require origin_start <= origin_end < target_end <= truth_as_of')
    maximum = split['max_train_size']
    if split['window'] == 'expanding' and maximum is not None:
        fail('expanding window requires max_train_size=null')
    if split['window'] == 'sliding' and (maximum is None or maximum < split['min_train_size']):
        fail('sliding window requires max_train_size >= min_train_size')
    names = [c['model_id'] for c in p['candidates']]
    if len(set(names)) != len(names):
        fail('candidate model_ids must be unique; name configurations separately')
    for c in p['candidates']:
        if c['track_id'] not in p['tracks']:
            fail(f'candidate has unknown track: {c}')
    for track in p['tracks'].values():
        if track['learning_regime'] == 'from_scratch' and track['pretraining_policy'] != 'not_applicable':
            fail('from_scratch requires not_applicable pretraining policy')
        if track['learning_regime'] != 'from_scratch' and track['pretraining_policy'] == 'not_applicable':
            fail('pretrained models require an explicit pretraining policy')
    inf = p['inference']
    if inf['enabled']:
        if not inf['assumptions_reviewed']:
            fail('inference requires explicit assumptions review')
        if inf['hac_lags'] < math.ceil(max(p['horizons']) / split['stride']) - 1:
            fail('HAC lag below the minimum overlapping-horizon guard; review dependence')
    regimes = p['regimes']
    if len({r['name'] for r in regimes}) != len(regimes) or any(r['name'] == 'overall' for r in regimes):
        fail('regime names must be unique and cannot be overall')
    for r in regimes:
        if stamp(r['start']) > stamp(r['end']):
            fail('regime start is after its end')
    selection = p['final_selection']
    if p['phase'] == 'final' and selection is None:
        fail('final evaluation requires a previously frozen, explicitly approved selection')
    if p['phase'] == 'development' and selection is not None:
        fail('development phase must not carry a final-selection approval')
    if selection and stamp(selection['locked_at']) > datetime.now(timezone.utc):
        fail('selection locked_at is in the future')


def load_data(path: Path, ids: list[str]) -> dict[str, list[dict]]:
    data = defaultdict(list)
    seen = set()
    with path.open(newline='', encoding='utf-8-sig') as handle:
        reader = csv.DictReader(handle)
        if set(reader.fieldnames or []) != {'series_id', 'timestamp', 'available_at', 'value'}:
            fail('data columns must be exactly series_id,timestamp,available_at,value')
        for line, row in enumerate(reader, 2):
            if None in row or any(value is None for value in row.values()):
                fail(f'malformed CSV row {line}')
            t, a = stamp(row['timestamp']), stamp(row['available_at'])
            try:
                value = float(row['value'])
            except ValueError:
                fail(f'invalid value at CSV row {line}')
            if not math.isfinite(value) or a < t:
                fail(f'row {line}: require finite observed value and available_at >= timestamp')
            key = row['series_id'], t, a
            if key in seen:
                fail(f'duplicate observation vintage at row {line}')
            seen.add(key)
            if row['series_id'] in ids:
                data[row['series_id']].append({'timestamp':t, 'available_at':a, 'value':value})
    if set(data) != set(ids):
        fail('one or more requested series are absent')
    calendars = [sorted({r['timestamp'] for r in data[s]}) for s in ids]
    if any(cal != calendars[0] for cal in calendars[1:]):
        fail('bundled planner requires an aligned target calendar; use an external plan adapter for ragged panels')
    return dict(data)


def snapshot(rows: list[dict], origin: datetime) -> dict[datetime, dict]:
    """Latest available vintage of each already observed point, as of the origin."""
    # ponytail: linear vintage scan per origin; use an indexed as-of store for large panels.
    values = {}
    for row in rows:
        t = row['timestamp']
        if t <= origin and row['available_at'] <= origin:
            if t not in values or row['available_at'] > values[t]['available_at']:
                values[t] = row
    return values


def history_at(rows: list[dict], origin: datetime, split: dict) -> tuple[list[dict], list[datetime]]:
    times = sorted({r['timestamp'] for r in rows if r['timestamp'] <= origin})
    if split['window'] == 'sliding':
        times = times[-split['max_train_size']:]
    values = snapshot(rows, origin)
    if len(times) < split['min_train_size'] or not times or times[-1] != origin:
        fail(f'insufficient history at {iso(origin)}')
    if any(t not in values for t in times):
        fail(f'target history unavailable at {iso(origin)}; do not drop or backfill ragged observations')
    return [values[t] for t in times], times


def predict_baseline(history: list[float], horizons: list[int], method: str, period: int) -> list[float]:
    if len(history) < 2:
        fail('baseline requires at least two observations')
    if method == 'naive':
        return [history[-1] for _ in horizons]
    if method == 'drift':
        slope = (history[-1] - history[0]) / (len(history) - 1)
        return [history[-1] + h * slope for h in horizons]
    if method == 'seasonal-naive':
        if len(history) < period:
            fail('seasonal-naive requires at least one complete seasonal cycle')
        return [history[-period + (h - 1) % period] for h in horizons]
    fail(f'unsupported built-in baseline: {method}')


def write_jsonl(path: Path, rows: Iterable[dict]) -> None:
    path.write_text(''.join(json.dumps(r, ensure_ascii=False, allow_nan=False) + '\n' for r in rows), encoding='utf-8')


def write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        path.write_text('', encoding='utf-8')
        return
    fields = list(dict.fromkeys(k for r in rows for k in r))
    with path.open('w', newline='', encoding='utf-8') as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def publish(out: Path, writer: Any) -> None:
    """Publish a new directory only. Never overwrite a previous run or input."""
    if out.exists():
        fail(f'output already exists: {out}; choose a new run directory')
    out.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=out.parent, prefix='.tsv-') as temp:
        stage = Path(temp) / 'result'
        stage.mkdir()
        writer(stage)
        stage.rename(out)


def build_plan(protocol: dict, data: dict[str, list[dict]]) -> tuple[list[dict], list[dict], list[dict]]:
    validate_protocol(protocol)
    split, expected, origins, omitted = protocol['split'], [], [], []
    start, end, target_end = map(stamp, [split['origin_start'], split['origin_end'], split['target_end']])
    horizons = sorted(protocol['horizons'])
    for series in protocol['series_ids']:
        rows = data[series]
        calendar = sorted({r['timestamp'] for r in rows})
        truth = snapshot(rows, stamp(protocol['truth_as_of']))
        candidates = [i for i, t in enumerate(calendar) if start <= t <= end][::split['stride']]
        for i in candidates:
            origin = calendar[i]
            if i < split['min_train_size'] - 1 or i + max(horizons) >= len(calendar) or calendar[i + max(horizons)] > target_end:
                omitted.append({'series_id':series,'origin':iso(origin),'reason':'warmup_or_horizon_outside_locked_grid'})
                continue
            history, times = history_at(rows, origin, split)
            y = [r['value'] for r in history]
            scale_abs, scale_sq = scaled_errors(y, protocol['metrics']['seasonal_period'])
            idx = sum(r['series_id'] == series for r in origins)
            origins.append({'series_id':series,'origin':iso(origin),'horizons':horizons,
                            'target_times':[iso(calendar[i+h]) for h in horizons],
                            'train_start':iso(times[0]),'origin_index':idx})
            for h in horizons:
                target = calendar[i+h]
                if target not in truth:
                    fail(f'truth not available by truth_as_of for {series} {iso(target)}')
                expected.append({'series_id':series,'origin':iso(origin),'target_time':iso(target),
                                 'horizon':h,'origin_index':idx,'y_true':truth[target]['value'],
                                 'y_origin':y[-1],'naive':y[-1], 'scale_abs':scale_abs,'scale_sq':scale_sq,
                                 'regimes':[r['name'] for r in protocol['regimes'] if stamp(r['start']) <= origin <= stamp(r['end'])]})
        if not any(r['series_id'] == series for r in origins):
            fail(f'no valid forecast origins for {series}')
    return expected, origins, omitted


def lock_plan(protocol_path: Path, data_path: Path, out: Path) -> None:
    p = read_json(protocol_path)
    validate_protocol(p)
    expected, origins, omitted = build_plan(p, load_data(data_path, p['series_ids']))
    def writer(stage: Path) -> None:
        write_jsonl(stage / 'expected.jsonl', expected)
        write_jsonl(stage / 'origins.jsonl', origins)
        write_jsonl(stage / 'omitted_origins.jsonl', omitted)
        lock = {'format_version':1, 'engine_version':VERSION, 'protocol':p,
                'protocol_sha256':digest(p), 'data_sha256':file_hash(data_path),
                'expected_sha256':file_hash(stage/'expected.jsonl'),
                'origins_sha256':file_hash(stage/'origins.jsonl'),
                'created_at':iso(datetime.now(timezone.utc)),
                'warning':'Local hashes detect accidental changes; they are not access control or proof of no test peeking.'}
        (stage/'lock.json').write_text(dump(lock),encoding='utf-8')
    publish(out, writer)


def load_plan(path: Path, include_expected: bool = True) -> tuple[dict, list[dict], list[dict]]:
    lock = read_json(path/'lock.json')
    validate_protocol(lock['protocol'])
    if lock['protocol_sha256'] != digest(lock['protocol']):
        fail('protocol hash mismatch')
    for name in (['expected','origins'] if include_expected else ['origins']):
        if file_hash(path/f'{name}.jsonl') != lock[f'{name}_sha256']:
            fail(f'{name} hash mismatch')
    expected = read_jsonl(path/'expected.jsonl') if include_expected else []
    return lock, expected, read_jsonl(path/'origins.jsonl')


def baseline_run(plan: Path, data_path: Path, method: str, out: Path) -> None:
    lock, _, origins = load_plan(plan, include_expected=False)
    p = lock['protocol']
    if file_hash(data_path) != lock['data_sha256']:
        fail('data differs from the locked snapshot')
    registered = next((c for c in p['candidates'] if c['model_id'] == method), None)
    if registered is None:
        fail('baseline must be registered as a candidate before locking')
    track = p['tracks'][registered['track_id']]
    if track['information_set'] != 'target_history_only' or track['learning_regime'] != 'from_scratch' or track['quantile_levels'] or track['refit_policy'] != 'each_origin':
        fail('built-in baselines require a history-only, from-scratch, point-only, each_origin track')
    data = load_data(data_path, p['series_ids'])
    records = []
    inference_seconds = 0.0
    for request in origins:
        origin = stamp(request['origin'])
        history, _ = history_at(data[request['series_id']], origin, p['split'])
        started = perf_counter()
        predictions = predict_baseline([r['value'] for r in history], request['horizons'], method, p['metrics']['seasonal_period'])
        inference_seconds += perf_counter() - started
        available = iso(max(r['available_at'] for r in history))
        for seed in p['seeds']:
            for h, target, value in zip(request['horizons'], request['target_times'], predictions):
                records.append({'series_id':request['series_id'],'origin':request['origin'],
                                'target_time':target,'horizon':h,'seed':seed,'status':'ok','point':value,'quantiles':{},
                                'fit_cutoff':available,'preprocess_cutoff':available,'max_available_at':available})
    spec = {'model_id':method,'model_version':VERSION,'code_sha256':file_hash(Path(__file__)),
            'config':{'seasonal_period':p['metrics']['seasonal_period']},'family':'baseline'}
    def writer(stage: Path) -> None:
        write_jsonl(stage/'forecasts.jsonl',records)
        manifest = {'schema_version':1,'run_id':method,'protocol_sha256':lock['protocol_sha256'],
                    'data_sha256':lock['data_sha256'],'track_id':registered['track_id'],'model_spec':spec,
                    'forecast_file':'forecasts.jsonl',
                    'audit':{'status':'reviewed','evidence':'Built-in as-of history path; source and tests bundled. Not an independent audit.',
                             'pretraining_overlap':'not_applicable'},
                    'runtime':{'training_seconds':0.0,'inference_seconds':inference_seconds,'hardware':f'{platform.system()} {platform.machine()} CPU; baseline arithmetic only'},
                    'comparison_to_naive':'not_assessed'}
        (stage/'run.json').write_text(dump(manifest),encoding='utf-8')
    publish(out, writer)


def forecast_key(row: dict, seeded: bool = False) -> tuple:
    if not isinstance(row.get('series_id'), str):
        fail('series_id must be a string')
    if isinstance(row.get('horizon'), bool) or not isinstance(row.get('horizon'), int):
        fail('horizon must be an integer')
    key = row['series_id'], iso(stamp(row['origin'])), row['horizon']
    if seeded:
        if isinstance(row.get('seed'), bool) or not isinstance(row.get('seed'), int):
            fail('seed must be an integer')
        return key + (row['seed'],)
    return key


def check_forecasts(manifest: dict, rows: list[dict], expected: list[dict], p: dict) -> tuple[list[dict], int]:
    truth = {forecast_key(r):r for r in expected}
    keys = {key+(seed,) for key in truth for seed in p['seeds']}
    seen, successes = set(), []
    levels = p['tracks'][manifest['track_id']]['quantile_levels']
    functional = p['tracks'][manifest['track_id']]['point_functional']
    allowed = {'series_id','origin','target_time','horizon','seed','status','point','quantiles',
               'fit_cutoff','preprocess_cutoff','max_available_at','error'}
    for row in rows:
        if set(row) - allowed:
            fail(f'unrecognized forecast columns: {set(row)-allowed}')
        key = forecast_key(row, seeded=True)
        if key not in keys or key in seen:
            fail('unexpected or duplicate forecast key; do not change the test set or seed list')
        seen.add(key)
        original = truth[key[:3]]
        if iso(stamp(row['target_time'])) != original['target_time']:
            fail('target_time and horizon do not match locked calendar')
        if row['status'] not in ['ok','failed']:
            fail('status must be ok or failed')
        if row['status'] == 'failed':
            if not isinstance(row.get('error'), str) or not row['error'].strip():
                fail('failed forecast must include an error reason')
            continue
        origin = stamp(row['origin'])
        cutoffs = [stamp(row[name]) for name in ['fit_cutoff','preprocess_cutoff','max_available_at']]
        if any(t > origin for t in cutoffs) or max(cutoffs[:2]) > cutoffs[2]:
            fail('future-information cutoff or inconsistent availability declaration')
        value = number(row['point'], 'point')
        quantiles = row.get('quantiles', {})
        if not isinstance(quantiles, dict) or {float(q) for q in quantiles} != set(levels):
            fail('quantile grid differs from the declared track')
        if any(isinstance(v, bool) or not isinstance(v, (int,float)) for v in quantiles.values()):
            fail('quantile values must be numeric')
        prob = probabilistic_scores(original['y_true'], quantiles) if quantiles else {}
        numeric_quantiles = {float(q):v for q,v in quantiles.items()}
        if functional == 'median' and 0.5 in numeric_quantiles and not math.isclose(value, numeric_quantiles[0.5], rel_tol=1e-9, abs_tol=1e-12):
            fail('median track requires point=q0.5')
        with np.errstate(over='raise', invalid='raise'):
            error = original['y_true'] - value
            squared = error*error
        if not math.isfinite(squared):
            fail('overflow in squared loss')
        tolerance = p['metrics']['direction_tolerance']
        direction = lambda x: 0 if abs(x) <= tolerance else (1 if x > 0 else -1)
        da = direction(value-original['y_origin']) == direction(original['y_true']-original['y_origin'])
        successes.append({**original,'seed':row['seed'],'point':value,'ae':abs(error),'se':squared,
                          'scaled_ae':ratio(abs(error), original['scale_abs']) if original['scale_abs'] is not None else None,
                          'scaled_se':ratio(squared, original['scale_sq']) if original['scale_sq'] is not None else None,
                          'direction_correct':int(da),**prob})
    return successes, len(keys)


def summary(rows: list[dict], primary: str) -> dict:
    values = point_summary([r['y_true'] for r in rows],[r['point'] for r in rows])
    base = point_summary([r['y_true'] for r in rows],[r['naive'] for r in rows])
    relative = ratio(values[primary],base[primary])
    ase = [r['scaled_ae'] for r in rows]
    sse = [r['scaled_se'] for r in rows]
    values.update({'oos_naive_skill':None if relative is None else 1-relative,
                   'naive_primary':base[primary],
                   'mase':float(np.mean(ase)) if all(v is not None for v in ase) else None,
                   'rmsse':math.sqrt(float(np.mean(sse))) if all(v is not None for v in sse) else None,
                   'undefined_scaled_rows':sum(v is None for v in ase),
                   'directional_accuracy':float(np.mean([r['direction_correct'] for r in rows])),
                   'n_rows':len(rows),'n_origins':len({r['origin'] for r in rows})})
    for metric in rows[0]:
        if metric.startswith(('pinball_','coverage_','width_','interval_score_')) or metric in ['wis','mean_pinball']:
            values[metric] = float(np.mean([r[metric] for r in rows]))
    return values


def grouped_summary(rows: list[dict], by: list[str], primary: str) -> list[dict]:
    groups = defaultdict(list)
    for r in rows:
        groups[tuple(r[k] for k in by)].append(r)
    return [{**dict(zip(by,key)),**summary(group,primary)} for key, group in sorted(groups.items())]


def infer_model(rows: list[dict], manifest: dict | None, p: dict, model_id: str, complete: bool) -> list[dict]:
    inf = p['inference']
    if not inf['enabled'] or model_id == 'naive':
        return []
    result=[]
    for series in p['series_ids']:
        for h in sorted(p['horizons']):
            subset = [r for r in rows if r['series_id']==series and r['horizon']==h]
            status = None
            if not complete:
                status='incomplete_or_unreviewed_run'
            elif manifest['comparison_to_naive'] != 'non_nested':
                status='nested_or_unassessed_comparison_requires_other_method'
            if status:
                result.append({'model_id':model_id,'series_id':series,'horizon':h,'status':status,'p_value':None})
                continue
            grouped=defaultdict(list)
            for r in subset:
                loss = r['ae'] if p['metrics']['primary']=='mae' else r['se']
                base_loss=abs(r['y_true']-r['naive'])
                if p['metrics']['primary']!='mae':
                    base_loss=base_loss**2
                grouped[r['origin']].append(loss-base_loss)
            d=[float(np.mean(grouped[o])) for o in sorted(grouped)]
            result.append({'model_id':model_id,'series_id':series,'horizon':h,
                           **dm_hac(d,inf['hac_lags'],inf['min_origins'],inf['alpha'])})
    return result


def score_runs(plan: Path, paths: list[Path], out: Path) -> None:
    lock, expected, _ = load_plan(plan)
    p, primary = lock['protocol'], lock['protocol']['metrics']['primary']
    manifests = {}
    for path in paths:
        manifest = read_json(path)
        validate_schema(manifest,'run')
        model_id=manifest['model_spec']['model_id']
        if model_id in manifests:
            fail('multiple runs for a candidate; combine all predeclared seeds in one ledger')
        manifests[model_id]=(manifest,path)
    registered={c['model_id']:c['track_id'] for c in p['candidates']}
    if set(manifests)-set(registered):
        fail('unregistered candidate submitted; create a new protocol version before expanding the cohort')
    leaderboard, horizon_rows, fold_rows, regime_rows, loss_rows, inference, audit_rows = [], [], [], [], [], [], []
    for model_id, track_id in registered.items():
        candidate={'model_id':model_id,'track_id':track_id,'phase':p['phase'],'rank':None,
                   'macro_naive_skill':None,'coverage':0.0,'status':'MISSING_RUN','model_spec_sha256':None}
        manifest, rows, total = None, [], len(expected)*len(p['seeds'])
        try:
            if model_id not in manifests:
                raise ValueError('registered candidate was not submitted')
            manifest,path=manifests[model_id]
            if manifest['track_id']!=track_id:
                fail('track_id differs from the predeclared candidate registry')
            for name in ['protocol_sha256','data_sha256']:
                if manifest[name]!=lock[name]:
                    fail(f'{name} mismatch')
            spec_hash=digest(manifest['model_spec'])
            candidate['model_spec_sha256']=spec_hash
            if p['phase']=='final' and spec_hash not in p['final_selection']['model_spec_hashes']:
                fail('model specification was not included in the frozen final selection')
            overlap=manifest['audit']['pretraining_overlap']
            policy=p['tracks'][track_id]['pretraining_policy']
            if policy=='not_applicable' and overlap!='not_applicable':
                fail('unexpected pretraining history in from-scratch track')
            if policy!='not_applicable' and overlap=='not_applicable':
                fail('pretrained track cannot declare pretraining not applicable')
            rows,total=check_forecasts(manifest,read_jsonl(path.parent/manifest['forecast_file']),expected,p)
            candidate['coverage']=len(rows)/total
            complete=len(rows)==total
            reviewed=manifest['audit']['status']=='reviewed'
            clean=overlap not in ['unknown','overlap'] or (overlap=='unknown' and policy=='unknown_allowed')
            candidate['status']='ELIGIBLE' if complete and reviewed and clean else (
                'INCOMPLETE' if not complete else 'UNREVIEWED' if not reviewed else 'PRETRAINING_UNVERIFIED')
            candidate['pretraining_overlap']=overlap
            candidate['audit_basis']=manifest['audit']['evidence']
            candidate['training_seconds']=manifest['runtime']['training_seconds']
            candidate['inference_seconds']=manifest['runtime']['inference_seconds']
            candidate['hardware']=manifest['runtime']['hardware']
            if rows:
                cells=grouped_summary(rows,['series_id','horizon'],primary)
                skills=[r['oos_naive_skill'] for r in cells]
                if candidate['status']=='ELIGIBLE':
                    if any(s is None for s in skills):
                        candidate['status']='UNDEFINED_BASELINE_SCALE'
                    else:
                        candidate['macro_naive_skill']=float(np.mean(skills))
                horizon_rows.extend({'model_id':model_id,'descriptive_only':candidate['status']!='ELIGIBLE',**r} for r in cells)
                for row in rows:
                    row['fold']=row['origin_index']//p['metrics']['fold_origins']
                folds=grouped_summary(rows,['series_id','horizon','fold'],primary)
                fold_rows.extend({'model_id':model_id,**r} for r in folds)
                finite_skills=[r['oos_naive_skill'] for r in folds if r['oos_naive_skill'] is not None]
                candidate['worst_cell_fold_skill']=min(finite_skills) if finite_skills else None
                candidate['cell_fold_skill_std']=float(np.std(finite_skills)) if finite_skills else None
                candidate['undefined_cell_folds']=sum(r['oos_naive_skill'] is None for r in folds)
                seed_skills=[]
                for seed in p['seeds']:
                    seed_cells=grouped_summary([r for r in rows if r['seed']==seed],['series_id','horizon'],primary)
                    ss=[r['oos_naive_skill'] for r in seed_cells]
                    if len(ss)==len(p['series_ids'])*len(p['horizons']) and all(s is not None for s in ss):
                        seed_skills.append(float(np.mean(ss)))
                candidate['seed_skill_std']=float(np.std(seed_skills)) if len(seed_skills)==len(p['seeds']) else None
                for regime in p['regimes']:
                    subset=[r for r in rows if regime['name'] in r['regimes']]
                    regime_rows.extend({'model_id':model_id,'regime':regime['name'],**r}
                                       for r in grouped_summary(subset,['series_id','horizon'],primary))
                loss_rows.extend({'model_id':model_id,**r} for r in rows)
        except (ValueError, KeyError, TypeError, OSError, OverflowError, FloatingPointError) as error:
            candidate['status']='MISSING_RUN' if model_id not in manifests else 'INVALID'
            candidate['macro_naive_skill']=None
            candidate['error']=str(error)
            rows=[]
        audit_rows.append({'model_id':model_id,'status':candidate['status'],
                           'expected_rows':total,'valid_rows':len(rows),
                           'error':candidate.get('error'),
                           'limitation':'Metadata and output checks do not prove the training code had no leakage.'})
        inference.extend(infer_model(rows,manifest,p,model_id,candidate['status']=='ELIGIBLE'))
        leaderboard.append(candidate)
    for track_id in p['tracks']:
        eligible=sorted([r for r in leaderboard if r['track_id']==track_id and r['status']=='ELIGIBLE'],key=lambda r:-r['macro_naive_skill'])
        previous=None
        for index,row in enumerate(eligible,1):
            if previous is not None and math.isclose(row['macro_naive_skill'],previous['macro_naive_skill'],rel_tol=0,abs_tol=1e-12):
                row['rank']=previous['rank']
            else:
                row['rank']=index
            previous=row
    adjusted=holm([r['p_value'] for r in inference])
    for row,p_holm in zip(inference,adjusted):
        row['p_holm']=p_holm
        row['family_size']=len(inference)
        row['better_than_naive_at_alpha']=bool(p_holm is not None and p_holm<p['inference']['alpha'] and row.get('mean_loss_difference',0)<0)
    def writer(stage: Path) -> None:
        for name,values in [('leaderboard',leaderboard),('horizon_metrics',horizon_rows),('fold_metrics',fold_rows),('regime_metrics',regime_rows),('statistical_tests',inference)]:
            write_csv(stage/f'{name}.csv',values)
        write_jsonl(stage/'losses.jsonl',loss_rows)
        (stage/'audit.json').write_text(dump(audit_rows),encoding='utf-8')
        summary_doc={'engine_version':VERSION,'phase':p['phase'],'benchmark_id':p['benchmark_id'],
                     'protocol_sha256':lock['protocol_sha256'],'data_sha256':lock['data_sha256'],
                     'expected_rows_per_candidate':len(expected)*len(p['seeds']),
                     'leaderboard':leaderboard,'inference_family_size':len(inference),
                     'forecasting_guarantee':False,'automatic_deployment_approval':False,
                     'warning':'Development results select candidates, not unbiased final performance. Final local approvals are declarations, not a secure holdout service.'}
        (stage/'summary.json').write_text(dump(summary_doc),encoding='utf-8')
        provenance={'plan_lock_sha256':file_hash(plan/'lock.json'),
                    'engine_sha256':file_hash(Path(__file__)),'metrics_sha256':file_hash(Path(__file__).with_name('metrics.py')),
                    'submitted_files':[{ 'manifest':str(path),'manifest_sha256':file_hash(path),
                       'forecasts_sha256':file_hash(path.parent/man['forecast_file']) if (path.parent/man['forecast_file']).is_file() else None}
                       for man,path in manifests.values()]}
        (stage/'provenance.json').write_text(dump(provenance),encoding='utf-8')
    publish(out,writer)


def main() -> None:
    parser=argparse.ArgumentParser(description=__doc__)
    commands=parser.add_subparsers(dest='command',required=True)
    command=commands.add_parser('lock',help='Freeze protocol, target snapshot, and expected scoring keys')
    command.add_argument('--protocol',type=Path,required=True)
    command.add_argument('--data',type=Path,required=True)
    command.add_argument('--out',type=Path,required=True)
    command=commands.add_parser('baseline',help='Generate one registered baseline using only as-of history')
    command.add_argument('--plan',type=Path,required=True)
    command.add_argument('--data',type=Path,required=True)
    command.add_argument('--method',choices=['naive','drift','seasonal-naive'],required=True)
    command.add_argument('--out',type=Path,required=True)
    command=commands.add_parser('score',help='Audit submissions and generate within-track descriptive leaderboards')
    command.add_argument('--plan',type=Path,required=True)
    command.add_argument('--runs',type=Path,nargs='+',required=True)
    command.add_argument('--out',type=Path,required=True)
    args=parser.parse_args()
    try:
        if args.command=='lock':
            lock_plan(args.protocol,args.data,args.out)
        elif args.command=='baseline':
            baseline_run(args.plan,args.data,args.method,args.out)
        else:
            score_runs(args.plan,args.runs,args.out)
        print(dump({'status':'completed','output':str(args.out)}),end='')
    except (ValueError,KeyError,TypeError,OSError,jsonschema.ValidationError) as error:
        print(f'VALIDATION_BLOCKED: {error}',file=sys.stderr)
        sys.exit(2)


if __name__=='__main__':
    main()
