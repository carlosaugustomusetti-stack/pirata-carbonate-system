"""Trend tests, seasonal comparisons and de-seasoning."""

import numpy as np
import pandas as pd
import pymannkendall as mk
from scipy.stats import anderson, linregress, mannwhitneyu


def _xy(df: pd.DataFrame, col: str, x: str = "Decimal date"):
    d = df[[x, col]].dropna()
    return d[x].to_numpy(float), d[col].to_numpy(float)


MK_MAX_N = 10_000  # Mann-Kendall needs O(n^2) memory; skipped for larger samples


def linear_trend(df: pd.DataFrame, col: str, x: str = "Decimal date") -> dict:
    """Ordinary least-squares trend (units per year) and Mann-Kendall test."""
    xs, ys = _xy(df, col, x)
    lr = linregress(xs, ys)
    out = {"n": len(ys), "slope": lr.slope, "std_err": lr.stderr, "intercept": lr.intercept,
           "r2": lr.rvalue ** 2, "p_value": lr.pvalue,
           "mk_trend": None, "mk_p_value": float("nan"), "mk_tau": float("nan")}
    if len(ys) <= MK_MAX_N:
        m = mk.original_test(ys[np.argsort(xs)])
        out.update(mk_trend=m.trend, mk_p_value=m.p, mk_tau=m.Tau)
    return out


def is_significant(df: pd.DataFrame, col: str, alpha: float = 0.05) -> bool:
    xs, ys = _xy(df, col)
    return len(ys) > 2 and linregress(xs, ys).pvalue < alpha


def trend_table(df: pd.DataFrame, cols, by_season: bool = True) -> pd.DataFrame:
    """Trends for all data and, optionally, for each season."""
    groups = {"All": df}
    if by_season:
        groups.update({s: g for s, g in df.groupby("Season")})
    rows = [{"variable": c, "period": name, **linear_trend(g, c)}
            for name, g in groups.items() for c in cols]
    return pd.DataFrame(rows).set_index(["variable", "period"])


def season_test(df: pd.DataFrame, cols) -> pd.DataFrame:
    """Wilcoxon-Mann-Whitney test between dry and wet season values."""
    rows = []
    for c in cols:
        dry = df.loc[df["Season"] == "Dry", c].dropna()
        wet = df.loc[df["Season"] == "Wet", c].dropna()
        stat, p = mannwhitneyu(dry, wet, alternative="two-sided")
        rows.append({"variable": c, "median_dry": dry.median(), "median_wet": wet.median(),
                     "U": stat, "p_value": p, "different": p < 0.05})
    return pd.DataFrame(rows).set_index("variable")


def compare_datasets(a: pd.Series, b: pd.Series) -> float:
    """Two-sided Mann-Whitney p-value between two samples (NaNs dropped)."""
    return mannwhitneyu(a.dropna(), b.dropna(), alternative="two-sided").pvalue


def normality_table(df: pd.DataFrame, cols) -> pd.DataFrame:
    """Anderson-Darling test for normality (5% critical value)."""
    rows = []
    for c in cols:
        x = df[c].dropna()
        try:  # SciPy >= 1.17
            res = anderson(x, method="interpolate")
            normal = res.pvalue >= 0.05
        except TypeError:  # older SciPy: compare with the 5% critical value
            res = anderson(x)
            normal = res.statistic < res.critical_values[list(res.significance_level).index(5.0)]
        rows.append({"variable": c, "A2": res.statistic, "normal_5pct": normal})
    return pd.DataFrame(rows).set_index("variable")


def summary_stats(df: pd.DataFrame, cols) -> pd.DataFrame:
    """Mean, standard deviation, median, min and max for all data and per season."""
    frames = {"All": df, **{s: g for s, g in df.groupby("Season")}}
    out = {name: g[cols].agg(["count", "mean", "std", "median", "min", "max"]).T
           for name, g in frames.items()}
    return pd.concat(out, names=["period", "variable"])


def deseasoned_monthly_means(df: pd.DataFrame, col: str) -> pd.DataFrame:
    """De-season a daily series with monthly climatology anomalies (Sutton et al., 2022).

    1. monthly means of the daily data
    2. climatology = mean of each calendar month over all years
    3. de-seasoned = monthly mean - climatology(month) + mean of the climatology
    """
    monthly = df.set_index("Date")[col].resample("MS").mean().dropna().to_frame("monthly_mean")
    clim = monthly.groupby(monthly.index.month)["monthly_mean"].mean()
    monthly["climatology"] = monthly.index.month.map(clim).to_numpy()
    monthly["deseasoned"] = monthly["monthly_mean"] - monthly["climatology"] + clim.mean()
    monthly = monthly.reset_index().rename(columns={"index": "Date"})
    days = (monthly["Date"] - pd.Timestamp("1970-01-01")).dt.days
    monthly["Decimal date"] = 1970 + days / 365.25
    return monthly
