"""Statistics reported in the paper, written as CSV files to ./results.

    python make_tables.py [--data data] [--out results]

Outputs
    summary_stats.csv        mean, std, median, min, max (all / dry / wet)
    normality.csv            Anderson-Darling test
    season_test.csv          Wilcoxon-Mann-Whitney dry vs wet
    trends.csv               linear + Mann-Kendall trends (all / dry / wet)
    trends_normalized.csv    same for salinity-normalised variables
    trends_deseasoned.csv    trends of de-seasoned monthly means
    comparison_glodap_socat.csv  Mann-Whitney p-values vs GLODAP and SOCAT
    misc.txt                 uncertainties, T/B ratio, xCO2 trends, fCO2 bias
"""

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import linregress

from pirata import config, io
from pirata.carbonate import (add_carbonate_system, add_normalized, mean_uncertainty,
                              temperature_biology_ratio)
from pirata.stats import (compare_datasets, deseasoned_monthly_means, normality_table,
                          season_test, summary_stats, trend_table)

VARS = ["Rain", "SSS", "SST", "TA", "DIC", "pH", "xCO2", "pCO2", "fCO2"]
TREND_VARS = ["SSS", "SST", "TA", "DIC", "pH", "xCO2", "pCO2", "fCO2", "DIC/TA", "TA-DIC"]


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--data", type=Path, default=config.DEFAULT_DATA_DIR)
    p.add_argument("--out", type=Path, default=config.DEFAULT_RESULTS_DIR)
    args = p.parse_args()
    out = args.out
    out.mkdir(parents=True, exist_ok=True)

    buoy = add_carbonate_system(io.load_buoy(args.data))
    no_zero_rain = buoy.assign(Rain=buoy["Rain"].replace(0, np.nan))

    summary_stats(no_zero_rain, VARS).round(4).to_csv(out / "summary_stats.csv")
    normality_table(buoy, VARS[1:]).to_csv(out / "normality.csv")
    season_test(buoy, VARS).to_csv(out / "season_test.csv")
    trend_table(buoy, TREND_VARS).to_csv(out / "trends.csv")

    norm, ref_sss = add_normalized(buoy)
    trend_table(norm, ["nTA", "nDIC", "npH", "nxCO2", "npCO2", "nfCO2"]).to_csv(out / "trends_normalized.csv")

    rows = []
    for col in ["SSS", "SST", "TA", "DIC", "pH", "fCO2"]:
        d = deseasoned_monthly_means(buoy, col)
        lr = linregress(d["Decimal date"], d["deseasoned"])
        rows.append({"variable": col, "n_months": len(d), "slope": lr.slope, "std_err": lr.stderr,
                     "r2": lr.rvalue ** 2, "p_value": lr.pvalue})
    pd.DataFrame(rows).set_index("variable").to_csv(out / "trends_deseasoned.csv")

    lines = [f"Reference salinity for normalisation: {ref_sss:.3f}"]
    lines += [f"Mean propagated uncertainty {k}: {v:.4f}" for k, v in mean_uncertainty(buoy).items()]
    lines += [f"{k}: {v:.3f}" for k, v in temperature_biology_ratio(buoy).items()]

    # Comparison datasets (skipped if a file is missing)
    try:
        glodap = io.load_glodap(args.data)
        socat = io.load_socat(args.data)
        b = buoy[buoy["Decimal date"].between(config.START_YEAR, config.END_YEAR)]
        comp = []
        for col, other, ocol in [("TA", glodap, "TA"), ("DIC", glodap, "DIC"), ("pH", glodap, "pH"),
                                 ("fCO2", socat, "FCO2_RECOMMENDED")]:
            row = {"variable": col, "reference": "GLODAP" if other is glodap else "SOCAT",
                   "n": other[ocol].notna().sum(), "p_all": compare_datasets(b[col], other[ocol])}
            for s in ("Dry", "Wet"):
                o = other[other["Season"] == s][ocol]
                row[f"n_{s.lower()}"] = o.notna().sum()
                row[f"p_{s.lower()}"] = compare_datasets(b.loc[b["Season"] == s, col], o)
                row[f"median_ref_{s.lower()}"] = o.median()
            comp.append(row)
        pd.DataFrame(comp).set_index("variable").to_csv(out / "comparison_glodap_socat.csv")
        trend_table(glodap, ["TA", "DIC", "pH"], by_season=False).to_csv(out / "trends_glodap.csv")
        trend_table(socat, ["FCO2_RECOMMENDED"], by_season=False).to_csv(out / "trends_socat.csv")
    except FileNotFoundError as err:
        lines.append(f"GLODAP/SOCAT comparison skipped: {err.filename} not found")

    if "SOCAT fCO2" in buoy:
        for name, mask in [("All", slice(None)), ("Dry", buoy["Season"] == "Dry"), ("Wet", buoy["Season"] == "Wet")]:
            d = (buoy["fCO2"] - buoy["SOCAT fCO2"])[mask].dropna()
            lines.append(f"fCO2 calculated - SOCAT ({name}): n={len(d)}, mean={d.mean():.1f}, "
                         f"overestimated {100 * (d > 0).mean():.1f}%, underestimated {100 * (d < 0).mean():.1f}%")

    try:
        atm = io.load_barbados(args.data)
        ocean = buoy.dropna(subset=["xCO2"])
        a = linregress(atm["time_decimal"], atm["value"])
        o = linregress(ocean["Decimal date"], ocean["xCO2"])
        lines.append(f"Atmospheric xCO2 trend (Barbados): {a.slope:.3f} +/- {a.stderr:.3f} ppm/yr")
        lines.append(f"Sea-surface xCO2 trend (this study): {o.slope:.3f} +/- {o.stderr:.3f} ppm/yr")
    except FileNotFoundError:
        lines.append("Barbados file not found: atmospheric trend skipped")

    (out / "misc.txt").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))
    print(f"\nTables written to {out}/")


if __name__ == "__main__":
    main()
