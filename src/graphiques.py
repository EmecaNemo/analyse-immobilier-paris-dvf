"""Graphiques Plotly partagés par le dashboard Streamlit et l'export PNG du README.

Usage :
    python src/graphiques.py   # output/tables/*.csv -> output/figures/*.png
"""

import json
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

TABLES_DIR = Path("output/tables")
FIGURES_DIR = Path("output/figures")
GEOJSON = Path("data/arrondissements.geojson")

# Palette (catégorielle dans un ordre fixe, séquentielle bleue à une teinte)
SERIES = ["#2a78d6", "#eb6834", "#1baf7a"]  # 3 arrondissements comparés au maximum
PARIS = "#52514e"  # référence « tout Paris », neutre
NEGATIVE, POSITIVE = "#e34948", "#2a78d6"
SEQUENTIAL = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"]
TEXT, MUTED, GRID = "#0b0b0b", "#52514e", "#e8e7e3"


def arr_label(n: int) -> str:
    return "Paris" if n == 0 else ("1er" if n == 1 else f"{n}e")


def style(fig: go.Figure, title: str, height: int = 420) -> go.Figure:
    fig.update_layout(
        title=dict(text=title, font=dict(size=16, color=TEXT), x=0.01, xanchor="left"),
        template="plotly_white",
        font=dict(family="Inter, Helvetica, Arial, sans-serif", size=12, color=MUTED),
        height=height,
        margin=dict(l=20, r=20, t=70, b=20),
        paper_bgcolor="white",
        plot_bgcolor="white",
        hoverlabel=dict(bgcolor="white", font_color=TEXT),
    )
    fig.update_xaxes(showgrid=False, linecolor=GRID, ticks="")
    fig.update_yaxes(gridcolor=GRID, zeroline=False, ticks="")
    return fig


def label_shifts(ends: dict, values: pd.Series, plot_px: float = 300, gap_px: float = 16) -> dict:
    """Décalages verticaux (px) pour que les étiquettes de fin de courbe ne se chevauchent pas."""
    px_per_unit = plot_px / (values.max() - values.min())
    shifts, last_px = {}, None
    for arr, y in sorted(ends.items(), key=lambda kv: kv[1]):
        y_px = y * px_per_unit
        target = y_px if last_px is None else max(y_px, last_px + gap_px)
        shifts[arr], last_px = target - y_px, target
    return shifts


def evolution(trimestres: pd.DataFrame, arrondissements: list[int]) -> go.Figure:
    """Prix médian au m² par trimestre : tout Paris + jusqu'à 3 arrondissements."""
    fig = go.Figure()
    series = [0] + arrondissements[:3]
    ends = {a: trimestres[trimestres["arrondissement"] == a]["prix_m2_median"].iloc[-1] for a in series}
    shifts = label_shifts(ends, trimestres[trimestres["arrondissement"].isin(series)]["prix_m2_median"])
    for i, arr in enumerate(series):
        d = trimestres[trimestres["arrondissement"] == arr]
        color = PARIS if arr == 0 else SERIES[i - 1]
        fig.add_trace(
            go.Scatter(
                x=d["trimestre"],
                y=d["prix_m2_median"],
                name=arr_label(arr),
                mode="lines+markers",
                line=dict(color=color, width=2, dash="dot" if arr == 0 else "solid"),
                marker=dict(size=8, color=color, line=dict(color="white", width=2)),
                customdata=d["nb_ventes"],
                hovertemplate="%{y:,.0f} €/m² (%{customdata:,} ventes)<extra>" + arr_label(arr) + "</extra>",
            )
        )
        # Étiquette directe en fin de courbe
        fig.add_annotation(
            x=d["trimestre"].iloc[-1], y=d["prix_m2_median"].iloc[-1], text=arr_label(arr),
            xanchor="left", xshift=8, yshift=shifts[arr], showarrow=False, font=dict(color=TEXT, size=12),
        )
    fig = style(fig, "Évolution du prix médian au m²")
    fig.update_layout(hovermode="x unified", legend=dict(orientation="h", y=1.08, x=0))
    fig.update_yaxes(ticksuffix=" €", tickformat=",.0f")
    fig.update_xaxes(tickvals=[t for t in trimestres["trimestre"].unique() if t.endswith("Q1")])
    return fig.update_layout(separators=", ")


def heatmap(annuel: pd.DataFrame) -> go.Figure:
    """Prix médian au m² : arrondissements (lignes) × années (colonnes)."""
    pivot = annuel.pivot(index="arrondissement", columns="annee", values="prix_m2_median")
    fig = go.Figure(
        go.Heatmap(
            z=pivot.values,
            x=[str(a) for a in pivot.columns],
            y=[arr_label(a) for a in pivot.index],
            colorscale=SEQUENTIAL,
            text=pivot.values,
            texttemplate="%{text:,.0f}",
            textfont=dict(size=11),
            xgap=2,
            ygap=2,
            colorbar=dict(title="€/m²", tickformat=",.0f"),
            hovertemplate="%{y} · %{x} : %{z:,.0f} €/m²<extra></extra>",
        )
    )
    fig = style(fig, "Prix médian au m² par arrondissement et par année", height=640)
    fig.update_yaxes(autorange="reversed", gridcolor="white")
    return fig.update_layout(separators=", ")


