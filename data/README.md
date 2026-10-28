# Input data

The data files are not included in this repository because of their size. Download them from the sources below and save them in this folder with these names, or point the scripts at another folder with `--data`. `.gitignore` keeps them out of git.

| File | Content | Source | Needed for |
|---|---|---|---|
| `Paper_data.csv` | Daily PIRATA 8°N 38°W record. Columns: `Date` (m/d/Y), `Rain` (mm h⁻¹), `SSS`, `SST` (°C), `SOCAT fCO2` (µatm, SOCAT daily value matched to the buoy, blank otherwise). Row 1 = names, row 2 = units. | [PIRATA, NOAA PMEL](https://www.pmel.noaa.gov/gtmba/pirata) | all figures |
| `BarbadosCO2.txt` | Atmospheric flask xCO₂ at Ragged Point (RPB), NOAA GML text format | [NOAA GML](https://gml.noaa.gov/dv/data/) | Fig. 2 |
| `SOCAT_2023.csv` | SOCATv2023 fCO₂ around the buoy (columns `EXPOCODE`, `DATETIME`, `LONGITUDE`, `LATITUDE`, `FCO2_RECOMMENDED`) | [SOCAT](https://socat.info) | Figs. 1, 5 |
| `GLODAP_2023.txt` | GLODAPv2.2022 subset, 3–10°N 28–42°W, ODV spreadsheet (tab separated) | [GLODAP](https://www.glodap.info) | Figs. 1, 4 |
| `SSS2.txt`, `SST2.txt` | High-frequency buoy SSS and SST (optional) | PIRATA | Fig. S2 |

Missing values in `Paper_data.csv` can be blank cells or Excel `#VALUE!` errors. The file also has TA, DIC, pH, xCO2, pCO2, fCO2 and Season columns calculated in Excel; the code ignores them and recalculates everything with PyCO2SYS.

All sources are publicly available. Please cite them as described on their websites (Bourlès et al., 2019 for PIRATA; Lauvset et al., 2022 for GLODAPv2.2022; Bakker et al., 2016 for SOCAT).
