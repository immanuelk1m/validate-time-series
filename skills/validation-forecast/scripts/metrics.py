"""Small, explicit forecast metrics. Undefined denominators remain None."""
from __future__ import annotations

import math
from statistics import NormalDist
from typing import Sequence

import numpy as np


def finite_vector(values: Sequence[float], name: str) -> np.ndarray:
    array = np.asarray(values, dtype=float)
    if array.ndim != 1 or not array.size or not np.all(np.isfinite(array)):
        raise ValueError(f'{name}: expected a nonempty finite vector')
    return array


def ratio(numerator: float, denominator: float) -> float | None:
    if denominator <= 0 or not math.isfinite(denominator):
        return None
    value = numerator / denominator
    return value if math.isfinite(value) else None


def scaled_errors(history: Sequence[float], period: int) -> tuple[float | None, float | None]:
    y = finite_vector(history, 'history')
    if period < 1:
        raise ValueError('seasonal_period must be positive')
    if len(y) <= period:
        return None, None
    with np.errstate(over='raise', invalid='raise'):
        delta = y[period:] - y[:-period]
        return float(np.mean(np.abs(delta))), float(np.mean(delta ** 2))


def point_summary(actual: Sequence[float], predicted: Sequence[float]) -> dict:
    y, p = finite_vector(actual, 'actual'), finite_vector(predicted, 'predicted')
    if y.shape != p.shape:
        raise ValueError('actual and predicted shapes differ')
    with np.errstate(over='raise', invalid='raise'):
        error = y - p
        mse = float(np.mean(error ** 2))
        return {'mae': float(np.mean(np.abs(error))), 'mse': mse,
                'rmse': math.sqrt(mse), 'bias_me': float(np.mean(error))}


def probabilistic_scores(actual: float, quantiles: dict[str, float]) -> dict:
    """Use paired central quantiles for interval scores; never label WIS as CRPS."""
    if not math.isfinite(actual) or not quantiles:
        raise ValueError('actual must be finite and quantiles nonempty')
    qs = sorted((float(q), float(value)) for q, value in quantiles.items())
    if len({q for q, _ in qs}) != len(qs):
        raise ValueError('duplicate numeric quantile levels')
    if any(not 0 < q < 1 or not math.isfinite(v) for q, v in qs):
        raise ValueError('invalid quantile level or value')
    if any(a[1] > b[1] for a, b in zip(qs, qs[1:])):
        raise ValueError('crossing quantiles; do not silently sort values')
    result = {}
    lookup = dict(qs)
    pinballs = []
    intervals = []
    for q, value in qs:
        e = actual - value
        pin = max(q * e, (q - 1) * e)
        result[f'pinball_q{q:g}'] = pin
        pinballs.append(pin)
        upper_q = next((x for x in lookup if math.isclose(x, 1 - q, abs_tol=1e-12)), None)
        if q < 0.5 and upper_q is not None:
            lower, upper, alpha = value, lookup[upper_q], 2 * q
            score = upper - lower + 2 / alpha * max(lower - actual, 0) + 2 / alpha * max(actual - upper, 0)
            level = f'{1-alpha:g}'
            result[f'coverage_{level}'] = float(lower <= actual <= upper)
            result[f'width_{level}'] = upper - lower
            result[f'interval_score_{level}'] = score
            intervals.append((alpha, score))
    result['mean_pinball'] = float(np.mean(pinballs))
    # WIS only for a complete symmetric central grid plus the median.
    if 0.5 in lookup and len(qs) == 2 * len(intervals) + 1:
        result['wis'] = (0.5 * abs(actual - lookup[0.5]) + sum(a / 2 * s for a, s in intervals)) / (len(intervals) + 0.5)
    return result


def dm_hac(differences: Sequence[float], lags: int, min_origins: int = 40, alpha: float = 0.05) -> dict:
    """Large-sample DM-style normal test with Bartlett HAC. Not Clark-West/HLN."""
    if not 0 < alpha < 1:
        raise ValueError('alpha must lie strictly between zero and one')
    d = finite_vector(differences, 'loss differences')
    n, mean = len(d), float(np.mean(d))
    base = {'n_origins': n, 'mean_loss_difference': mean, 'hac_lags': lags,
            'statistic': None, 'p_value': None, 'mean_difference_ci_lower':None,
            'mean_difference_ci_upper':None, 'confidence_level':1-alpha}
    if not isinstance(lags, int) or isinstance(lags, bool) or lags < 0:
        raise ValueError('hac lags must be a nonnegative integer')
    if n < max(min_origins, 2 * lags + 2):
        return {**base, 'status': 'insufficient_origins'}
    if np.all(d == 0):
        return {**base, 'statistic': 0.0, 'p_value': 1.0, 'status': 'identical_losses'}
    z = d - mean
    variance = float(np.dot(z, z) / n)
    for lag in range(1, lags + 1):
        variance += 2 * (1 - lag / (lags + 1)) * float(np.dot(z[lag:], z[:-lag]) / n)
    if not math.isfinite(variance) or variance <= np.finfo(float).eps * max(float(np.mean(d*d)), 1e-300):
        return {**base, 'status': 'degenerate_long_run_variance'}
    standard_error = math.sqrt(variance / n)
    statistic = mean / standard_error
    critical = NormalDist().inv_cdf(1-alpha/2)
    return {**base, 'statistic': statistic, 'p_value': math.erfc(abs(statistic) / math.sqrt(2)),
            'mean_difference_ci_lower':mean-critical*standard_error,
            'mean_difference_ci_upper':mean+critical*standard_error,
            'status': 'asymptotic_diagnostic'}


def holm(pvalues: Sequence[float | None]) -> list[float | None]:
    """Keep untestable planned hypotheses in the family conservatively as p=1."""
    if any(p is not None and (not math.isfinite(p) or not 0 <= p <= 1) for p in pvalues):
        raise ValueError('p-values must lie in [0, 1]')
    m = len(pvalues)
    adjusted = [None] * m
    running = 0.0
    for rank, i in enumerate(sorted(range(m), key=lambda j: 1.0 if pvalues[j] is None else pvalues[j])):
        p = 1.0 if pvalues[i] is None else pvalues[i]
        running = max(running, min(1.0, (m - rank) * p))
        if pvalues[i] is not None:
            adjusted[i] = running
    return adjusted
