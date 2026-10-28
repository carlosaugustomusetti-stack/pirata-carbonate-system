"""Carbonate-system reconstruction from SSS and SST."""

import numpy as np
import pandas as pd
import PyCO2SYS as pyco2

from . import config


# ---------------------------------------------------------------------------
# Time helpers
# ---------------------------------------------------------------------------
def decimal_year(dates: pd.Series) -> pd.Series:
    """Decimal year as 1970 + days since 1970-01-01 / 365.25."""
    days = (pd.to_datetime(dates) - pd.Timestamp("1970-01-01")).dt.total_seconds() / 86400
    return 1970 + days / 365.25


def season(month: int) -> str:
    """Dry season = January-June, wet season = July-December."""
    return "Wet" if month in config.WET_MONTHS else "Dry"


def add_time_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["Decimal date"] = decimal_year(df["Date"])
    df["Season"] = df["Date"].dt.month.map(season)
    return df


# ---------------------------------------------------------------------------
# TA, DIC, pH and fCO2
# ---------------------------------------------------------------------------
def estimate_ta_dic(df: pd.DataFrame) -> pd.DataFrame:
    """TA (Lefevre et al., 2010) and DIC (Bonou et al., 2016) from SSS."""
    df = df.copy()
    years = df["Date"].dt.year.astype(float)
    df["TA"] = config.A_TA * df["SSS"] + config.B_TA
    df["DIC"] = (config.A_DIC * df["SSS"] + config.B_DIC
                 + config.DIC_ANNUAL_INCREASE * (years - config.DIC_REFERENCE_YEAR))
    return df


def co2sys(ta, dic, sss, sst, uncertainty: bool = False) -> dict:
    """Run PyCO2SYS with TA and DIC as the input pair."""
    kwargs = dict(par1=np.asarray(ta, float), par2=np.asarray(dic, float),
                  par1_type=1, par2_type=2,
                  salinity=np.asarray(sss, float), temperature=np.asarray(sst, float),
                  opt_k_carbonic=config.OPT_K_CARBONIC)
    if uncertainty:
        kwargs.update(uncertainty_into=["pH", "fCO2"],
                      uncertainty_from={"par1": config.U_TA, "par2": config.U_DIC})
    return pyco2.sys(**kwargs)


def add_carbonate_system(df: pd.DataFrame) -> pd.DataFrame:
    """Add TA, DIC, pH (total scale), xCO2, pCO2, fCO2, DIC/TA and TA-DIC."""
    df = estimate_ta_dic(df)
    out = co2sys(df["TA"], df["DIC"], df["SSS"], df["SST"])
    df["pH"] = out["pH_total"]
    df["xCO2"] = out["xCO2"]
    df["pCO2"] = out["pCO2"]
    df["fCO2"] = out["fCO2"]
    df["DIC/TA"] = df["DIC"] / df["TA"]
    df["TA-DIC"] = df["TA"] - df["DIC"]
    return df


def mean_uncertainty(df: pd.DataFrame) -> dict:
    """Mean propagated uncertainty of pH and fCO2 from the TA and DIC errors."""
    out = co2sys(df["TA"], df["DIC"], df["SSS"], df["SST"], uncertainty=True)
    return {"u_pH": float(np.nanmean(out["u_pH"])), "u_fCO2": float(np.nanmean(out["u_fCO2"]))}


# ---------------------------------------------------------------------------
# Salinity normalisation (Friis et al., 2003)
# ---------------------------------------------------------------------------
def normalize(var: pd.Series, sss: pd.Series, intercept: float, ref_sss: float) -> pd.Series:
    """nX = (X - X_S=0) * S_ref / S + X_S=0, with a non-zero freshwater end-member."""
    return (var - intercept) * (ref_sss / sss) + intercept


def add_normalized(df: pd.DataFrame, ref_sss: float | None = None) -> tuple[pd.DataFrame, float]:
    """Add nTA, nDIC and the pH / fCO2 recalculated from them.

    The reference salinity defaults to the mean SSS of the record (35.42).
    """
    df = df.dropna(subset=["SSS"]).copy()
    ref_sss = df["SSS"].mean() if ref_sss is None else ref_sss
    df["nTA"] = normalize(df["TA"], df["SSS"], config.B_TA, ref_sss)
    df["nDIC"] = normalize(df["DIC"], df["SSS"], config.B_DIC, ref_sss)
    out = co2sys(df["nTA"], df["nDIC"], df["SSS"], df["SST"])
    df["npH"] = out["pH_total"]
    df["nxCO2"] = out["xCO2"]
    df["npCO2"] = out["pCO2"]
    df["nfCO2"] = out["fCO2"]
    return df, ref_sss


# ---------------------------------------------------------------------------
# Thermal vs non-thermal (biological) control of pCO2 (Takahashi et al., 2002)
# ---------------------------------------------------------------------------
def temperature_biology_ratio(df: pd.DataFrame) -> dict:
    sst_mean = df["SST"].mean()
    pco2_at_mean_t = df["pCO2"] * np.exp(0.0423 * (sst_mean - df["SST"]))
    pco2_thermal = df["pCO2"].mean() * np.exp(0.0423 * (df["SST"] - sst_mean))
    bio = pco2_at_mean_t.max() - pco2_at_mean_t.min()
    temp = pco2_thermal.max() - pco2_thermal.min()
    return {"delta_pCO2_temperature": temp, "delta_pCO2_biology": bio, "T/B": temp / bio}
