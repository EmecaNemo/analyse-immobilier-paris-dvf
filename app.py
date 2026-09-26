"""Dashboard Streamlit : marché immobilier parisien (données DVF).

Usage :
    streamlit run app.py
"""

import json
from datetime import date
from pathlib import Path

import joblib
import pandas as pd
import streamlit as st

from src.graphiques import GEOJSON, arr_label, carte, evolution, heatmap, predictions, variation

TABLES = Path("output/tables")
MODEL_PATH = Path("models/modele_prix.joblib")

st.set_page_config(page_title="Immobilier parisien (DVF)", page_icon="🏠", layout="wide")


@st.cache_data
def load_tables() -> dict[str, pd.DataFrame]:
    return {p.stem: pd.read_csv(p) for p in TABLES.glob("*.csv")}


@st.cache_resource
def load_model() -> dict:
    return joblib.load(MODEL_PATH)


@st.cache_data
def centroids() -> dict[int, tuple[float, float]]:
    """Centre (lat, lon) de chaque arrondissement, utilisé par l'estimateur."""
    features = json.loads(GEOJSON.read_text(encoding="utf-8"))["features"]
    return {f["properties"]["c_ar"]: (f["properties"]["geom_x_y"]["lat"], f["properties"]["geom_x_y"]["lon"]) for f in features}


def euros(x: float) -> str:
    return f"{x:,.0f} €".replace(",", " ")


t = load_tables()
annuel = t["prix_arrondissement_annee"]
trimestres = t["evolution_trimestrielle"]
annees = sorted(annuel["annee"].unique())
paris = trimestres[trimestres["arrondissement"] == 0]

st.title("🏠 Marché immobilier parisien")
st.caption(
    f"Ventes d'appartements et de maisons à Paris, {annees[0]}–{annees[-1]} · "
    "Source : Demandes de valeurs foncières (DVF), data.gouv.fr"
)

# Indicateurs clés
dernier, premier = paris.iloc[-1], paris.iloc[0]
c1, c2, c3 = st.columns(3)
c1.metric(f"Prix médian au m² ({dernier['trimestre']})", euros(dernier["prix_m2_median"]))
c2.metric(
    f"Variation depuis {premier['trimestre']}",
    f"{dernier['prix_m2_median'] / premier['prix_m2_median'] - 1:+.1%}".replace(".", ","),
)
c3.metric("Ventes analysées", f"{int(annuel['nb_ventes'].sum()):,}".replace(",", " "))

tab_evol, tab_carte, tab_estim, tab_methodo = st.tabs(
    ["📈 Évolution", "🗺️ Carte", "🧮 Estimer un bien", "ℹ️ Méthodologie"]
)

with tab_evol:
    choix = st.multiselect(
        "Comparer avec Paris (3 arrondissements maximum)",
        options=list(range(1, 21)),
        default=[7, 11, 19],
        format_func=arr_label,
        max_selections=3,
    )
    st.plotly_chart(evolution(trimestres, choix), width="stretch")
    st.plotly_chart(heatmap(annuel), width="stretch")

with tab_carte:
    annee = st.select_slider("Année", options=annees, value=annees[-1])
    st.plotly_chart(carte(annuel, annee), width="stretch")
    st.plotly_chart(variation(t["variation_2021_2025"], annees[0], annees[-1]), width="stretch")
    st.markdown("**Prix selon la taille du logement**")
    st.dataframe(
        t["prix_par_taille"].rename(
            columns={
                "taille": "Taille",
                "prix_m2_median": "Prix médian au m² (€)",
                "surface_mediane": "Surface médiane (m²)",
                "prix_median": "Prix médian (€)",
                "nb_ventes": "Ventes",
            }
        ),
        hide_index=True,
    )

with tab_estim:
    bundle = load_model()
    left, right = st.columns([1, 1])
    with left:
        arr = st.selectbox("Arrondissement", list(range(1, 21)), index=10, format_func=arr_label)
        surface = st.number_input("Surface (m²)", min_value=9, max_value=400, value=50, step=1)
        pieces = st.number_input("Nombre de pièces", min_value=1, max_value=10, value=2, step=1)
        type_local = st.radio("Type de bien", ["Appartement", "Maison"], horizontal=True)
        dependance = st.checkbox("Avec cave ou parking")
    lat, lon = centroids()[arr]
    today = date.today()
    X = pd.DataFrame(
        [
            {
                "arrondissement": arr,
                "type_local": type_local,
                "surface": float(surface),
                "pieces": float(pieces),
                "dependance": int(dependance),
                "latitude": lat,
                "longitude": lon,
                "periode": min(today.year + (today.timetuple().tm_yday - 1) / 365, annees[-1] + 1),
            }
        ]
    )[bundle["features"]]
    prix_m2 = float(bundle["model"].predict(X)[0])
    with right:
        st.metric("Prix estimé", euros(prix_m2 * surface))
        st.metric("Prix au m² estimé", euros(prix_m2))
        st.caption(
            f"Modèle : {bundle['name']} (scikit-learn). Erreur moyenne sur le jeu de test : ±17 % environ. "
            "Estimation indicative : l'étage, l'état du bien ou le DPE ne figurent pas dans les données DVF."
        )
    if "predictions_test" in t:
        st.plotly_chart(predictions(t["predictions_test"]), width="stretch")

with tab_methodo:
    for fichier in ["nettoyage.md", "modele.md"]:
        chemin = Path("output") / fichier
        if chemin.exists():
            st.markdown(chemin.read_text(encoding="utf-8"))
    st.markdown(
        "Le code (nettoyage pandas, requêtes SQL DuckDB, modèle scikit-learn) est disponible sur "
        "[GitHub](https://github.com/EmecaNemo/analyse-immobilier-paris-dvf)."
    )
