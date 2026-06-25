from dash import Input, Output, State, dcc, html

from analise_temporal.services import dados
from analise_temporal.services.graficos import fig_top_pessoas, fig_trajetoria_pessoa

PANEL_STYLE = {
    "backgroundColor": "white",
    "border": "1px solid #e5e7eb",
    "borderRadius": "8px",
    "padding": "16px",
}
MUTED_TEXT = {"color": "#4b5563", "fontSize": "14px", "lineHeight": "1.45"}


def create_layout():
    dff_mov = dados.df_mov.copy()
    pessoas = sorted(dff_mov["pessoa"].dropna().unique())

    return html.Div([
        html.H2("Carreiras Individuais", style={"marginTop": 0}),
        html.P(
            "Pessoas com mais movimentações no diário oficial e trajetória individual.",
            style=MUTED_TEXT,
        ),
        html.Div(style={"marginTop": "16px", **PANEL_STYLE},
            children=[dcc.Graph(id="graf_top_pessoas", figure=fig_top_pessoas(dff_mov))]),
        html.Div(style={"marginTop": "16px", **PANEL_STYLE},
            children=[
                html.H4("Trajetória Individual", style={"margin": "0 0 12px 0"}),
                html.Div(style={"display": "flex", "gap": "12px", "alignItems": "center", "marginBottom": "12px"},
                    children=[
                        dcc.Dropdown(
                            id="dd_pessoa",
                            options=[{"label": p, "value": p} for p in pessoas],
                            placeholder="Selecione uma pessoa...",
                            style={"width": "400px"},
                        ),
                        html.Button("Ver trajetória", id="btn_ver_trajetoria", n_clicks=0,
                            style={
                                "backgroundColor": "#1f5eff", "border": "0", "borderRadius": "6px",
                                "color": "white", "cursor": "pointer", "fontWeight": "bold",
                                "padding": "10px 14px",
                            }),
                    ]
                ),
                dcc.Graph(id="graf_trajetoria_pessoa"),
            ]
        ),
    ])


def register_callbacks(app):
    @app.callback(
        Output("graf_trajetoria_pessoa", "figure"),
        Input("btn_ver_trajetoria", "n_clicks"),
        State("dd_pessoa", "value"),
    )
    def update_trajetoria(n, pessoa):
        dff_mov = dados.df_mov.copy()
        return fig_trajetoria_pessoa(dff_mov, pessoa)
