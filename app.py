from __future__ import annotations

import os

from dash import Dash, Input, Output, dcc, html

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
        html.Div(
            id="sidebar-style",
            children=[
                html.Style("""
                    #sidebar { width:240px; min-width:240px; background-color:#1f2937; color:#f9fafb;
                               padding:20px 0; height:100vh; position:fixed; top:0; left:0; overflow-y:auto;
                               display:flex; flex-direction:column; transition:width 0.2s ease, min-width 0.2s ease; }
                    #sidebar.closed { width:50px; min-width:50px; }
                    .sidebar-header { display:flex; align-items:center; gap:8px; padding:0 16px 20px 16px;
                                      border-bottom:1px solid #374151; margin-bottom:12px; }
                    #sidebar.closed .sidebar-header { justify-content:center; padding:0 0 20px 0; }
                    .sidebar-title { font-size:20px; font-weight:bold; flex:1; }
                    #sidebar.closed .sidebar-title { display:none; }
                    .sidebar-links { display:flex; flex-direction:column; gap:2px; }
                    #sidebar.closed .sidebar-links { align-items:center; }
                    .nav-item { display:flex; align-items:center; gap:10px; padding:10px 16px; color:#d1d5db;
                                border-radius:6px; cursor:pointer; white-space:nowrap; overflow:hidden;
                                transition:background 0.15s; }
                    .nav-item:hover { background:#374151; }
                    #sidebar.closed .nav-item { padding:10px 0; justify-content:center; }
                    #sidebar.closed .nav-label { display:none; }
                    .nav-icon { font-size:16px; flex-shrink:0; }
                    .content-open { margin-left:240px; }
                    .content-closed { margin-left:50px; }
                    #page-content { flex:1; padding:24px; box-sizing:border-box; transition:margin-left 0.2s ease; }
                """)
            ],
        ),
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
