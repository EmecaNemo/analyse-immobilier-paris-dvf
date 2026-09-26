-- Prix médian au m² selon la taille du logement
SELECT
    CASE
        WHEN pieces <= 1 THEN '1 pièce'
        WHEN pieces = 2  THEN '2 pièces'
        WHEN pieces = 3  THEN '3 pièces'
        WHEN pieces = 4  THEN '4 pièces'
        ELSE '5 pièces et +'
    END                         AS taille,
    MEDIAN(prix_m2)::INTEGER    AS prix_m2_median,
    MEDIAN(surface)::INTEGER    AS surface_mediane,
    MEDIAN(prix)::INTEGER       AS prix_median,
    COUNT(*)                    AS nb_ventes
FROM transactions
GROUP BY taille
ORDER BY taille;
