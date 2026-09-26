# Modèle de prédiction du prix au m²

Découpage aléatoire : 114 871 ventes pour l'apprentissage  28 718 pour le test.

|                                            |   MAE (€/m²) | Erreur relative moyenne   |    R² |
|:-------------------------------------------|-------------:|:--------------------------|------:|
| Référence (médiane arrondissement × année) |         1875 | 19.0%                     | 0.268 |
| Régression linéaire                        |         1874 | 19.4%                     | 0.297 |
| Gradient boosting                          |         1699 | 17.5%                     | 0.4   |

Modèle retenu : **Gradient boosting**.
