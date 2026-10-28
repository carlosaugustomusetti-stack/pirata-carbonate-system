"""One function per figure of de Assis et al. (2024), Front. Mar. Sci. 11:1286960.

Every function takes already-loaded DataFrames and returns a matplotlib
Figure, so figures can be reproduced, tweaked or tested independently.
"""

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from matplotlib.patches import Rectangle
from matplotlib.ticker import MultipleLocator
from scipy.stats import linregress

from . import config
from .config import CO2, UATM, axis_label
from .stats import deseasoned_monthly_means, is_significant

MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------
def _panel_letter(ax, i: int, size: int = 14) -> None:
    ax.text(0.02, 0.98, f"({chr(97 + i)})", transform=ax.transAxes, va="top", ha="left",
            fontsize=size, fontweight="bold")


def _year_axis(ax, rotate: bool = True) -> None:
    ax.xaxis.set_major_locator(MultipleLocator(2))
    if rotate:
        ax.tick_params(axis="x", rotation=45, labelsize=12)


def _trend_line(ax, df, col, color, linestyle="solid") -> None:
    """Regression line with 95% confidence band (seaborn regplot)."""
    d = df[["Decimal date", col]].dropna()
    sns.regplot(x=d["Decimal date"], y=d[col], scatter=False, color=color,
                line_kws={"linestyle": linestyle}, ax=ax)


def season_panel(ax, df: pd.DataFrame, col: str, marker_size: float = 5) -> None:
    """Dry (red) and wet (blue) scatter with seasonal and overall trend lines.

    Trend lines are drawn only when the linear trend is significant (p < 0.05):
    dry = red dash-dot, wet = blue dashed, all data = black solid.
    """
    ax.grid(True, which="both", linestyle="dotted")
    for season, (color, linestyle) in config.SEASON_STYLE.items():
        sub = df[df["Season"] == season]
        d = sub[["Decimal date", col]].dropna()
        ax.scatter(d["Decimal date"], d[col], facecolor="white", edgecolor=color,
                   s=marker_size, label=season)
        if is_significant(sub, col):
            _trend_line(ax, sub, col, color, linestyle)
    if is_significant(df, col):
        _trend_line(ax, df, col, "black")
    ax.set_xlabel("")
    ax.set_ylabel(axis_label(col), fontsize=14)


