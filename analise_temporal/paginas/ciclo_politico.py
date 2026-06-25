from dash import dcc, html

from analise_temporal.services import dados
from analise_temporal.services.graficos import (
    fig_ciclo_politico,
    fig_transicoes_governo,
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

    governos = dff_mov["representante_governo"].dropna().unique()
    periodo = f"{int(dff_mov['ano'].min())}-{int(dff_mov['ano'].max())}"

    return html.Div([
        html.H2("Ciclo Político", style={"marginTop": 0}),
        html.P(
            "Impacto das transições de governo no volume de nomeações e exonerações.",
            style=MUTED_TEXT,
        ),
        html.Div(style={"display": "grid", "gridTemplateColumns": "1fr 1fr 1fr", "gap": "12px", "marginTop": "16px"},
            children=[
                html.Div([
                    html.Div("Governos no período", style={"fontSize": "13px", "color": "#666"}),
                    html.Div(f"{len(governos)}", style={"fontSize": "28px", "fontWeight": "bold"}),
                ], style=PANEL_STYLE),
                html.Div([
                    html.Div("Período analisado", style={"fontSize": "13px", "color": "#666"}),
                    html.Div(periodo, style={"fontSize": "28px", "fontWeight": "bold"}),
                ], style=PANEL_STYLE),
                html.Div([
                    html.Div("Governo com mais atos", style={"fontSize": "13px", "color": "#666"}),
                    html.Div(
                        dff_mov["representante_governo"].value_counts().index[0][:50],
                        style={"fontSize": "16px", "fontWeight": "bold"},
                    ),
                ], style=PANEL_STYLE),
            ]
        ),
        html.Div(style={"marginTop": "16px", **PANEL_STYLE},
            children=[dcc.Graph(id="graf_ciclo_politico", figure=fig_ciclo_politico(dff_mov))]),
        html.Div(style={"marginTop": "16px", **PANEL_STYLE},
            children=[dcc.Graph(id="graf_transicoes_governo", figure=fig_transicoes_governo(dff_mov))]),
    ])
