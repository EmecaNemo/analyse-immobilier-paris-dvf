"""Télécharge les fichiers DVF géolocalisés de Paris (département 75) depuis data.gouv.fr.

Usage :
    python src/telecharger.py                   # années 2021 à 2025
    python src/telecharger.py --annees 2024 2025
"""

import argparse
from pathlib import Path

import requests

URL = "https://files.data.gouv.fr/geo-dvf/latest/csv/{annee}/departements/75.csv.gz"
RAW_DIR = Path("data/raw")


def download(annee: int) -> Path:
    path = RAW_DIR / f"dvf_75_{annee}.csv.gz"
    if path.exists():
        print(f"{path} déjà présent")
        return path
    response = requests.get(URL.format(annee=annee), timeout=120)
    response.raise_for_status()
    path.write_bytes(response.content)
    print(f"{path} ({len(response.content) / 1e6:.1f} Mo)")
    return path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--annees", type=int, nargs="+", default=[2021, 2022, 2023, 2024, 2025])
    args = parser.parse_args()
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    for annee in args.annees:
        download(annee)


if __name__ == "__main__":
    main()
