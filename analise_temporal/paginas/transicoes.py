from dash import dcc, html

from analise_temporal.services import dados
from analise_temporal.services.graficos import (
    construir_eventos,
    estado_estacionario,
    fig_heatmap,
    fig_network_3d,
    fig_sankey,
    gerar_resumo,
    matriz_transicao,
)

PANEL_STYLE = {
    "backgroundColor": "white",
    "border": "1px solid #e5e7eb",
    "borderRadius": "8px",
    "padding": "16px",
}
MUTED_TEXT = {"color": "#4b5563", "fontSize": "14px", "lineHeight": "1.45"}


def create_layout():
    dff = dados.df.copy()
    eventos, trans = construir_eventos(dff)
    matriz, mat_prob = matriz_transicao(trans)
    est = estado_estacionario(mat_prob)
    resumo = gerar_resumo(dff, trans, mat_prob)

    return html.Div([
        html.H2("Fluxo e Transições de Estado", style={"marginTop": 0}),
        html.P(
            "Análise das transições entre estados após exoneração: mudança de cargo, órgão e tempo de retorno.",
            style=MUTED_TEXT,
        ),
        html.Div(style={"display": "grid", "gridTemplateColumns": "1fr 1fr", "gap": "16px", "marginTop": "16px"},
            children=[
                html.Div([
                    html.H4("Matriz de Transição (Probabilidades)", style={"margin": "0 0 8px 0"}),
                    dcc.Graph(id="graf_heatmap", figure=fig_heatmap(mat_prob)),
                ], style=PANEL_STYLE),
                html.Div([
                    html.H4("Diagrama Sankey", style={"margin": "0 0 8px 0"}),
                    dcc.Graph(id="graf_sankey", figure=fig_sankey(trans)),
                ], style=PANEL_STYLE),
            ]
        ),
        html.Div(style={"marginTop": "16px"}, children=[
            html.Div([
                html.H4("Rede de Transições 3D", style={"margin": "0 0 8px 0"}),
                dcc.Graph(id="graf_rede3d", figure=fig_network_3d(trans)),
            ], style=PANEL_STYLE),
        ]),
        html.Div(style={"marginTop": "16px", **PANEL_STYLE},
            children=[
                html.H4("Resumo Analítico", style={"margin": "0 0 8px 0"}),
                html.Pre(resumo, style=MUTED_TEXT | {"whiteSpace": "pre-wrap", "fontSize": "13px"}),
            ]
        ),
    ])