def carte(annuel: pd.DataFrame, annee: int) -> go.Figure:
    """Carte choroplèthe des prix médians au m² pour une année."""
    geojson = json.loads(GEOJSON.read_text(encoding="utf-8"))
    d = annuel[annuel["annee"] == annee].assign(nom=lambda x: x["arrondissement"].map(arr_label))
    fig = px.choropleth(
        d,
        geojson=geojson,
        locations="arrondissement",
        featureidkey="properties.c_ar",
        color="prix_m2_median",
        color_continuous_scale=SEQUENTIAL,
        hover_name="nom",
        custom_data=["nb_ventes"],
    )
    fig.update_traces(
        marker_line_color="white",
        marker_line_width=1.5,
        hovertemplate="<b>%{hovertext}</b><br>%{z:,.0f} €/m²<br>%{customdata[0]:,} ventes<extra></extra>",
    )
    fig.update_geos(fitbounds="geojson", visible=False)
    fig = style(fig, f"Prix médian au m² en {annee}", height=520)
    fig.update_layout(coloraxis_colorbar=dict(title="€/m²", tickformat=",.0f"))
    return fig.update_layout(separators=", ")


def variation(variations: pd.DataFrame, debut: int, fin: int) -> go.Figure:
    """Variation du prix médian au m² entre deux années, par arrondissement."""
    d = variations.sort_values("variation_pct", ascending=False)
    fig = go.Figure(
        go.Bar(
            x=d["variation_pct"],
            y=[arr_label(a) for a in d["arrondissement"]],
            orientation="h",
            marker=dict(
                color=[NEGATIVE if v < 0 else POSITIVE for v in d["variation_pct"]],
                cornerradius=4,
            ),
            text=[f"{v:+.1f} %" for v in d["variation_pct"]],
            textposition="outside",
            textfont=dict(color=TEXT),
            customdata=d[["prix_debut", "prix_fin"]],
            hovertemplate=(
                "%{y} : %{customdata[0]:,.0f} → %{customdata[1]:,.0f} €/m²<extra></extra>"
            ),
        )
    )
    fig = style(fig, f"Variation du prix médian au m² entre {debut} et {fin}", height=620)
    fig.update_layout(bargap=0.25)
    lo, hi = d["variation_pct"].min(), d["variation_pct"].max()
    fig.update_xaxes(
        ticksuffix=" %", gridcolor=GRID, showgrid=True, zeroline=True, zerolinecolor=MUTED,
        range=[min(lo, 0) * 1.2 - 0.5, max(hi, 0) * 1.2 + 0.5],  # place pour les étiquettes
    )
    fig.update_yaxes(showgrid=False)
    return fig.update_layout(separators=", ")


def predictions(pred: pd.DataFrame, n: int = 3000) -> go.Figure:
    """Prix au m² prédit vs réel sur un échantillon du jeu de test."""
    d = pred.sample(min(n, len(pred)), random_state=0)
    lo, hi = 3_000, 25_000
    fig = go.Figure(
        [
            go.Scatter(
                x=[lo, hi], y=[lo, hi], mode="lines", name="Prédiction parfaite",
                line=dict(color=MUTED, width=1.5, dash="dash"), hoverinfo="skip",
            ),
            go.Scatter(
                x=d["prix_m2"], y=d["prediction"], mode="markers", name="Ventes (test)",
                marker=dict(size=8, color=SERIES[0], opacity=0.25, line=dict(color="white", width=1)),
                hovertemplate="Réel : %{x:,.0f} €/m²<br>Prédit : %{y:,.0f} €/m²<extra></extra>",
            ),
        ]
    )
    fig = style(fig, "Prix au m² prédit vs réel (échantillon de test)", height=520)
    fig.update_xaxes(title="Prix réel (€/m²)", range=[lo, hi], tickformat=",.0f", showgrid=True, gridcolor=GRID)
    fig.update_yaxes(title="Prix prédit (€/m²)", range=[lo, hi], tickformat=",.0f")
    fig.update_layout(legend=dict(orientation="h", y=1.08, x=0))
    return fig.update_layout(separators=", ")


def load_tables() -> dict[str, pd.DataFrame]:
    return {p.stem: pd.read_csv(p) for p in TABLES_DIR.glob("*.csv")}


def main() -> None:
    t = load_tables()
    annees = sorted(t["prix_arrondissement_annee"]["annee"].unique())
    figures = {
        "evolution": evolution(t["evolution_trimestrielle"], [7, 11, 19]),
        "heatmap": heatmap(t["prix_arrondissement_annee"]),
        "carte": carte(t["prix_arrondissement_annee"], annees[-1]),
        "variation": variation(t["variation_2021_2025"], annees[0], annees[-1]),
    }
    if "predictions_test" in t:
        figures["predictions"] = predictions(t["predictions_test"])
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    for name, fig in figures.items():
        fig.write_image(FIGURES_DIR / f"{name}.png", width=900, scale=2)
        print(f"-> {FIGURES_DIR / name}.png")


if __name__ == "__main__":
    main()
