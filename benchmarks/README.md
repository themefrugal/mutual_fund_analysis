# Rolling SIP performance reference

`rolling_sip_legacy.py` preserves the original pre-optimization calculation,
including its early redemption on the last contribution date.
`rolling_sip_reference.py` is the straightforward calculation corrected to redeem
after the full requested duration. The production implementation is
`api/core/rolling.py`. Run the deterministic comparison from the repository root:

```powershell
python -m benchmarks.benchmark_rolling_sip --history-years 20 --window-years 7
```

The benchmark checks every start date, end date, missing XIRR, and XIRR value.
It requires an absolute XIRR difference below `1e-8` percentage points.
`tests/test_rolling_sip_equivalence.py` also checks sparse and duplicate NAV rows.

On Windows with Python 3.14, pandas 3.0.3, NumPy 2.5.0, and pyxirr 0.10.8,
the 20-year synthetic history with seven-year SIP windows produced:

| Start frequency | Windows | Reference | Optimized | Speedup | Maximum XIRR difference |
| --- | ---: | ---: | ---: | ---: | ---: |
| Monthly | 156 | 1.683 s | 0.065 s | 25.77× | 2.84e-14 percentage points |
| Weekly | 678 | 7.528 s | 0.184 s | 41.01× | 3.20e-14 percentage points |
| Daily | 4,748 | 42.426 s | 0.601 s | 70.55× | 4.80e-14 percentage points |

Timings vary by machine and run. The benchmark uses a fixed random seed and
the same NAV history for both implementations.
