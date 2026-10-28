"""Constants, file names and plot labels shared by all figures."""

from pathlib import Path

# --------------------------------------------------------------------------
# Input files (place them in the data directory, default ./data)
# --------------------------------------------------------------------------
BUOY_FILE = "Paper_data.csv"          # daily PIRATA 8N38W: Date, Rain, SSS, SST, SOCAT fCO2
BARBADOS_FILE = "BarbadosCO2.txt"     # NOAA GML flask xCO2, Ragged Point (RPB)
SOCAT_FILE = "SOCAT_2023.csv"         # SOCATv2023 subset around the buoy
GLODAP_FILE = "GLODAP_2023.txt"       # GLODAPv2.2022 subset, 3-10N 28-42W
SSS_HIGHRES_FILE = "SSS2.txt"         # optional, high-frequency buoy SSS (Fig. S2)
SST_HIGHRES_FILE = "SST2.txt"         # optional, high-frequency buoy SST (Fig. S2)

DEFAULT_DATA_DIR = Path("data")
DEFAULT_FIG_DIR = Path("figures")
DEFAULT_RESULTS_DIR = Path("results")

# --------------------------------------------------------------------------
# Study period and site
# --------------------------------------------------------------------------
START_YEAR, END_YEAR = 1998, 2018
BUOY_LON, BUOY_LAT = -38.0, 8.0
GLODAP_MAX_DEPTH = 20  # m

# --------------------------------------------------------------------------
# Empirical TA and DIC relationships with SSS
#   TA  = 58.1 * SSS + 265            (Lefevre et al., 2010)
#   DIC = 50.1 * SSS + 198 + 0.9 * (year - 1989)   (Bonou et al., 2016)
# --------------------------------------------------------------------------
A_TA, B_TA, U_TA = 58.1, 265.0, 11.6      # umol/kg, U = uncertainty
A_DIC, B_DIC, U_DIC = 50.1, 198.0, 24.0   # umol/kg
DIC_ANNUAL_INCREASE = 0.9                 # umol/kg/yr
DIC_REFERENCE_YEAR = 1989

# PyCO2SYS options: Millero (2006) carbonic constants, total pH scale,
# KSO4 Dickson (1990) is the PyCO2SYS default.
OPT_K_CARBONIC = 13

# Seasons (paper, Section 2.1): dry = Jan-Jun, wet = Jul-Dec
WET_MONTHS = range(7, 13)

# --------------------------------------------------------------------------
# Plot styling
# --------------------------------------------------------------------------
SEASON_STYLE = {
    # season: (edge colour, trend line style)
    "Dry": ("red", "dashdot"),
    "Wet": ("blue", "dashed"),
}
UMOL = "[μmol kg⁻¹]"
UATM = "[μatm]"
CO2 = "CO₂"

LABELS = {
    "SSS": ("SSS", "[-]"),
    "SST": ("SST", "[°C]"),
    "TA": ("TA", UMOL),
    "DIC": ("DIC", UMOL),
    "pH": ("pH", "[-]"),
    "fCO2": (f"f{CO2}", UATM),
    "nTA": ("nTA", UMOL),
    "nDIC": ("nDIC", UMOL),
    "npH": ("npH", "[-]"),
    "nfCO2": (f"nf{CO2}", UATM),
    "DIC/TA": ("DIC/TA", "[-]"),
    "TA-DIC": ("TA−DIC", UMOL),
}


def axis_label(var: str) -> str:
    name, unit = LABELS[var]
    return f"{name} {unit}"
