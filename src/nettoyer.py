"""Nettoie les données DVF brutes : une ligne par vente d'un logement, avec son prix au m².

Usage :
    python src/nettoyer.py   # data/raw/*.csv.gz -> data/processed/transactions.parquet

Une mutation DVF peut s'étaler sur plusieurs lignes (appartement + cave + parking) et la
valeur foncière est répétée sur chaque ligne. On ne garde donc que les ventes portant sur
un seul logement : le prix de la mutation est alors bien celui de ce logement.
"""

from pathlib import Path

import pandas as pd

RAW_DIR = Path("data/raw")
OUTPUT = Path("data/processed/transactions.parquet")
REPORT = Path("output/nettoyage.md")

LOGEMENTS = ["Appartement", "Maison"]
LOCAL_COMMERCIAL = "Local industriel. commercial ou assimilé"
SURFACE_MIN, SURFACE_MAX = 9, 400  # m² ; 9 m² = surface minimale d'un logement décent
PRIX_M2_MIN, PRIX_M2_MAX = 3_000, 35_000  # € / m² ; hors de ces bornes : erreurs ou ventes atypiques


def load_raw() -> pd.DataFrame:
    files = sorted(RAW_DIR.glob("dvf_75_*.csv.gz"))
    if not files:
        raise SystemExit("Aucun fichier brut : lancez d'abord python src/telecharger.py")
    return pd.concat((pd.read_csv(f, low_memory=False) for f in files), ignore_index=True)


def clean(raw: pd.DataFrame) -> tuple[pd.DataFrame, list[tuple[str, int]]]:
    """Renvoie les ventes nettoyées et le nombre de lignes restant après chaque étape."""
    steps = [("Lignes brutes", len(raw))]

    df = raw.drop_duplicates()
    steps.append(("Suppression des doublons exacts", len(df)))

    df = df[(df["nature_mutation"] == "Vente") & df["valeur_fonciere"].notna()]
    steps.append(("Ventes avec un prix renseigné", len(df)))

    # Composition de chaque mutation : nombre de logements et de locaux commerciaux
    composition = df.groupby("id_mutation")["type_local"].agg(
        n_logements=lambda s: s.isin(LOGEMENTS).sum(),
        n_commerces=lambda s: (s == LOCAL_COMMERCIAL).sum(),
        n_dependances=lambda s: (s == "Dépendance").sum(),
    )
    simples = composition[(composition["n_logements"] == 1) & (composition["n_commerces"] == 0)]
    df = df[df["type_local"].isin(LOGEMENTS)].merge(simples, left_on="id_mutation", right_index=True)
    steps.append(("Ventes d'un seul logement (1 ligne par vente)", len(df)))

    df = df[df["surface_reelle_bati"].between(SURFACE_MIN, SURFACE_MAX)]
    steps.append((f"Surface entre {SURFACE_MIN} et {SURFACE_MAX} m²", len(df)))

    df = df.assign(prix_m2=df["valeur_fonciere"] / df["surface_reelle_bati"])
    df = df[df["prix_m2"].between(PRIX_M2_MIN, PRIX_M2_MAX)]
    steps.append((f"Prix au m² entre {PRIX_M2_MIN:,} et {PRIX_M2_MAX:,} €".replace(",", " "), len(df)))

    df = df.dropna(subset=["latitude", "longitude"])
    steps.append(("Transactions géolocalisées", len(df)))

    date = pd.to_datetime(df["date_mutation"])
    clean_df = pd.DataFrame(
        {
            "id_mutation": df["id_mutation"],
            "date": date,
            "annee": date.dt.year,
            "trimestre": date.dt.to_period("Q").astype(str),
            "arrondissement": df["code_commune"].astype(int) - 75100,
            "type_local": df["type_local"],
            "surface": df["surface_reelle_bati"],
            "pieces": df["nombre_pieces_principales"].astype("Int64"),
            "dependance": df["n_dependances"] > 0,
            "prix": df["valeur_fonciere"],
            "prix_m2": df["prix_m2"].round(0),
            "latitude": df["latitude"],
            "longitude": df["longitude"],
        }
    )
    return clean_df.sort_values("date").reset_index(drop=True), steps


def write_report(steps: list[tuple[str, int]]) -> None:
    lines = ["# Nettoyage des données", "", "| Étape | Lignes restantes |", "|:--|--:|"]
    lines += [f"| {name} | {count:,} |".replace(",", " ") for name, count in steps]
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    df, steps = clean(load_raw())
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(OUTPUT, index=False)
    write_report(steps)
    for name, count in steps:
        print(f"{count:>9,}  {name}")
    print(f"-> {OUTPUT} ({len(df):,} ventes)")


if __name__ == "__main__":
    main()
