#!/usr/bin/env python3
"""End-to-end synthetic demonstration; never interpreted as market-model evidence."""
from __future__ import annotations

import argparse
import csv
from datetime import datetime, timedelta, timezone
import math
from pathlib import Path
import random

from tsvalidate import ROOT, baseline_run, dump, iso, lock_plan, read_json, score_runs


def demo(out: Path) -> None:
    if out.exists():
        raise ValueError(f'output exists: {out}')
    out.mkdir(parents=True)
    rng = random.Random(73)
    start = datetime(2020,1,5,tzinfo=timezone.utc)
    rows=[]
    random_walk=100.0
    for i in range(240):
        when=iso(start+timedelta(weeks=i))
        random_walk += rng.gauss(0,1)
        for series,value in [('seasonal',100+0.08*i+5*math.sin(2*math.pi*i/13)+rng.gauss(0,0.3)),('random-walk',random_walk)]:
            rows.append({'series_id':series,'timestamp':when,'available_at':when,'value':value})
    with (out/'data.csv').open('w',newline='',encoding='utf-8') as handle:
        writer=csv.DictWriter(handle,fieldnames=['series_id','timestamp','available_at','value'])
        writer.writeheader()
        writer.writerows(rows)
    protocol=read_json(ROOT/'assets/protocol.example.json')
    (out/'protocol.json').write_text(dump(protocol),encoding='utf-8')
    lock_plan(out/'protocol.json',out/'data.csv',out/'plan')
    runs=[]
    for method in ['naive','drift','seasonal-naive']:
        baseline_run(out/'plan',out/'data.csv',method,out/method)
        runs.append(out/method/'run.json')
    score_runs(out/'plan',runs,out/'evaluation')
    print(f'SYNTHETIC DEMO: {out / "evaluation/summary.json"}')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path,required=True)
    demo(parser.parse_args().out)
