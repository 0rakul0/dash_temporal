from __future__ import annotations

import re
import unicodedata

from dash import Input, Output, State, dcc, html
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from analise_temporal.services import dados
from analise_temporal.services.graficos import fig_top_pessoas


def _fold(s: str) -> str:
    return unicodedata.normalize("NFKD", s).encode("ascii", errors="ignore").decode("ascii")

PANEL_STYLE = {
    "backgroundColor": "white",
    "border": "1px solid #e5e7eb",
    "borderRadius": "8px",
    "padding": "16px",
}
MUTED_TEXT = {"color": "#4b5563", "fontSize": "14px", "lineHeight": "1.45"}

_NOISE_PAT = re.compile(
    r"^(?:"
    r"CORONEL|MAJOR\b|MAJ\b|CAPIT[AÃ]O|TENENTECORONEL|TENENTE\b|TEN\s+CEL\b|SUBTENENTE|SARGENTO|CABO|SOLDADO|ALMIRANTE|GENERAL|"
    r"DELEGADO|DEFENSOR|PROCURADOR|PERITO|INSPETOR\w*|FISCAL|AGENTE|ANALISTA|T[Cc]NICO|AUXILIAR|"
    r"SECRET[AÃ]RIO|SUBSECRET[AÃ]RIO|DIRETOR|PRESIDENTE|COORDENADOR|GERENTE|CHEFE|ASSESSOR|"
    r"AUDITOR|CONTADOR|ADVOGADO|MEDICO|ENFERMEIRO|DENTISTA|FARMACEUTICO|TECNICO|"
    r"POLICIAL|ESPECIALISTA|"
    r"ANTERIORMENTE|NOS\s+TERMOS|E\s+NOS\s+TERMOS|ID\.?\s*FUNCIONAL|REGULAMENTADA|CLASSE\s+INICIAL"
    r")\b",
    re.IGNORECASE,
)


def _is_noise(name: str) -> bool:
    if len(name) < 8:
        return True
    if _NOISE_PAT.match(name):
        return True
    return False


pessoas = [p for p in dados.df_mov["pessoa"].unique() if not _is_noise(p)]
pessoas_fold = [_fold(p) for p in pessoas]
vectorizer = TfidfVectorizer(analyzer="char", ngram_range=(1, 3), lowercase=True)
tfidf_matrix = vectorizer.fit_transform(pessoas_fold)


def _search(query: str, top_n: int = 30) -> list[tuple[str, float]]:
    query_vec = vectorizer.transform([_fold(query)])
    sim = cosine_similarity(query_vec, tfidf_matrix).flatten()
    best = sim.argsort()[-top_n:][::-1]
    return [(pessoas[i], float(sim[i])) for i in best if sim[i] > 0]


def create_layout():
    dff_mov = dados.df_mov.copy()
    dff_clean = dff_mov[~dff_mov["pessoa"].apply(_is_noise)]

    return html.Div(
        style={"maxWidth": "1200px", "margin": "0 auto"},
        children=[
            html.H2("Busca de Pessoa", style={"marginTop": 0}),
            html.P(
                "Pesquise pelo nome para ver a trajetória completa — "
                "independente de governo, órgão ou secretaria.",
                style=MUTED_TEXT,
            ),
            html.Div(
                style={**PANEL_STYLE, "marginTop": "16px"},
                children=[
                    html.Div(style={"display": "flex", "gap": "16px", "alignItems": "flex-end", "flexWrap": "wrap"},
                        children=[
                            html.Div(style={"flex": "1", "minWidth": "280px"},
                                children=[
                                    html.Label("Nome:", style={"fontWeight": 600, "marginBottom": "6px", "display": "block"}),
                                    dcc.Dropdown(
                                        id="busca-dropdown",
                                        placeholder="Digite ao menos 3 caracteres...",
                                        options=[],
                                        value=None,
                                        clearable=True,
                                    ),
                                ]
                            ),
                            html.Div(id="busca-stats", style=MUTED_TEXT),
                        ]
                    ),
                ],
            ),
            html.Div(id="busca-trajetoria", style={"marginTop": "16px"}),
            html.Div(style={"marginTop": "24px", **PANEL_STYLE},
                children=[dcc.Graph(figure=fig_top_pessoas(dff_clean))]),
        ],
    )


def register_callbacks(app):

    @app.callback(
        Output("busca-dropdown", "options"),
        Input("busca-dropdown", "search_value"),
        State("busca-dropdown", "value"),
    )
    def update_options(search_value, current_value):
        if not search_value or len(search_value.strip()) < 3:
            if current_value:
                return [{"label": current_value, "value": current_value}]
            return []
        results = _search(search_value.strip())
        return [{"label": f"{nome}  ({score:.0%})", "value": nome} for nome, score in results]

    @app.callback(
        Output("busca-trajetoria", "children"),
        Output("busca-stats", "children"),
        Input("busca-dropdown", "value"),
    )
    def show_trajetoria(pessoa):
        if not pessoa:
            return "", ""

        dff = dados.df_mov[dados.df_mov["pessoa"] == pessoa].copy()
        dff = dff.sort_values("data_movimentacao")

        total_atos = len(dff)
        governos = dff["governador_edicao"].nunique()
        orgaos = dff["orgao"].nunique()
        stats = f"{total_atos} atos | {governos} {'governos' if governos > 1 else 'governo'} | {orgaos} {'órgãos' if orgaos > 1 else 'órgão'}"

        if "cargo" in dff.columns:
            cols = ["data_movimentacao", "tipo_ato", "orgao", "cargo", "governador_edicao"]
        else:
            cols = ["data_movimentacao", "tipo_ato", "orgao", "cargo_assinante", "governador_edicao"]
        tabela_data = dff[cols].copy()
        tabela_data["data_movimentacao"] = tabela_data["data_movimentacao"].dt.date
        tabela_data.columns = ["Data", "Tipo", "Órgão", "Cargo", "Governo"]

        tabela = html.Div(
            style={**PANEL_STYLE, "marginTop": "8px", "overflowX": "auto"},
            children=[
                html.H4(f"Trajetória de {pessoa}", style={"marginTop": 0}),
                html.Table(
                    style={
                        "width": "100%",
                        "borderCollapse": "collapse",
                        "fontSize": "13px",
                    },
                    children=[
                        html.Thead(
                            html.Tr(
                                [
                                    html.Th(col, style=th_style)
                                    for col in tabela_data.columns
                                ]
                            )
                        ),
                        html.Tbody(
                            [
                                html.Tr(
                                    [
                                        html.Td(
                                            str(row[col]),
                                            style=td_style,
                                        )
                                        for col in tabela_data.columns
                                    ],
                                    style={
                                        "backgroundColor": (
                                            "#f0fdf4"
                                            if row["Tipo"] == "nomeacao"
                                            else "#fef2f2"
                                        )
                                    },
                                )
                                for _, row in tabela_data.iterrows()
                            ]
                        ),
                    ],
                ),
            ],
        )

        return tabela, stats


th_style = {
    "padding": "8px 12px",
    "textAlign": "left",
    "backgroundColor": "#f3f4f6",
    "borderBottom": "2px solid #d1d5db",
    "position": "sticky",
    "top": 0,
}

td_style = {
    "padding": "6px 12px",
    "borderBottom": "1px solid #e5e7eb",
    "whiteSpace": "nowrap",
}
