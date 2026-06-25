from dash import dcc, html

from analise_temporal.services import dados
from analise_temporal.services.graficos import fig_rotatividade_orgaos

PANEL_STYLE = {
    "backgroundColor": "white",
    "border": "1px solid #e5e7eb",
    "borderRadius": "8px",
    "padding": "16px",
}
MUTED_TEXT = {"color": "#4b5563", "fontSize": "14px", "lineHeight": "1.45"}


def create_layout():
    dff_mov = dados.df_mov.copy()

    total_orgaos = dff_mov["orgao"].nunique()
    top_orgao = dff_mov["orgao"].value_counts().index[0]

    return html.Div([
        html.H2("Rotatividade por Órgão", style={"marginTop": 0}),
        html.P(
            "Volume de nomeações e exonerações por órgão. Quanto maior a soma, maior a rotatividade.",
            style=MUTED_TEXT,
        ),
        html.Div(style={"display": "grid", "gridTemplateColumns": "1fr 1fr 1fr", "gap": "12px", "marginTop": "16px"},
            children=[
                html.Div([
                    html.Div("Órgãos distintos", style={"fontSize": "13px", "color": "#666"}),
                    html.Div(f"{total_orgaos:,}", style={"fontSize": "28px", "fontWeight": "bold"}),
                ], style=PANEL_STYLE),
                html.Div([
                    html.Div("Órgão com mais atos", style={"fontSize": "13px", "color": "#666"}),
                    html.Div(str(top_orgao)[:60], style={"fontSize": "16px", "fontWeight": "bold"}),
                ], style=PANEL_STYLE),
                html.Div([
                    html.Div("Média de atos por órgão", style={"fontSize": "13px", "color": "#666"}),
                    html.Div(f"{len(dff_mov) / total_orgaos:.0f}", style={"fontSize": "28px", "fontWeight": "bold"}),
                ], style=PANEL_STYLE),
            ]
        ),
        html.Div(style={"marginTop": "16px", **PANEL_STYLE},
            children=[dcc.Graph(id="graf_rotatividade", figure=fig_rotatividade_orgaos(dff_mov))]),
    ])
