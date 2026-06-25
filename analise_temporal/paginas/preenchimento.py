from dash import dcc, html

from analise_temporal.services import dados
from analise_temporal.services.graficos import (
    fig_preenchimento_por_tempo,
    fig_tempo_preenchimento,
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
    dff_mov = dados.df_mov.copy()

    media_dias = dff["dias_desde_exoneracao"].mean()
    mediana_dias = dff["dias_desde_exoneracao"].median()

    return html.Div([
        html.H2("Tempo de Preenchimento de Vagas", style={"marginTop": 0}),
        html.P(
            "Análise do tempo entre a exoneração de uma pessoa e sua nova nomeação.",
            style=MUTED_TEXT,
        ),
        html.Div(style={"display": "grid", "gridTemplateColumns": "1fr 1fr 1fr", "gap": "12px", "marginTop": "16px"},
            children=[
                html.Div([
                    html.Div("Tempo médio", style={"fontSize": "13px", "color": "#666"}),
                    html.Div(f"{media_dias:.0f} dias", style={"fontSize": "28px", "fontWeight": "bold"}),
                ], style=PANEL_STYLE),
                html.Div([
                    html.Div("Tempo mediano", style={"fontSize": "13px", "color": "#666"}),
                    html.Div(f"{mediana_dias:.0f} dias", style={"fontSize": "28px", "fontWeight": "bold"}),
                ], style=PANEL_STYLE),
                html.Div([
                    html.Div("Retornos imediatos (0 dias)", style={"fontSize": "13px", "color": "#666"}),
                    html.Div(
                        f"{int((dff['dias_desde_exoneracao'] == 0).sum()):,}",
                        style={"fontSize": "28px", "fontWeight": "bold"},
                    ),
                ], style=PANEL_STYLE),
            ]
        ),
        html.Div(style={"display": "grid", "gridTemplateColumns": "1fr 1fr", "gap": "16px", "marginTop": "16px"},
            children=[
                html.Div([
                    html.H4("Distribuição de Dias", style={"margin": "0 0 8px 0"}),
                    dcc.Graph(id="graf_tempo_preenchimento", figure=fig_tempo_preenchimento(dff, dff_mov)),
                ], style=PANEL_STYLE),
                html.Div([
                    html.H4("Categorias de Retorno", style={"margin": "0 0 8px 0"}),
                    dcc.Graph(id="graf_preenchimento_tempo", figure=fig_preenchimento_por_tempo(dff)),
                ], style=PANEL_STYLE),
            ]
        ),
    ])
