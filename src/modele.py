"""Entraîne un modèle de prédiction du prix au m² et le compare à des références.

Usage :
    python src/modele.py   # -> models/modele_prix.joblib + output/modele.md

Modèles comparés (même découpage apprentissage / test) :
- référence : prix médian au m² de l'arrondissement pour l'année ;
- régression linéaire (variables catégorielles encodées) ;
- gradient boosting (HistGradientBoostingRegressor) sur les mêmes variables ;
- gradient boosting + prix du voisinage (src/voisinage.py), entraîné sur log(prix au m²).
Le modèle qui a la plus faible erreur absolue moyenne est sauvegardé pour le dashboard.
"""

import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer, TransformedTargetRegressor
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_absolute_percentage_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # `src.voisinage`, importable aussi par app.py
from src.voisinage import PrixVoisinage  # noqa: E402

DATA = Path("data/processed/transactions.parquet")
MODEL_PATH = Path("models/modele_prix.joblib")
REPORT = Path("output/modele.md")
PREDICTIONS = Path("output/tables/predictions_test.csv")

CATEGORICAL = ["arrondissement", "type_local"]
NUMERIC = ["surface", "pieces", "dependance", "latitude", "longitude", "periode"]
LOCALISATION = ["latitude", "longitude", "periode"]  # entrées de PrixVoisinage
FEATURES = CATEGORICAL + NUMERIC
TARGET = "prix_m2"


def add_features(df: pd.DataFrame) -> pd.DataFrame:
    """`periode` = temps continu en années (ex. 2023.5), pour capter la tendance du marché."""
    date = pd.to_datetime(df["date"])
    return df.assign(
        periode=date.dt.year + (date.dt.dayofyear - 1) / 365,
        pieces=df["pieces"].astype(float),
        dependance=df["dependance"].astype(int),
    )


def build_models() -> dict:
    linear = make_pipeline(
        ColumnTransformer(
            [
                ("cat", OneHotEncoder(handle_unknown="ignore"), CATEGORICAL),
                ("num", StandardScaler(), NUMERIC),
            ]
        ),
        LinearRegression(),
    )
    boosting = make_pipeline(
        ColumnTransformer(
            [("cat", OneHotEncoder(handle_unknown="ignore", sparse_output=False), CATEGORICAL)],
            remainder="passthrough",
        ),
        HistGradientBoostingRegressor(max_iter=500, learning_rate=0.05, random_state=42),
    )
    # Prix du voisinage + cible en log : l'erreur porte sur des écarts relatifs, comme les prix.
    voisinage = TransformedTargetRegressor(
        regressor=make_pipeline(
            ColumnTransformer(
                [
                    ("cat", OneHotEncoder(handle_unknown="ignore", sparse_output=False), CATEGORICAL),
                    ("num", "passthrough", NUMERIC),
                    ("voisinage", PrixVoisinage(), LOCALISATION),
                ]
            ),
            HistGradientBoostingRegressor(max_iter=500, learning_rate=0.05, random_state=42),
        ),
        func=np.log,
        inverse_func=np.exp,
    )
    return {
        "Régression linéaire": linear,
        "Gradient boosting": boosting,
        "Gradient boosting + prix du voisinage": voisinage,
    }


def baseline_predict(train: pd.DataFrame, test: pd.DataFrame) -> np.ndarray:
    """Prédit la médiane (arrondissement, année) calculée sur l'échantillon d'apprentissage."""
    medians = train.groupby(["arrondissement", "annee"])[TARGET].median().rename("pred")
    return test.join(medians, on=["arrondissement", "annee"])["pred"].to_numpy()


def scores(y_true, y_pred) -> dict:
    return {
        "MAE (€/m²)": round(mean_absolute_error(y_true, y_pred)),
        "Erreur relative moyenne": f"{mean_absolute_percentage_error(y_true, y_pred):.1%}",
        "R²": round(r2_score(y_true, y_pred), 3),
    }


def main() -> None:
    df = add_features(pd.read_parquet(DATA))
    train, test = train_test_split(df, test_size=0.2, random_state=42)
    print(f"Apprentissage : {len(train):,} ventes — test : {len(test):,} ventes")

    results = {"Référence (médiane arrondissement × année)": scores(test[TARGET], baseline_predict(train, test))}
    fitted = {}
    for name, model in build_models().items():
        print(f"Entraînement : {name}...")
        model.fit(train[FEATURES], train[TARGET])
        fitted[name] = model
        results[name] = scores(test[TARGET], model.predict(test[FEATURES]))

    table = pd.DataFrame(results).T
    best = min(fitted, key=lambda n: results[n]["MAE (€/m²)"])
    print(table.to_string())
    print(f"Modèle retenu : {best}")

    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump({"model": fitted[best], "features": FEATURES, "name": best}, MODEL_PATH)

    PREDICTIONS.parent.mkdir(parents=True, exist_ok=True)
    test.assign(prediction=fitted[best].predict(test[FEATURES]).round(0))[
        ["arrondissement", "surface", "pieces", TARGET, "prediction"]
    ].to_csv(PREDICTIONS, index=False)

    REPORT.write_text(
        "\n".join(
            [
                "# Modèle de prédiction du prix au m²",
                "",
                f"Découpage aléatoire : {len(train):,} ventes pour l'apprentissage ; "
                f"{len(test):,} pour le test.".replace(",", " "),
                "",
                table.to_markdown(),
                "",
                f"Modèle retenu : **{best}**.",
                "",
                "*Prix du voisinage* : prix médian au m² des 10, 30 et 100 ventes les plus proches et prix "
                "des autres ventes du même immeuble, ajustés de l'évolution du marché et calculés hors "
                "échantillon (une vente ne sert jamais à décrire son propre prix).",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"-> {MODEL_PATH}, {REPORT}")


if __name__ == "__main__":
    main()
