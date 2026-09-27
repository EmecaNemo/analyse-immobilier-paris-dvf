"""Variables de voisinage : prix au m² des ventes les plus proches géographiquement.

Le transformer apprend les ventes de l'échantillon d'apprentissage (coordonnées + prix) et
calcule, pour chaque bien, le prix médian de ses 10, 30 et 100 plus proches voisins, ainsi que
le prix médian des ventes du même immeuble (moins de 15 m).

Les prix des voisins sont d'abord ramenés à un niveau de marché commun (écart au prix médian
de leur trimestre), pour ne pas mélanger une vente de 2021 et une vente de 2024. Le calcul est
additif : appliqué à log(prix), il correspond à un ajustement en pourcentage.

Pour éviter la fuite de données, `fit_transform` calcule ces variables « hors échantillon »
(validation croisée en 5 blocs), comme `TargetEncoder` de scikit-learn : une vente ne sert
jamais à décrire son propre prix.
"""

import numpy as np
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.model_selection import KFold
from sklearn.neighbors import KDTree

K_VOISINS = (10, 30, 100)
RAYON_IMMEUBLE = 15  # mètres
LAT_REF = np.radians(48.86)


def to_metres(X) -> np.ndarray:
    """Projection plane (latitude, longitude) -> mètres, suffisante à l'échelle de Paris."""
    return np.c_[X["longitude"].to_numpy() * 111_320 * np.cos(LAT_REF), X["latitude"].to_numpy() * 110_540]


def trimestre(X) -> np.ndarray:
    return np.floor(X["periode"].to_numpy() * 4)


class PrixVoisinage(TransformerMixin, BaseEstimator):
    """Entrée : colonnes latitude, longitude, periode. Sortie : 5 variables de voisinage."""

    def __init__(self, n_splits: int = 5, random_state: int = 0):
        self.n_splits = n_splits
        self.random_state = random_state

    def fit(self, X, y):
        y = np.asarray(y, dtype=float)
        q = trimestre(X)
        niveaux = {t: np.median(y[q == t]) for t in np.unique(q)}
        self.niveaux_ = niveaux
        self.y_ajuste_ = y - np.array([niveaux[t] for t in q])
        self.tree_ = KDTree(to_metres(X))
        return self

    def transform(self, X):
        return self._features(self.tree_, self.y_ajuste_, X)

    def fit_transform(self, X, y):
        self.fit(X, y)
        out = np.empty((len(X), 5))
        folds = KFold(self.n_splits, shuffle=True, random_state=self.random_state)
        for ref, qry in folds.split(X):
            tree = KDTree(to_metres(X.iloc[ref]))
            out[qry] = self._features(tree, self.y_ajuste_[ref], X.iloc[qry])
        return out

    @staticmethod
    def _features(tree, y_ajuste, X) -> np.ndarray:
        dist, idx = tree.query(to_metres(X), k=max(K_VOISINS))
        voisins = [np.median(y_ajuste[idx[:, :k]], axis=1) for k in K_VOISINS]
        meme_immeuble = dist < RAYON_IMMEUBLE
        n = meme_immeuble.sum(axis=1)
        somme = np.where(meme_immeuble, y_ajuste[idx], 0).sum(axis=1)
        # Moyenne (et non médiane) des ventes du même immeuble, NaN s'il n'y en a pas :
        # le gradient boosting gère les valeurs manquantes.
        immeuble = np.divide(somme, n, out=np.full(len(n), np.nan), where=n > 0)
        return np.c_[np.column_stack(voisins), n, immeuble]

    def get_feature_names_out(self, input_features=None):
        return np.array([f"voisins_{k}" for k in K_VOISINS] + ["immeuble_nb_ventes", "immeuble_prix"])
