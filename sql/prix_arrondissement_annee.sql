-- Prix médian au m² et nombre de ventes, par arrondissement et par année
SELECT
    arrondissement,
    annee,
    MEDIAN(prix_m2)::INTEGER AS prix_m2_median,
    COUNT(*)                 AS nb_ventes
FROM transactions
GROUP BY arrondissement, annee
ORDER BY arrondissement, annee;