def season_grid(df: pd.DataFrame, cols, ncols: int = 2, figsize=(12, 12),
                marker_size: float = 5, titles=None) -> plt.Figure:
    nrows = int(np.ceil(len(cols) / ncols))
    fig, axs = plt.subplots(nrows, ncols, figsize=figsize, sharex=True, squeeze=False)
    for i, col in enumerate(cols):
        ax = axs[i // ncols, i % ncols]
        season_panel(ax, df, col, marker_size)
        _year_axis(ax)
        right = ncols > 1 and i % ncols == ncols - 1
        if right:
            ax.yaxis.tick_right()
            ax.yaxis.set_label_position("right")
        ax.legend(loc="lower right" if right else "lower left")
        if titles:
            ax.set_title(titles[i], fontsize=16)
        else:
            _panel_letter(ax, i)
        if i // ncols == nrows - 1:
            ax.set_xlabel("Year", fontsize=14)
    fig.tight_layout()
    return fig


# ---------------------------------------------------------------------------
# Figure 1 - study area
# ---------------------------------------------------------------------------
def fig01_map(socat: pd.DataFrame, glodap: pd.DataFrame) -> plt.Figure:
    import cartopy.crs as ccrs
    import cartopy.feature as cfeature

    proj = ccrs.PlateCarree()
    fig, ax = plt.subplots(figsize=(10, 8), subplot_kw={"projection": proj})
    ax.set_extent([-50, -23, -5, 20], crs=proj)
    ax.add_feature(cfeature.LAND, edgecolor="black", facecolor="lightgray")
    ax.add_feature(cfeature.COASTLINE)
    ax.add_feature(cfeature.BORDERS, linestyle=":")

    ax.scatter(socat["LONGITUDE"], socat["LATITUDE"], facecolor="white", edgecolor="gray",
               s=25, label="SOCAT", transform=proj)
    ax.scatter(glodap["Longitude"], glodap["Latitude"], facecolor="white", edgecolor="blue",
               s=25, label="GLODAP", transform=proj)
    ax.plot(config.BUOY_LON, config.BUOY_LAT, marker="^", markersize=12, markerfacecolor="white",
            markeredgecolor="green", markeredgewidth=2, linestyle="none", label="This study",
            transform=proj)

    # Mean ITCZ position in August (6-10N) and March (0-4N)
    for y0 in (6, 0):
        ax.add_patch(Rectangle((-50, y0), 27, 4, fill=False, edgecolor="red", linewidth=3,
                               linestyle="dashed", transform=proj))
    for x, y, text, bold in [(-43, 2, "NBC", True), (-25, 5, "NECC", True), (-32, 17, "NEC", True),
                             (-25, 7, "ITCZ August", False), (-25, 1, "ITCZ March", False),
                             (-47, -4, "Brazil", True)]:
        ax.text(x, y, text, fontsize=12, fontweight="bold" if bold else "normal",
                ha="center", va="center", transform=proj)

    ax.gridlines(draw_labels=True, linestyle="--")
    ax.legend(loc="upper right")
    return fig


# ---------------------------------------------------------------------------
# Figure 2 - ocean vs atmospheric xCO2
# ---------------------------------------------------------------------------
def fig02_atmosphere(buoy: pd.DataFrame, barbados: pd.DataFrame) -> plt.Figure:
    ocean = buoy.dropna(subset=["Decimal date", "xCO2"])
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.scatter(barbados["time_decimal"], barbados["value"], facecolor="white", edgecolor="blue",
               label="Atmosphere (Ragged Point, Barbados)")
    ax.scatter(ocean["Decimal date"], ocean["xCO2"], facecolor="white", edgecolor="red",
               label="Sea surface (this study)")
    for x, y, ls, label in [(barbados["time_decimal"], barbados["value"], "solid", "Atmospheric trend"),
                            (ocean["Decimal date"], ocean["xCO2"], "dashed", "Ocean trend")]:
        lr = linregress(x, y)
        ax.plot(x, lr.slope * x + lr.intercept, color="black", linestyle=ls,
                label=f"{label} ({lr.slope:.2f} ppm yr⁻¹)")
    ax.set_xlabel("Year", fontsize=14)
    ax.set_ylabel(f"x{CO2} [ppm]", fontsize=14)
    ax.tick_params(labelsize=12)
    ax.legend()
    ax.grid(True)
    fig.tight_layout()
    return fig


# ---------------------------------------------------------------------------
# Figure 3 - monthly climatology
# ---------------------------------------------------------------------------
def _shade_seasons(ax) -> None:
    ax.axvspan(0.5, 6.5, alpha=0.2, color="red")    # dry: Jan-Jun
    ax.axvspan(6.5, 12.5, alpha=0.2, color="blue")  # wet: Jul-Dec
    ax.set_xlim(0.5, 12.5)


def _twin_panel(ax, means, stds, left, right, left_side: bool) -> None:
    m = means.index.to_numpy()
    ax.plot(m, means[left], "rD--", label=left)
    ax.errorbar(m, means[left], yerr=stds[left], fmt="none", color="red", capsize=5)
    ax.set_ylabel(axis_label(left), color="red", fontsize=14)
    ax.tick_params(axis="y", labelcolor="red", labelsize=12)
    ax2 = ax.twinx()
    ax2.plot(m, means[right], "bo-", label=right)
    ax2.errorbar(m, means[right], yerr=stds[right], fmt="none", color="blue", capsize=5)
    ax2.set_ylabel(axis_label(right), color="blue", fontsize=14)
    ax2.tick_params(axis="y", labelcolor="blue", labelsize=12, direction="in")
    side = "left" if left_side else "right"
    ax2.spines[side].set_position(("axes", -0.25 if left_side else 1.2))
    for a in (ax, ax2):
        a.yaxis.set_ticks_position(side)
        a.yaxis.set_label_position(side)
    _shade_seasons(ax)


def fig03_climatology(buoy: pd.DataFrame) -> plt.Figure:
    df = buoy.copy()
    df["Rain"] = df["Rain"].replace(0, np.nan)  # mean rain rate of rainy days
    cols = ["Rain", "SSS", "SST", "TA", "DIC", "pH", "fCO2"]
    grouped = df.groupby(df["Date"].dt.month)[cols]
    means, stds = grouped.mean(), grouped.std()

    fig, axs = plt.subplots(2, 2, figsize=(13, 10))
    ax = axs[0, 0]
    ax.bar(means.index, means["Rain"], color="blue", alpha=0.6)
    ax.errorbar(means.index, means["Rain"], yerr=stds["Rain"], fmt="none", color="black", capsize=5)
    ax.set_ylabel("Rain [mm h⁻¹]", fontsize=14)
    _shade_seasons(ax)

    _twin_panel(axs[0, 1], means, stds, "SST", "SSS", left_side=False)
    _twin_panel(axs[1, 0], means, stds, "TA", "DIC", left_side=True)
    _twin_panel(axs[1, 1], means, stds, "pH", "fCO2", left_side=False)

    for i, ax in enumerate(axs.ravel()):
        ax.grid(True)
        ax.text(0.03, 0.97, f"({chr(97 + i)})", transform=ax.transAxes, fontsize=16, va="top")
        ax.set_xticks(range(1, 13))
        if i < 2:
            ax.set_xticklabels([])
        else:
            ax.set_xticklabels(MONTHS, fontsize=12)
            ax.set_xlabel("Month", fontsize=14)
    fig.tight_layout()
    return fig


# ---------------------------------------------------------------------------
# Figure 4 - comparison with GLODAP
# ---------------------------------------------------------------------------
def fig04_glodap(buoy: pd.DataFrame, glodap: pd.DataFrame) -> plt.Figure:
    b = buoy[buoy["Decimal date"].between(config.START_YEAR, config.END_YEAR)]
    fig, axs = plt.subplots(1, 3, figsize=(16, 5.5))
    for i, (ax, col) in enumerate(zip(axs, ["TA", "DIC", "pH"])):
        ax.scatter(b["Decimal date"], b[col], facecolor="white", edgecolor="green", alpha=0.5,
                   label="This study")
        ax.scatter(glodap["Decimal date"], glodap[col], facecolor="orange", edgecolor="black",
                   alpha=0.5, label="GLODAP")
        _trend_line(ax, b, col, "black", "solid")
        _trend_line(ax, glodap, col, "black", "dashed")
        ax.set_xlabel("Year", fontsize=14)
        ax.set_ylabel(axis_label(col), fontsize=14)
        ax.set_title(f"({chr(97 + i)})", fontsize=16)
        ax.xaxis.set_major_locator(MultipleLocator(5))
        ax.legend()
        ax.grid(True)
    fig.tight_layout()
    return fig


# ---------------------------------------------------------------------------
# Figure 5 - comparison with SOCAT / CARIOCA
# ---------------------------------------------------------------------------
def fig05_socat(buoy: pd.DataFrame, socat: pd.DataFrame) -> plt.Figure:
    fig, axs = plt.subplots(1, 3, figsize=(17, 5.5))

    ax = axs[0]
    ax.scatter(buoy["Decimal date"], buoy["fCO2"], facecolor="white", edgecolor="green",
               alpha=0.5, label="This study")
    ship, carioca = socat[~socat["CARIOCA"]], socat[socat["CARIOCA"]]
    ax.scatter(ship["Decimal date"], ship["FCO2_RECOMMENDED"], facecolor="white",
               edgecolor="orange", alpha=0.5, label="SOCAT")
    ax.scatter(carioca["Decimal date"], carioca["FCO2_RECOMMENDED"], facecolor="white",
               edgecolor="black", alpha=0.5, label="SOCAT (CARIOCA buoy)")
    _trend_line(ax, buoy, "fCO2", "black", "solid")
    _trend_line(ax, socat, "FCO2_RECOMMENDED", "black", "dashed")
    ax.set_xlabel("Year", fontsize=14)
    ax.set_ylabel(f"f{CO2} {UATM}", fontsize=14)

    # (b) calculated minus observed, matched by day ("SOCAT fCO2" column)
    ax = axs[1]
    for season, (color, _) in config.SEASON_STYLE.items():
        s = buoy[buoy["Season"] == season]
        ax.scatter(s["Decimal date"], s["fCO2"] - s["SOCAT fCO2"], facecolor="white",
                   edgecolor=color, alpha=0.5, label=season)
    ax.axhline(0, color="black", linestyle="--")
    ax.set_xlabel("Year", fontsize=14)
    ax.set_ylabel(f"Difference {UATM}", fontsize=14)

    # (c) calculated vs observed with 1:1 line
    ax = axs[2]
    for season, (color, _) in config.SEASON_STYLE.items():
        s = buoy[buoy["Season"] == season]
        ax.scatter(s["SOCAT fCO2"], s["fCO2"], color=color, alpha=0.7, s=20, label=season)
    lims = [buoy["SOCAT fCO2"].min(), buoy["SOCAT fCO2"].max()]
    ax.plot(lims, lims, "k-", label="1:1")
    ax.set_xlabel(f"Observed f{CO2} {UATM}", fontsize=14)
    ax.set_ylabel(f"Calculated f{CO2} {UATM}", fontsize=14)

    for i, ax in enumerate(axs):
        ax.set_title(f"({chr(97 + i)})", fontsize=16)
        ax.legend()
        ax.grid(True)
    fig.tight_layout()
    return fig


# ---------------------------------------------------------------------------
# Figure 6 - time series of the six variables
# ---------------------------------------------------------------------------
def fig06_timeseries(buoy: pd.DataFrame) -> plt.Figure:
    return season_grid(buoy, ["SSS", "SST", "TA", "DIC", "pH", "fCO2"])


# ---------------------------------------------------------------------------
# Figure 7 - de-seasoned pH and fCO2 trends
# ---------------------------------------------------------------------------
def fig07_deseasoned(buoy: pd.DataFrame, deseasoned: dict | None = None) -> plt.Figure:
    """``deseasoned`` maps 'pH'/'fCO2' to a DataFrame with 'Decimal date' and
    'deseasoned' columns; computed from the daily data when not given."""
    deseasoned = deseasoned or {c: deseasoned_monthly_means(buoy, c) for c in ["pH", "fCO2"]}
    fig, axs = plt.subplots(1, 2, figsize=(13, 5))
    for i, (ax, col, unit) in enumerate(zip(axs, ["pH", "fCO2"], ["[-]", UATM])):
        d = deseasoned[col]
        ax.scatter(buoy["Decimal date"], buoy[col], facecolor="white", edgecolor="blue", s=12,
                   label="This study (daily)")
        ax.scatter(d["Decimal date"], d["deseasoned"], color="red", edgecolor="darkred", s=25,
                   label="De-seasoned monthly means")
        lr = linregress(d["Decimal date"], d["deseasoned"])
        ax.plot(d["Decimal date"], lr.slope * d["Decimal date"] + lr.intercept, color="black",
                label=f"De-seasoned trend ({lr.slope:.4f} yr⁻¹)")
        name = "pH" if col == "pH" else f"f{CO2}"
        ax.set_title(f"({chr(97 + i)}) {name}", fontsize=16)
        ax.set_xlabel("Year", fontsize=14)
        ax.set_ylabel(unit, fontsize=14)
        ax.legend()
        ax.grid(True, which="both", linestyle="dotted")
    fig.tight_layout()
    return fig


# ---------------------------------------------------------------------------
# Figure 8 - salinity-normalised variables
# ---------------------------------------------------------------------------
def fig08_normalized(normalized: pd.DataFrame, ref_sss: float) -> plt.Figure:
    titles = ["(a) Normalized total alkalinity",
              "(b) Normalized dissolved inorganic carbon",
              "(c) pH from normalized TA and DIC",
              f"(d) f{CO2} from normalized TA and DIC"]
    fig = season_grid(normalized, ["nTA", "nDIC", "npH", "nfCO2"], figsize=(12, 12),
                      marker_size=20, titles=titles)
    fig.suptitle(f"Reference salinity = {ref_sss:.2f}", fontsize=13, y=1.01)
    return fig


# ---------------------------------------------------------------------------
# Figure 9 - daily heatmaps (year x day of year)
# ---------------------------------------------------------------------------
def fig09_heatmaps(buoy: pd.DataFrame) -> plt.Figure:
    df = buoy.assign(Year=buoy["Date"].dt.year, Day=buoy["Date"].dt.dayofyear)
    cols = ["SSS", "SST", "TA", "DIC", "pH", "fCO2"]
    month_starts = [0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334]
    fig, axes = plt.subplots(3, 2, figsize=(15, 10))
    for i, col in enumerate(cols):
        ax = axes[i // 2, i % 2]
        grid = df.pivot_table(index="Year", columns="Day", values=col, aggfunc="mean")
        grid = grid.reindex(columns=range(1, 367))
        sns.heatmap(grid, cmap="coolwarm", cbar_kws={"label": axis_label(col)}, ax=ax)
        _panel_letter(ax, i)
        ax.set_xticks(month_starts)
        if i // 2 == 2:
            ax.set_xticklabels(MONTHS, rotation=0)
            ax.set_xlabel("Month", fontsize=14)
        else:
            ax.set_xticklabels([])
            ax.set_xlabel("")
        if i % 2 == 0:
            ax.set_ylabel("Year", fontsize=14)
        else:
            ax.set_ylabel("")
            ax.tick_params(axis="y", left=False, labelleft=False)
        ax.tick_params(axis="both", labelsize=12)
        ax.add_patch(Rectangle((0, 0), 1, 1, transform=ax.transAxes, color="black",
                               linewidth=2, fill=False))
        ax.grid(True, linestyle="--", linewidth=0.5, color="black")
    fig.tight_layout()
    return fig


# ---------------------------------------------------------------------------
# Figure 10 - DIC/TA ratio and TA-DIC (buffer capacity)
# ---------------------------------------------------------------------------
def fig10_buffer(buoy: pd.DataFrame) -> plt.Figure:
    return season_grid(buoy, ["DIC/TA", "TA-DIC"], ncols=1, figsize=(12, 10), marker_size=20)


# ---------------------------------------------------------------------------
# Supplementary figures
# ---------------------------------------------------------------------------
def figS1_data_count(buoy: pd.DataFrame) -> plt.Figure:
    counts = (buoy.groupby(buoy["Date"].dt.year)[["SST", "SSS", "Rain"]].count()
              .rename_axis("Year").reset_index()
              .melt(id_vars="Year", var_name="Variable", value_name="N"))
    fig, ax = plt.subplots(figsize=(11, 6))
    sns.barplot(data=counts, x="Year", y="N", hue="Variable",
                palette={"SST": "red", "SSS": "green", "Rain": "blue"}, ax=ax)
    ax.set_ylabel("Number of daily values")
    ax.tick_params(axis="x", rotation=45)
    ax.legend(loc="upper right")
    fig.tight_layout()
    return fig


def figS2_highres(sss: pd.DataFrame, sst: pd.DataFrame) -> plt.Figure:
    fig, axs = plt.subplots(2, 1, figsize=(10, 12), sharex=True)
    for i, (ax, df, col, unit) in enumerate(zip(axs, [sss, sst], ["SSS", "SST"], ["[-]", "[°C]"])):
        daily = df.resample("D", on="DateTime")[col].mean()
        ax.plot(df["DateTime"], df[col], "o", color="blue", ms=3, label=f"{col} values")
        ax.plot(daily.index, daily, "^", color="red", ms=3, label="Daily means")
        ax.set_ylabel(f"{col} {unit}", fontsize=14)
        ax.text(0.03, 0.97, f"({chr(97 + i)})", transform=ax.transAxes, fontsize=16, va="top")
        ax.legend(fontsize=13)
        ax.grid(True)
    axs[1].set_xlabel("Date", fontsize=14)
    fig.tight_layout()
    return fig


def figS3_annual_means(buoy: pd.DataFrame) -> plt.Figure:
    cols = ["SSS", "SST", "TA", "DIC", "pH", "fCO2"]
    g = buoy.groupby(buoy["Date"].dt.year)[cols]
    means, stds = g.mean(), g.std()
    fig, axs = plt.subplots(3, 2, figsize=(12, 12), sharex=True)
    for i, col in enumerate(cols):
        ax = axs[i // 2, i % 2]
        ax.grid(True, which="both", linestyle="dotted")
        m = means[col].dropna()
        ax.plot(m.index, m, color="black", linewidth=2)
        ax.scatter(m.index, m, facecolor="white", edgecolor="black", zorder=3)
        ax.errorbar(m.index, m, yerr=stds[col].loc[m.index], fmt="none", color="red", capsize=5)
        lr = linregress(m.index, m)
        if lr.pvalue < 0.05:
            sns.regplot(x=m.index.to_numpy(), y=m.to_numpy(), scatter=False, color="purple", ax=ax)
        ax.set_ylabel(axis_label(col), fontsize=13)
        _panel_letter(ax, i)
        _year_axis(ax)
        if i >= 4:
            ax.set_xlabel("Year", fontsize=13)
    fig.tight_layout()
    return fig


def figS4_anomalies(buoy: pd.DataFrame) -> plt.Figure:
    cols = ["SSS", "SST", "TA", "DIC", "pH", "fCO2"]
    df = buoy.dropna(subset=cols).copy()
    for c in cols:
        df[c] = df[c] - df[c].mean()
    fig = season_grid(df, cols)
    for ax, c in zip(fig.axes, cols):
        ax.set_ylabel(f"{config.LABELS[c][0]} anomaly {config.LABELS[c][1]}", fontsize=14)
    return fig
