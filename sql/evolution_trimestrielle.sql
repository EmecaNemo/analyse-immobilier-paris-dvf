-- Prix médian au m² par trimestre : tout Paris (arrondissement = 0) et chaque arrondissement
SELECT 0 AS arrondissement, trimestre, MEDIAN(prix_m2)::INTEGER AS prix_m2_median, COUNT(*) AS nb_ventes
FROM transactions
GROUP BY trimestre
UNION ALL
SELECT arrondissement, trimestre, MEDIAN(prix_m2)::INTEGER, COUNT(*)
FROM transactions
GROUP BY arrondissement, trimestre
ORDER BY arrondissement, trimestre;
