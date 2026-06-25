from dash import dcc, html

from analise_temporal.services import dados
from analise_temporal.services.graficos import (
    fig_sazonalidade_heatmap,
    fig_sazonalidade_mensal,
)

PANEL_STYLE = {
    "backgroundColor": "white",
    "border": "1px solid #e5e7eb",
    "borderRadius": "8px",
    "padding": "16px",
}
MUTED_TEXT = {"color": "#4b5563", "fontSize": "14px", "lineHeight": "1.45"}


def create_layout():
    dff_mov = dados.df_mov.copy()

    return html.Div([
        html.H2("Sazonalidade", style={"marginTop": 0}),
        html.P(
            "Padrões mensais de nomeações e exonerações ao longo dos anos.",
            style=MUTED_TEXT,
        ),
        html.Div(style={"display": "grid", "gridTemplateColumns": "1fr 1fr", "gap": "16px", "marginTop": "16px"},
            children=[
                html.Div([
                    html.H4("Média Mensal", style={"margin": "0 0 8px 0"}),
                    dcc.Graph(id="graf_sazonalidade_mensal", figure=fig_sazonalidade_mensal(dff_mov)),
                ], style=PANEL_STYLE),
                html.Div([
                    html.H4("Heatmap Anual", style={"margin": "0 0 8px 0"}),
                    dcc.Graph(id="graf_sazonalidade_heatmap", figure=fig_sazonalidade_heatmap(dff_mov)),
                ], style=PANEL_STYLE),
            ]
        ),
        html.Div(style={"marginTop": "16px", **PANEL_STYLE},
            children=[
                html.P(
                    "Meses típicos de pico: final de ano (dezembro) e início de governo "
                    "costumam concentrar mais exonerações. Nomeações tendem a crescer "
                    "no início do ano legislativo.",
                    style=MUTED_TEXT,
                ),
            ]
        ),
    ])
