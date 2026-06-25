from dash import dcc, html

from analise_temporal.services import dados
from analise_temporal.services.graficos import (
    fig_indicacao_por_governo,
    fig_indicacao_vs_carreira,
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

    total_gov = int((dff_mov["autoria_ato"] == "Governador").sum())
    total_sec = int((dff_mov["autoria_ato"] == "Secretaria/Subsecretaria").sum())
    total_outros = len(dff_mov) - total_gov - total_sec

    return html.Div([
        html.H2("Indicação Política vs Carreira", style={"marginTop": 0}),
        html.P(
            "Comparação entre atos assinados pelo governador (indicação política) e "
            "por secretarias/subsecretarias (carreira administrativa).",
            style=MUTED_TEXT,
        ),
        html.Div(style={"display": "grid", "gridTemplateColumns": "1fr 1fr 1fr", "gap": "12px", "marginTop": "16px"},
            children=[
                html.Div([
                    html.Div("Atos do Governador", style={"fontSize": "13px", "color": "#666"}),
                    html.Div(f"{total_gov:,}", style={"fontSize": "28px", "fontWeight": "bold", "color": "#b4423c"}),
                ], style=PANEL_STYLE),
                html.Div([
                    html.Div("Atos de Secretarias", style={"fontSize": "13px", "color": "#666"}),
                    html.Div(f"{total_sec:,}", style={"fontSize": "28px", "fontWeight": "bold", "color": "#287c5a"}),
                ], style=PANEL_STYLE),
                html.Div([
                    html.Div("Razão Gov/Secretaria", style={"fontSize": "13px", "color": "#666"}),
                    html.Div(
                        f"{total_gov / max(total_sec, 1):.2f}x",
                        style={"fontSize": "28px", "fontWeight": "bold"},
                    ),
                ], style=PANEL_STYLE),
            ]
        ),
        html.Div(style={"display": "grid", "gridTemplateColumns": "1fr 1fr", "gap": "16px", "marginTop": "16px"},
            children=[
                html.Div([
                    html.H4("Evolução Temporal", style={"margin": "0 0 8px 0"}),
                    dcc.Graph(id="graf_indicacao_vs_carreira", figure=fig_indicacao_vs_carreira(dff_mov)),
                ], style=PANEL_STYLE),
                html.Div([
                    html.H4("Composição por Governo", style={"margin": "0 0 8px 0"}),
                    dcc.Graph(id="graf_indicacao_por_governo", figure=fig_indicacao_por_governo(dff_mov)),
                ], style=PANEL_STYLE),
            ]
        ),
    ])
