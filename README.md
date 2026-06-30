# mutual_fund_analysis

Analysis of Indian equity mutual funds — IRR calculation for SIP, SWP, STP, and lumpsum investments.

## Features

- **NAV history** — fetch and chart any fund's daily NAV from [mfapi.in](https://mfapi.in)
- **Lumpsum CAGR** — rolling CAGR distribution across all start dates
- **SIP XIRR** — point-in-time XIRR for a given SIP start date and duration
- **Rolling SIP XIRR** — slide a fixed-duration SIP window across the full NAV history and visualise the XIRR distribution (histogram + time-series)
- **SWP** — Systematic Withdrawal Plan simulation
- **STP** — Systematic Transfer Plan between two funds
- **Fund comparison** — overlay NAV and CAGR for multiple funds

## Tech stack

| Layer | Technology |
|---|---|
| Streamlit app | `app/app.py` |
| FastAPI backend | `api/` |
| Next.js frontend | `web/` |
| XIRR engine | Python (default) · Haskell (optional, see below) |

## Running locally

```bash
pip install -r requirements.txt
streamlit run app/app.py
```

## Rolling SIP XIRR engine

The rolling XIRR feature has two backends controlled by a single flag at the top of `app/app.py`:

```python
USE_HASKELL_ENGINE = False   # True → Haskell binary, False → pure Python
```

### Python backend (default)

No extra setup needed. Works on all platforms including Render. Uses a pure-Python Newton-Raphson XIRR solver — fast enough for typical NAV histories (10–30 years, ~60–300 windows).

### Haskell backend (optional, Windows)

Produces identical results ~10× faster for very long histories. Requires:

1. Install [GHCup](https://www.haskell.org/ghcup/) — installs GHC and Cabal
2. Build the binary:
   ```bash
   cd engine
   cabal build --builddir=D:\build\rolling-sip-xirr
   ```
3. Copy the output `.exe` to `engine/bin/rolling-sip-xirr.exe`
4. Set `USE_HASKELL_ENGINE = True` in `app/app.py`

The binary is excluded from version control (`.gitignore`). The Haskell source lives in `engine/app/Main.hs`.

## Deployment (Render)

The app is deployed as a Streamlit service on [Render](https://render.com). The Python XIRR backend (`USE_HASKELL_ENGINE = False`) works out of the box — no Haskell toolchain required.
