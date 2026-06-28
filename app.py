from __future__ import annotations

import os

from dash import Dash, Input, Output, State, dcc, html

from analise_temporal.paginas import anomalias
from analise_temporal.paginas import busca
from analise_temporal.paginas import ciclo_politico
from analise_temporal.paginas import cocorrencia
from analise_temporal.paginas import dashboard
from analise_temporal.paginas import indicacao
from analise_temporal.paginas import mobilidade
from analise_temporal.paginas import preenchimento
from analise_temporal.paginas import rotatividade
from analise_temporal.paginas import sazonalidade
from analise_temporal.paginas import transicoes


NAV_ITEMS = [
    ("/", "Visão Geral", "dashboard"),
    ("/busca", "Busca de Pessoa", "search"),
    ("/transicoes", "Fluxo e Transições", "right-left"),
    ("/mobilidade", "Mobilidade", "trending-up"),
    ("/rotatividade", "Rotatividade por Órgão", "building"),
    ("/sazonalidade", "Sazonalidade", "calendar"),
    ("/ciclo-politico", "Ciclo Político", "bar-chart-2"),
    ("/preenchimento", "Tempo de Preenchimento", "clock"),
    ("/indicacao", "Indicação vs Carreira", "check-square"),
    ("/anomalias", "Anomalias", "alert-triangle"),
    ("/coccurrencia", "Co-ocorrência", "layers"),
]

PAGES = {
    "/": (dashboard, "Visão Geral"),
    "/busca": (busca, "Busca de Pessoa"),
    "/transicoes": (transicoes, "Fluxo e Transições"),
    "/mobilidade": (mobilidade, "Mobilidade"),
    "/rotatividade": (rotatividade, "Rotatividade por Órgão"),
    "/sazonalidade": (sazonalidade, "Sazonalidade"),
    "/ciclo-politico": (ciclo_politico, "Ciclo Político"),
    "/preenchimento": (preenchimento, "Tempo de Preenchimento"),
    "/indicacao": (indicacao, "Indicação vs Carreira"),
    "/anomalias": (anomalias, "Anomalias"),
    "/coccurrencia": (cocorrencia, "Co-ocorrência"),
}

ICONS = {
    "dashboard": "\u2302",
    "search": "\u2315",
    "users": "\u263c",
    "right-left": "\u2194",
    "trending-up": "\u2197",
    "building": "\u2302",
    "calendar": "\u2630",
    "bar-chart-2": "\u2261",
    "clock": "\u23f1",
    "users": "\u263c",
    "check-square": "\u2611",
    "alert-triangle": "\u26a0",
    "layers": "\u2637",
}


def _nav_link(path, label, icon):
    return dcc.Link(
        html.Div(
            [html.Span(icon, className="nav-icon"), html.Span(label, className="nav-label")],
            className="nav-item",
        ),
        href=path,
        style={"textDecoration": "none"},
    )


def create_sidebar():
    links = [_nav_link(path, label, ICONS.get(icon_key, "\u25cf")) for path, label, icon_key in NAV_ITEMS]
    return html.Div(
        id="sidebar",
        className="open",
        children=[
            html.Div(
                [
                    html.Span("DOU-RJ", className="sidebar-title"),
                    html.Button("\u2630", id="sidebar-toggle",
                                style={"background": "none", "border": "none", "color": "#f9fafb",
                                       "fontSize": "18px", "cursor": "pointer", "padding": "0 16px"}),
                ],
                className="sidebar-header",
            ),
            html.Div(links, className="sidebar-links"),
        ],
    )


app = Dash(
    __name__,
    suppress_callback_exceptions=True,
    external_stylesheets=["https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;500;700&display=swap"],
)
server = app.server
app.title = "DOU RJ - Analise Temporal de Publicacoes"

app.layout = html.Div(
    style={"display": "flex", "minHeight": "100vh", "backgroundColor": "#f3f4f6", "fontFamily": "Roboto, sans-serif"},
    children=[
        dcc.Store(id="sidebar-state", data="open"),
        create_sidebar(),
        html.Div(
            id="page-content",
            className="content-open",
            style={"flex": "1", "padding": "24px", "boxSizing": "border-box"},
        ),
        dcc.Location(id="url", refresh="callback"),
    ],
)


@app.callback(
    Output("sidebar", "className"),
    Output("page-content", "className"),
    Output("sidebar-state", "data"),
    Input("sidebar-toggle", "n_clicks"),
    State("sidebar-state", "data"),
    prevent_initial_call=True,
)
def toggle_sidebar(_, state):
    if state == "open":
        return "closed", "content-closed", "closed"
    return "open", "content-open", "open"


@app.callback(Output("page-content", "children"), Input("url", "pathname"))
def render_page(pathname):
    pathname = pathname.rstrip("/") or "/"
    page_module, _ = PAGES.get(pathname, (None, None))
    if page_module is None:
        page_module, _ = PAGES["/"]
    return page_module.create_layout()


for pathname, (page_module, _) in PAGES.items():
    if hasattr(page_module, "register_callbacks"):
        page_module.register_callbacks(app)


@server.get("/healthz")
def healthz():
    return {"status": "ok"}


if __name__ == "__main__":
    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", "8052"))
    app.run(host=host, port=port, debug=False, use_reloader=False)
