#!/usr/bin/env python3
"""Score existing forecast ledgers against an existing lock; never replan or fit."""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

import jsonschema
import tsvalidate as v


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan', type=Path, required=True)
    parser.add_argument('--runs', type=Path, nargs='+', required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    try:
        v.score_runs(args.plan, args.runs, args.out)
        print(v.dump({'status': 'SCORED', 'output': str(args.out)}), end='')
    except (ValueError, KeyError, TypeError, OSError, jsonschema.ValidationError) as error:
        print(f'VALIDATION_BLOCKED: {error}', file=sys.stderr)
        sys.exit(2)


if __name__ == '__main__':
    main()
