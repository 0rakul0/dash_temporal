from dash import dcc, html

from analise_temporal.services import dados
from analise_temporal.services.graficos import fig_timeline_mobilidade

PANEL_STYLE = {
    "backgroundColor": "white",
    "border": "1px solid #e5e7eb",
    "borderRadius": "8px",
    "padding": "16px",
}
MUTED_TEXT = {"color": "#4b5563", "fontSize": "14px", "lineHeight": "1.45"}


def create_layout():
    dff = dados.df.copy()

    return html.Div([
        html.H2("Mobilidade após Exoneração", style={"marginTop": 0}),
        html.P(
            "Taxa de pessoas que mudaram de cargo ou órgão quando retornaram após exoneração.",
            style=MUTED_TEXT,
        ),
        html.Div(style={"marginTop": "16px", **PANEL_STYLE},
            children=[dcc.Graph(id="graf_mobilidade", figure=fig_timeline_mobilidade(dff))]),
        html.Div(style={"display": "grid", "gridTemplateColumns": "1fr 1fr", "gap": "16px", "marginTop": "16px"},
            children=[
                html.Div([
                    html.H4("Resumo", style={"margin": "0 0 8px 0"}),
                    html.Div([
                        html.P(f"Total de retornos: {len(dff):,}", style=MUTED_TEXT),
                        html.P(f"Mudaram de cargo: {dff['mudou_cargo'].sum():,} ({dff['mudou_cargo'].mean():.1%})",
                                style=MUTED_TEXT),
                        html.P(f"Mudaram de órgão: {dff['mudou_orgao'].sum():,} ({dff['mudou_orgao'].mean():.1%})",
                                style=MUTED_TEXT),
                    ]),
                ], style=PANEL_STYLE),
                html.Div([
                    html.H4("Distribuição Temporal", style={"margin": "0 0 8px 0"}),
                    html.P(
                        "Pessoas que retornam imediatamente (<1 dia) tendem a ser "
                        "reconduções formais. Retornos longos (>180 dias) indicam "
                        "reingresso no serviço público após afastamento prolongado.",
                        style=MUTED_TEXT,
                    ),
                ], style=PANEL_STYLE),
            ]
        ),
    ])
