"""Offline tests for the trend statistics and archive binning."""
import math
from datetime import date, timedelta

from app.analysis.archive import ArchiveService
from app.analysis.stats import TrendAnalyzer, normal_cdf, t_critical_95


def test_normal_cdf_and_t_critical():
    assert abs(normal_cdf(1.96) - 0.975) < 1e-3
    assert abs(t_critical_95(10) - 2.228) < 0.02  # textbook value
    assert abs(t_critical_95(30) - 2.042) < 0.01


def test_perfect_increasing_trend():
    xs = list(range(2000, 2010))
    ys = [2 * (x - 2000) + 5 for x in xs]
    r = TrendAnalyzer().analyze(xs, ys)
    assert abs(r["linear_slope_per_year"] - 2) < 1e-9 and abs(r["sen_slope_per_year"] - 2) < 1e-9
    assert r["mann_kendall_s"] == 45 and abs(r["mann_kendall_z"] - 44 / math.sqrt(125)) < 1e-9
    assert r["p_value"] < 0.001 and r["direction"] == "Increasing" and abs(r["r_squared"] - 1) < 1e-9


def test_flat_noise_is_not_significant():
    xs = list(range(2000, 2012))
    ys = [1, 3, 2, 3, 1, 2, 3, 1, 2, 3, 2, 1]
    r = TrendAnalyzer().analyze(xs, ys)
    assert r["significance_level"] == "Not Significant" and r["direction"] == "Stable"


def test_too_few_points_rejected():
    try:
        TrendAnalyzer().analyze([1, 2, 3], [1, 2, 3])
        assert False
    except ValueError:
        pass


def _daily(start_year, end_year):
    days, t, d = [], [], date(start_year, 1, 1)
    while d <= date(end_year, 12, 31):
        days.append(d.isoformat())
        t.append(10 + 0.5 * (d.year - start_year))  # +0.5 °C per year
        d += timedelta(days=1)
    n = len(days)
    return {"time": days, "temperature_2m_mean": t, "precipitation_sum": [2.0] * n, "snowfall_sum": [0.1] * n,
            "wind_speed_10m_max": [8.0] * n, "shortwave_radiation_sum": [15.0] * n,
            "et0_fao_evapotranspiration": [3.0] * n}


def test_annual_and_quarterly_binning():
    daily = _daily(2000, 2005)
    annual = ArchiveService.aggregate(daily, "annual")
    assert [b["year"] for b in annual] == [2000, 2001, 2002, 2003, 2004, 2005]
    assert abs(annual[0]["precip_sum"] - 2.0 * 366) < 1e-6  # 2000 is a leap year
    quarterly = ArchiveService.aggregate(daily, "quarterly")
    assert len(quarterly) == 24 and quarterly[1]["x"] == 2000.25
    series = ArchiveService.variable_series(annual, "moisture_balance")
    assert abs(series[1]["value"] - (2.0 - 3.0) * 365) < 1e-6


def test_anomaly_uses_early_baseline_and_partial_year_dropped():
    daily = _daily(2000, 2005)
    keep = len(daily["time"]) - 200  # chop most of 2005
    daily = {k: v[:keep] for k, v in daily.items()}
    annual = ArchiveService.aggregate(daily, "annual")
    assert annual[-1]["year"] == 2004  # 2005 incomplete -> dropped
    anomaly = ArchiveService.variable_series(annual, "temp_anomaly")
    assert abs(anomaly[0]["value"] - (-0.5)) < 1e-6  # baseline = mean of first 3 bins (10, 10.5, 11)=10.5
