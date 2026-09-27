# Modèle de prédiction du prix au m²

Découpage aléatoire : 114 871 ventes pour l'apprentissage ; 28 718 pour le test.

|                                            |   MAE (€/m²) | Erreur relative moyenne   |    R² |
|:-------------------------------------------|-------------:|:--------------------------|------:|
| Référence (médiane arrondissement × année) |         1875 | 19.0%                     | 0.268 |
| Régression linéaire                        |         1874 | 19.4%                     | 0.297 |
| Gradient boosting                          |         1699 | 17.5%                     | 0.4   |
| Gradient boosting + prix du voisinage      |         1672 | 16.8%                     | 0.411 |

Modèle retenu : **Gradient boosting + prix du voisinage**.

*Prix du voisinage* : prix médian au m² des 10, 30 et 100 ventes les plus proches et prix des autres ventes du même immeuble, ajustés de l'évolution du marché et calculés hors échantillon (une vente ne sert jamais à décrire son propre prix).
