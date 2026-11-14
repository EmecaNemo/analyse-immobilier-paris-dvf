"""Tests de src/nettoyer.py sur un petit jeu de données inventé (aucun téléchargement).

Lancer : .venv/bin/python -m pytest -q
"""
import pandas as pd
import pytest

from src import nettoyer


def ligne(id_mutation, type_local="Appartement", valeur=500_000, surface=50, **autres):
    """Une ligne DVF brute minimale ; les arguments nommés remplacent les valeurs par défaut."""
    base = {
        "id_mutation": id_mutation,
        "date_mutation": "2024-03-15",
        "nature_mutation": "Vente",
        "valeur_fonciere": valeur,
        "code_commune": 75111,
        "type_local": type_local,
        "surface_reelle_bati": surface,
        "nombre_pieces_principales": 2,
        "latitude": 48.86,
        "longitude": 2.38,
    }
    return base | autres


# --- Exemple déjà écrit ------------------------------------------------------------------------------

def test_une_vente_simple_est_gardee_avec_son_prix_m2():
    raw = pd.DataFrame([ligne("2024-1")])
    df, steps = nettoyer.clean(raw)
    assert len(df) == 1
    assert df.loc[0, "prix_m2"] == 10_000          # 500 000 € / 50 m²
    assert df.loc[0, "arrondissement"] == 11       # code commune 75111 → 11e
    assert steps[-1] == ("Transactions géolocalisées", 1)


# --- Règles de filtrage ------------------------------------------------------------------------------

def test_vente_de_deux_logements_est_exclue():
    # Mutation avec 2 appartements : la valeur foncière couvre les deux, le prix au m² serait faux.
    raw = pd.DataFrame([ligne("2024-2"), ligne("2024-2", surface=30), ligne("2024-3")])
    df, _ = nettoyer.clean(raw)
    assert df["id_mutation"].tolist() == ["2024-3"]


def test_bornes_surface_et_prix_m2():
    raw = pd.DataFrame([
        ligne("a", surface=8),                      # trop petit (< 9 m²)
        ligne("b", surface=450, valeur=5_000_000),  # trop grand (> 400 m²)
        ligne("c", valeur=100_000),                 # 2 000 €/m² : trop bas (< 3 000)
        ligne("d"),                                 # 10 000 €/m² : gardée
        ligne("d", type_local="Dépendance", surface=None),  # cave vendue avec « d »
    ])
    df, _ = nettoyer.clean(raw)
    assert df["id_mutation"].tolist() == ["d"]
    assert bool(df.loc[0, "dependance"]) is True  # la cave n'exclut pas la vente, elle est notée


def test_vente_avec_local_commercial_est_exclue():
    raw = pd.DataFrame([ligne("e"), ligne("e", type_local=nettoyer.LOCAL_COMMERCIAL, surface=20)])
    df, _ = nettoyer.clean(raw)
    assert df.empty


def test_doublons_et_non_ventes_retires():
    raw = pd.DataFrame([
        ligne("f"), ligne("f"),                          # doublon exact → une seule ligne
        ligne("g", nature_mutation="Echange"),           # pas une vente
        ligne("h", valeur=None),                         # prix manquant
        ligne("i", latitude=None),                       # non géolocalisée
    ])
    df, steps = nettoyer.clean(raw)
    assert df["id_mutation"].tolist() == ["f"]
    assert steps[1] == ("Suppression des doublons exacts", 4)
