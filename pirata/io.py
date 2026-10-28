"""Loaders for the buoy data and the comparison datasets.

Each loader returns a tidy DataFrame with a ``Date`` (datetime) column, a
``Decimal date`` column and, where relevant, a ``Season`` column.
"""

from pathlib import Path

import numpy as np
import pandas as pd

from . import config
from .carbonate import add_time_columns


def _find_header_line(path: Path, contains: str, default: int | None = None,
                      encoding: str = "latin-1") -> int:
    """Return the 0-based index of the first line containing ``contains``.

    Falls back to ``default`` (the fixed number of header lines in the
    original files) when nothing matches.
    """
    with open(path, encoding=encoding) as f:
        for i, line in enumerate(f):
            if contains in line:
                return i
    if default is not None:
        return default
    raise ValueError(f"Could not find the header line ({contains!r}) in {path}")


def _first_line_not_starting_with(path: Path, prefix: str, encoding: str = "latin-1") -> int:
    with open(path, encoding=encoding) as f:
        for i, line in enumerate(f):
            if not line.startswith(prefix):
                return i
    raise ValueError(f"No data found in {path}")


# ---------------------------------------------------------------------------
# PIRATA buoy (8N 38W)
# ---------------------------------------------------------------------------
def load_buoy(data_dir: Path) -> pd.DataFrame:
    """Daily PIRATA data (TA, DIC, pH... columns in the file are recalculated).

    The CSV has the column names in the first row and the units in the second
    row (skipped). Missing values are blanks or Excel ``#VALUE!`` errors.
    """
    path = Path(data_dir) / config.BUOY_FILE
    buoy = pd.read_csv(path, skiprows=[1], encoding="latin-1",
                       na_values=["#VALUE!", " ", ""])
    buoy["Date"] = pd.to_datetime(buoy["Date"], format="%m/%d/%Y")
    for col in ["Rain", "SSS", "SST", "SOCAT fCO2"]:
        if col in buoy:
            buoy[col] = pd.to_numeric(buoy[col], errors="coerce")
    return add_time_columns(buoy)


def load_highres(data_dir: Path) -> tuple[pd.DataFrame, pd.DataFrame] | None:
    """High-frequency SSS and SST records (optional, for Fig. S2)."""
    s_path = Path(data_dir) / config.SSS_HIGHRES_FILE
    t_path = Path(data_dir) / config.SST_HIGHRES_FILE
    if not (s_path.exists() and t_path.exists()):
        return None
    sss = pd.read_csv(s_path, sep="\t", na_values=-9.999, dtype={"HHMM": str})
    sst = pd.read_csv(t_path, sep="\t", na_values=-9.999, dtype={"HHMMSS": str})
    sss["DateTime"] = pd.to_datetime(sss["YYYYMMDD"].astype(str) + sss["HHMM"], format="%Y%m%d%H%M")
    sst["DateTime"] = pd.to_datetime(sst["YYYYMMDD"].astype(str) + sst["HHMMSS"], format="%Y%m%d%H%M%S")
    return sss, sst


# ---------------------------------------------------------------------------
# Atmospheric xCO2 at Ragged Point, Barbados (NOAA GML flask data)
# ---------------------------------------------------------------------------
BARBADOS_COLUMNS = [
    "site_code", "year", "month", "day", "hour", "minute", "second", "datetime",
    "time_decimal", "air_sample_container_id", "value", "value_unc", "latitude",
    "longitude", "altitude", "elevation", "intake_height", "method", "event_number",
    "instrument", "analysis_datetime", "qcflag",
]


def load_barbados(data_dir: Path) -> pd.DataFrame:
    path = Path(data_dir) / config.BARBADOS_FILE
    # Header lines start with "#"; the column-name line starts with "site_code"
    df = pd.read_csv(path, sep=r"\s+", comment="#", header=None,
                     names=BARBADOS_COLUMNS, encoding="latin-1")
    df = df[df["site_code"] != "site_code"]
    df[["time_decimal", "value"]] = df[["time_decimal", "value"]].apply(pd.to_numeric, errors="coerce")
    df = df.replace(-999.99, np.nan).dropna(subset=["time_decimal", "value"])
    return df


