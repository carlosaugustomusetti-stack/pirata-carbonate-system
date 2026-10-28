"""Reproduce the figures of de Assis et al. (2024), Front. Mar. Sci. 11:1286960.

Usage:
    python make_figures.py                      # all figures
    python make_figures.py --only 3 6 S1        # selected figures
    python make_figures.py --data path/to/data --out figures --format pdf
"""

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from pirata import config, figures, io  # noqa: E402
from pirata.carbonate import add_carbonate_system, add_normalized  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--data", type=Path, default=config.DEFAULT_DATA_DIR, help="folder with the input files")
    parser.add_argument("--out", type=Path, default=config.DEFAULT_FIG_DIR, help="output folder")
    parser.add_argument("--only", nargs="+", help="figure ids, e.g. 1 2 6 S1")
    parser.add_argument("--format", default="png", help="png, pdf, svg, jpg ...")
    parser.add_argument("--dpi", type=int, default=300)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    buoy = add_carbonate_system(io.load_buoy(args.data))
    cache: dict = {}

    def socat():
        cache.setdefault("socat", io.load_socat(args.data))
        return cache["socat"]

    def glodap():
        cache.setdefault("glodap", io.load_glodap(args.data))
        return cache["glodap"]

    def normalized():
        cache.setdefault("norm", add_normalized(buoy))
        return cache["norm"]

    jobs = {
        "1": ("fig01_study_area", lambda: figures.fig01_map(socat(), glodap())),
        "2": ("fig02_xco2_ocean_vs_atmosphere", lambda: figures.fig02_atmosphere(buoy, io.load_barbados(args.data))),
        "3": ("fig03_monthly_climatology", lambda: figures.fig03_climatology(buoy)),
        "4": ("fig04_glodap_comparison", lambda: figures.fig04_glodap(buoy, glodap())),
        "5": ("fig05_socat_comparison", lambda: figures.fig05_socat(buoy, socat())),
        "6": ("fig06_time_series", lambda: figures.fig06_timeseries(buoy)),
        "7": ("fig07_deseasoned_trends", lambda: figures.fig07_deseasoned(buoy, io.load_deseasoned(args.data))),
        "8": ("fig08_normalized", lambda: figures.fig08_normalized(*normalized())),
        "9": ("fig09_heatmaps", lambda: figures.fig09_heatmaps(buoy)),
        "10": ("fig10_dic_ta_buffer", lambda: figures.fig10_buffer(buoy)),
        "S1": ("figS1_data_count", lambda: figures.figS1_data_count(buoy)),
        "S2": ("figS2_highres_vs_daily", lambda: figures.figS2_highres(*io.load_highres(args.data))),
        "S3": ("figS3_annual_means", lambda: figures.figS3_annual_means(buoy)),
        "S4": ("figS4_anomalies", lambda: figures.figS4_anomalies(buoy)),
    }

    selected = [s.upper() for s in args.only] if args.only else list(jobs)
    for key in selected:
        name, make = jobs[key]
        path = args.out / f"{name}.{args.format}"
        try:
            fig = make()
            fig.savefig(path, dpi=args.dpi, bbox_inches="tight")
        except FileNotFoundError as err:
            print(f"[skip] Figure {key}: missing input file ({err.filename})")
            continue
        except TypeError:
            if key == "S2":
                print("[skip] Figure S2: high-resolution SSS/SST files not found")
                continue
            raise
        except OSError as err:  # e.g. cartopy cannot download coastlines offline
            print(f"[fail] Figure {key}: {err}")
            plt.close("all")
            continue
        plt.close(fig)
        print(f"[ok]   Figure {key}: {path}")


if __name__ == "__main__":
    main()
