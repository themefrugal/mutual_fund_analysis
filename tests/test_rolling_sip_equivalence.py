"""Keep the optimized rolling SIP calculation aligned with the saved reference."""

import numpy as np
import pandas as pd
import pytest

from api.core.rolling import rolling_sip_xirr, rolling_sip_xirr_records
from benchmarks.rolling_sip_reference import rolling_sip_xirr as reference_rolling_sip_xirr


@pytest.mark.parametrize("frequency", ["Monthly", "Weekly", "Daily"])
@pytest.mark.parametrize("missing_dates", [False, True])
def test_rolling_sip_matches_reference(frequency, missing_dates):
    dates = pd.date_range("2020-01-01", "2022-01-31", freq="D")
    navs = pd.DataFrame({"date": dates, "nav": 10 * np.exp(np.linspace(0, 0.4, len(dates)))})
    if missing_dates:
        navs = navs[~navs["date"].isin(pd.to_datetime(["2020-01-31", "2020-02-29", "2021-07-15"]))]
        duplicate = navs.loc[navs["date"].eq(pd.Timestamp("2021-01-01"))].copy()
        duplicate["nav"] *= 1.01
        navs = pd.concat([navs, duplicate], ignore_index=True)

    args = (navs, 1, 1000.0, 7.5, frequency)
    reference = reference_rolling_sip_xirr(*args)
    optimized = rolling_sip_xirr(*args)

    pd.testing.assert_frame_equal(reference[["startDate", "endDate"]], optimized[["startDate", "endDate"]])
    np.testing.assert_allclose(reference["xirr"], optimized["xirr"], rtol=0, atol=1e-8, equal_nan=True)
    records = rolling_sip_xirr_records(*args)
    assert len(records) == len(reference)
    if records:
        assert records[0]["start_date"] == reference.iloc[0]["startDate"].strftime("%Y-%m-%d")


def test_rolling_sip_rejects_unknown_frequency():
    navs = pd.DataFrame({"date": pd.date_range("2020-01-01", periods=2), "nav": [10.0, 11.0]})
    with pytest.raises(ValueError, match="Rolling frequency"):
        rolling_sip_xirr(navs, 1, 1000.0, 0.0, "Yearly")
