from dash import dcc, html

from analise_temporal.services import dados
from analise_temporal.services.graficos import (
    fig_anomalias_orgaos,
    fig_anomalias_por_ano,
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
        html.H2("Anomalias", style={"marginTop": 0}),
        html.P(
            "Detecção de anos e órgãos com volume de atos atípico (fora de ±2σ / ±3σ da média).",
            style=MUTED_TEXT,
        ),
        html.Div(style={"marginTop": "16px", **PANEL_STYLE},
            children=[dcc.Graph(id="graf_anomalias_ano", figure=fig_anomalias_por_ano(dff_mov))]),
        html.Div(style={"marginTop": "16px", **PANEL_STYLE},
            children=[dcc.Graph(id="graf_anomalias_orgaos", figure=fig_anomalias_orgaos(dff_mov))]),
    ])