# ---------------------------------------------------------------------------
# SOCATv2023
# ---------------------------------------------------------------------------
def load_socat(data_dir: Path) -> pd.DataFrame:
    path = Path(data_dir) / config.SOCAT_FILE
    header = _find_header_line(path, "EXPOCODE,", default=64)
    socat = pd.read_csv(path, skiprows=header, encoding="latin-1")
    socat["Date"] = pd.to_datetime(socat["DATETIME"], format="%d-%b-%Y %H:%M")
    socat["FCO2_RECOMMENDED"] = pd.to_numeric(socat["FCO2_RECOMMENDED"], errors="coerce")
    socat.loc[socat["FCO2_RECOMMENDED"] < -1e30, "FCO2_RECOMMENDED"] = np.nan  # SOCAT bad flag
    socat = socat.dropna(subset=["FCO2_RECOMMENDED"])
    # Expocodes starting with 357F are the CARIOCA sensor on the PIRATA buoy
    socat["CARIOCA"] = socat["EXPOCODE"].astype(str).str.startswith("357F")
    return add_time_columns(socat)


# ---------------------------------------------------------------------------
# GLODAPv2.2022 (ODV spreadsheet export, tab separated)
# ---------------------------------------------------------------------------
GLODAP_RENAME = {
    "ALKALI [UMOL/KG]": "TA",
    "TCARBN [UMOL/KG]": "DIC",
    "pH~_T [p,T,S]": "pH",
    "DEPTH [M]": "Depth",
    "Latitude [degrees_north]": "Latitude",
    "Longitude [degrees_east]": "Longitude",
}


def load_glodap(data_dir: Path, max_depth: float = config.GLODAP_MAX_DEPTH,
                years: tuple[int, int] = (config.START_YEAR, config.END_YEAR)) -> pd.DataFrame:
    """GLODAP samples shallower than ``max_depth`` within ``years``."""
    path = Path(data_dir) / config.GLODAP_FILE
    # ODV spreadsheet: comment lines start with "//", then the column header
    header = _first_line_not_starting_with(path, "//")
    glodap = pd.read_csv(path, skiprows=header, sep="\t", encoding="latin-1")
    # Station metadata (cruise, date, position...) is only written on the
    # first row of each station: carry it down to every sample.
    glodap.iloc[:, :19] = glodap.iloc[:, :19].ffill()
    glodap = glodap.rename(columns=GLODAP_RENAME)
    glodap["Date"] = pd.to_datetime(glodap["yyyy-mm-ddThh:mm:ss.sss"], format="%Y-%m-%dT%H:%M:%S")
    for col in ["TA", "DIC", "pH", "Depth", "Latitude", "Longitude"]:
        glodap[col] = pd.to_numeric(glodap[col], errors="coerce")
    glodap["Longitude"] = ((glodap["Longitude"] + 180) % 360) - 180  # 0-360 -> -180-180
    glodap = add_time_columns(glodap)
    keep = (glodap["Depth"] <= max_depth) & glodap["Decimal date"].between(years[0], years[1])
    return glodap.loc[keep].copy()


# ---------------------------------------------------------------------------
# Optional: de-seasoned monthly means exported from the original analysis
# ---------------------------------------------------------------------------
def load_deseasoned(data_dir: Path) -> dict | None:
    """Read ``<var>_deseasoned_monthly_means.csv`` for pH and fCO2 if both exist."""
    out = {}
    for var in ["pH", "fCO2"]:
        path = Path(data_dir) / f"{var}_deseasoned_monthly_means.csv"
        if not path.exists():
            return None
        df = pd.read_csv(path)
        df["Date"] = pd.to_datetime(df["date"], format="%Y-%m-%d")
        df["deseasoned"] = df[f"deseasoned_monthly_mean_{var}"]
        df["Decimal date"] = 1970 + (df["Date"] - pd.Timestamp("1970-01-01")).dt.days / 365.25
        out[var] = df
    return out
