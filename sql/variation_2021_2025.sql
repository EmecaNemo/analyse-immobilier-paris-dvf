-- Variation du prix médian au m² entre la première et la dernière année, par arrondissement
WITH par_annee AS (
    SELECT arrondissement, annee, MEDIAN(prix_m2) AS prix_m2_median
    FROM transactions
    GROUP BY arrondissement, annee
),
bornes AS (
    SELECT MIN(annee) AS debut, MAX(annee) AS fin FROM transactions
)
SELECT
    p.arrondissement,
    MAX(CASE WHEN p.annee = b.debut THEN p.prix_m2_median END)::INTEGER AS prix_debut,
    MAX(CASE WHEN p.annee = b.fin   THEN p.prix_m2_median END)::INTEGER AS prix_fin,
    ROUND(100 * (MAX(CASE WHEN p.annee = b.fin THEN p.prix_m2_median END)
               / MAX(CASE WHEN p.annee = b.debut THEN p.prix_m2_median END) - 1), 1) AS variation_pct
FROM par_annee p, bornes b
GROUP BY p.arrondissement
ORDER BY variation_pct;
