"""Compare rolling SIP implementations on deterministic calendar-day NAV history.

Run from the repository root with: python -m benchmarks.benchmark_rolling_sip
"""

from __future__ import annotations

import argparse
import time

import numpy as np
import pandas as pd

from benchmarks.rolling_sip_reference import rolling_sip_xirr as reference
from api.core.rolling import rolling_sip_xirr as candidate


def nav_history(years: int) -> pd.DataFrame:
    dates = pd.date_range("2010-01-01", periods=round(years * 365.25), freq="D")
    rng = np.random.default_rng(1729)
    nav = 10 * np.exp(np.cumsum(rng.normal(0.00025, 0.008, len(dates))))
    return pd.DataFrame({"date": dates, "nav": nav})


def timed(fn, *args):
    start = time.perf_counter()
    result = fn(*args)
    return result, time.perf_counter() - start


def compare(base: pd.DataFrame, optimized: pd.DataFrame) -> float:
    pd.testing.assert_frame_equal(base[["startDate", "endDate"]], optimized[["startDate", "endDate"]])
    left = base["xirr"].to_numpy(dtype=float)
    right = optimized["xirr"].to_numpy(dtype=float)
    np.testing.assert_array_equal(np.isnan(left), np.isnan(right))
    if not len(left):
        return 0.0
    error = float(np.nanmax(np.abs(left - right)))
    np.testing.assert_allclose(left, right, rtol=0, atol=1e-8, equal_nan=True)
    return error


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--history-years", type=int, default=8)
    parser.add_argument("--window-years", type=int, default=3)
    parser.add_argument("--baseline-only", action="store_true")
    args = parser.parse_args()

    navs = nav_history(args.history_years)
    for frequency in ("Monthly", "Weekly", "Daily"):
        inputs = (navs, args.window_years, 1000.0, 5.0, frequency)
        base, baseline_seconds = timed(reference, *inputs)
        if args.baseline_only:
            print(f"{frequency:7} windows={len(base):5} reference={baseline_seconds:.3f}s", flush=True)
            continue
        fast, optimized_seconds = timed(candidate, *inputs)
        max_error = compare(base, fast)
        print(
            f"{frequency:7} windows={len(base):5} reference={baseline_seconds:.3f}s "
            f"optimized={optimized_seconds:.3f}s speedup={baseline_seconds / optimized_seconds:.2f}x "
            f"max_xirr_error={max_error:.3g} percentage points",
            flush=True,
        )


if __name__ == "__main__":
    main()
