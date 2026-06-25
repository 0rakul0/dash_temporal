from dash import dcc, html

from analise_temporal.services import dados
from analise_temporal.services.graficos import (
    fig_coccurrencias,
    fig_distribuicao_por_edicao,
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
        html.H2("Co-ocorrência", style={"marginTop": 0}),
        html.P(
            "Análise de quantas pessoas são nomeadas/exoneradas na mesma edição do diário oficial. "
            "Edições com muitos atos podem indicar mutirões ou reformas administrativas.",
            style=MUTED_TEXT,
        ),
        html.Div(style={"display": "grid", "gridTemplateColumns": "1fr 1fr", "gap": "16px", "marginTop": "16px"},
            children=[
                html.Div([
                    html.H4("Edições com Maior Concentração", style={"margin": "0 0 8px 0"}),
                    dcc.Graph(id="graf_coccurrencias", figure=fig_coccurrencias(dff_mov)),
                ], style=PANEL_STYLE),
                html.Div([
                    html.H4("Distribuição por Edição", style={"margin": "0 0 8px 0"}),
                    dcc.Graph(id="graf_distribuicao_edicao", figure=fig_distribuicao_por_edicao(dff_mov)),
                ], style=PANEL_STYLE),
            ]
        ),
    ])
