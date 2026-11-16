"""Trend statistics (pure Python, no scipy): OLS, Sen's slope, Mann-Kendall."""
import math
from itertools import combinations
from statistics import mean, median, stdev


def normal_cdf(z: float) -> float:
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))


def t_critical_95(df: int) -> float:
    """Two-sided 95% Student-t critical value (Cornish-Fisher expansion)."""
    z = 1.959964
    df = max(df, 1)
    return z + (z**3 + z) / (4 * df) + (5 * z**5 + 16 * z**3 + 3 * z) / (96 * df**2)


class TrendAnalyzer:
    """Computes the trend statistics the analysis charts display."""

    MIN_POINTS = 4

    def analyze(self, xs: list[float], ys: list[float]) -> dict:
        n = len(xs)
        if n != len(ys) or n < self.MIN_POINTS:
            raise ValueError(f"Need at least {self.MIN_POINTS} data points, got {n}")

        mx, my = mean(xs), mean(ys)
        sxx = sum((x - mx) ** 2 for x in xs)
        syy = sum((y - my) ** 2 for y in ys)
        sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
        lin_slope = sxy / sxx if sxx else 0.0
        lin_intercept = my - lin_slope * mx
        pearson = sxy / math.sqrt(sxx * syy) if sxx and syy else 0.0

        sen_slope, sen_intercept = self._sen(xs, ys)
        s, z, tau, p = self._mann_kendall(ys)

        # 95% confidence band for the OLS line
        residual_ss = sum((y - (lin_intercept + lin_slope * x)) ** 2 for x, y in zip(xs, ys))
        s_err = math.sqrt(residual_ss / (n - 2)) if n > 2 else 0.0
        t_crit = t_critical_95(n - 2)
        trend_line = []
        for x in xs:
            fit = lin_intercept + lin_slope * x
            half = t_crit * s_err * math.sqrt(1 / n + (x - mx) ** 2 / sxx) if sxx else 0.0
            trend_line.append({"x": x, "ols": fit, "sen": sen_intercept + sen_slope * x,
                               "ci_low": fit - half, "ci_high": fit + half})

        std = stdev(ys)
        if p < 0.001:
            level = "p < 0.001"
        elif p < 0.01:
            level = "p < 0.01"
        elif p < 0.05:
            level = "p < 0.05"
        else:
            level = "Not Significant"
        direction = "Stable" if level == "Not Significant" else ("Increasing" if sen_slope > 0 else "Decreasing")

        return {
            "n": n, "mean": my, "std_dev": std, "latest_value": ys[-1],
            "latest_z_score": (ys[-1] - my) / std if std else 0.0,
            "linear_slope_per_year": lin_slope, "linear_intercept": lin_intercept,
            "sen_slope_per_year": sen_slope, "sen_intercept": sen_intercept,
            "r_squared": pearson**2, "pearson_r": pearson,
            "mann_kendall_s": s, "mann_kendall_z": z, "kendall_tau": tau, "p_value": p,
            "is_significant": level != "Not Significant", "significance_level": level,
            "direction": direction, "trend_line": trend_line,
        }

    @staticmethod
    def _sen(xs: list[float], ys: list[float]) -> tuple[float, float]:
        slopes = [(ys[j] - ys[i]) / (xs[j] - xs[i])
                  for i, j in combinations(range(len(xs)), 2) if xs[j] != xs[i]]
        slope = median(slopes) if slopes else 0.0
        return slope, median(y - slope * x for x, y in zip(xs, ys))

    @staticmethod
    def _mann_kendall(ys: list[float]) -> tuple[int, float, float, float]:
        n = len(ys)
        s = 0
        for i, j in combinations(range(n), 2):
            d = ys[j] - ys[i]
            s += (d > 0) - (d < 0)
        ties: dict[float, int] = {}
        for y in ys:
            ties[y] = ties.get(y, 0) + 1
        tie_term = sum(t * (t - 1) * (2 * t + 5) for t in ties.values() if t > 1)
        var = (n * (n - 1) * (2 * n + 5) - tie_term) / 18
        if var <= 0 or s == 0:
            z = 0.0
        else:
            z = (s - 1) / math.sqrt(var) if s > 0 else (s + 1) / math.sqrt(var)
        p = 2 * (1 - normal_cdf(abs(z)))
        tau = s / (n * (n - 1) / 2)
        return s, z, tau, p
