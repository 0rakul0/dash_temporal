from __future__ import annotations

import os

from dash import Dash, Input, Output, dcc, html

from analise_temporal.paginas import anomalias
from analise_temporal.paginas import carreiras
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
    ("/transicoes", "Fluxo e Transições", "right-left"),
    ("/mobilidade", "Mobilidade", "trending-up"),
    ("/rotatividade", "Rotatividade por Órgão", "building"),
    ("/sazonalidade", "Sazonalidade", "calendar"),
    ("/ciclo-politico", "Ciclo Político", "bar-chart-2"),
    ("/preenchimento", "Tempo de Preenchimento", "clock"),
    ("/carreiras", "Carreiras Individuais", "users"),
    ("/indicacao", "Indicação vs Carreira", "check-square"),
    ("/anomalias", "Anomalias", "alert-triangle"),
    ("/coccurrencia", "Co-ocorrência", "layers"),
]

PAGES = {
    "/": (dashboard, "Visão Geral"),
    "/transicoes": (transicoes, "Fluxo e Transições"),
    "/mobilidade": (mobilidade, "Mobilidade"),
    "/rotatividade": (rotatividade, "Rotatividade por Órgão"),
    "/sazonalidade": (sazonalidade, "Sazonalidade"),
    "/ciclo-politico": (ciclo_politico, "Ciclo Político"),
    "/preenchimento": (preenchimento, "Tempo de Preenchimento"),
    "/carreiras": (carreiras, "Carreiras Individuais"),
    "/indicacao": (indicacao, "Indicação vs Carreira"),
    "/anomalias": (anomalias, "Anomalias"),
    "/coccurrencia": (cocorrencia, "Co-ocorrência"),
}

ICONS = {
    "dashboard": "\u2302",
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


def create_sidebar():
    links = []
    for path, label, icon_key in NAV_ITEMS:
        icon = ICONS.get(icon_key, "\u25cf")
        links.append(
            dcc.Link(
                html.Div(
                    f"{icon}  {label}",
                    style={
                        "padding": "10px 16px",
                        "color": "#d1d5db",
                        "textDecoration": "none",
                        "fontSize": "14px",
                        "borderRadius": "6px",
                        "transition": "background 0.15s",
                        "cursor": "pointer",
                    },
                ),
                href=path,
                style={"textDecoration": "none"},
            )
        )
    return html.Div(
        style={
            "width": "240px",
            "minWidth": "240px",
            "backgroundColor": "#1f2937",
            "color": "#f9fafb",
            "padding": "20px 0",
            "height": "100vh",
            "position": "fixed",
            "top": 0,
            "left": 0,
            "overflowY": "auto",
            "display": "flex",
            "flexDirection": "column",
        },
        children=[
            html.Div(
                "DOU-RJ",
                style={
                    "fontSize": "20px",
                    "fontWeight": "bold",
                    "padding": "0 16px 20px 16px",
                    "borderBottom": "1px solid #374151",
                    "marginBottom": "12px",
                },
            ),
            html.Div(links, style={"display": "flex", "flexDirection": "column", "gap": "2px"}),
        ],
    )


app = Dash(__name__, suppress_callback_exceptions=True)
server = app.server
app.title = "DOU RJ - Analise Temporal de Publicacoes"

app.layout = html.Div(
    style={"display": "flex", "minHeight": "100vh", "backgroundColor": "#f3f4f6"},
    children=[
        create_sidebar(),
        html.Div(
            id="page-content",
            style={
                "marginLeft": "240px",
                "flex": "1",
                "padding": "24px",
                "maxWidth": "calc(100% - 240px)",
                "boxSizing": "border-box",
            },
        ),
        dcc.Location(id="url", refresh="callback"),
    ],
)


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
