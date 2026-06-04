from __future__ import annotations

from dash import Input, Output, State, ctx, dcc, html

from analise_temporal.services import dados
from analise_temporal.services.graficos import (
    fig_fluxo_por_governo,
    fig_orgaos_por_governo,
    fig_saldo_por_governo,
    fig_serie_temporal_governo,
    fig_timeline_governo,
    periodo_anos,
    periodo_movimentacoes,
    tabela_resumo_governos,
)


DATA_SOURCE_URL = "https://github.com/0rakul0/exoneracoes_nomeacoes_dou"

PANEL_STYLE = {
    "backgroundColor": "white",
    "border": "1px solid #e5e7eb",
    "borderRadius": "8px",
    "padding": "16px",
}

MUTED_TEXT = {"color": "#4b5563", "fontSize": "14px", "lineHeight": "1.45"}


def opcoes_iniciais():
    df = dados.df
    df_mov = dados.df_mov
    estados = sorted(df_mov["estado"].dropna().astype(str).unique().tolist())
    anos = sorted(
        set(df["ano"].dropna().astype(int).unique().tolist()).union(
            set(df_mov["ano"].dropna().astype(int).unique().tolist())
        )
    )
    orgaos = sorted(
        set(df["orgao"].dropna().astype(str).unique().tolist()).union(
            set(df_mov["orgao"].dropna().astype(str).unique().tolist())
        )
    )
    representantes = sorted(
        set(df["representante_origem"].dropna().astype(str).unique().tolist()).union(
            set(df_mov["representante_origem"].dropna().astype(str).unique().tolist())
        )
    )
    return estados, anos, orgaos, representantes


def create_layout():
    estados, anos, orgaos, governadores_edicao = opcoes_iniciais()
    ano_min = min(anos) if anos else ""
    ano_max = max(anos) if anos else ""

    return html.Div(
        style={
            "fontFamily": "Arial, sans-serif",
            "padding": "24px",
            "backgroundColor": "#f7f7f7",
            "color": "#111827",
        },
        children=[
            html.Div(
                className="dashboard-shell",
                style={"maxWidth": "1560px", "margin": "0 auto"},
                children=[
                    header_section(ano_min, ano_max),
                    context_tiles(),
                    state_tabs(estados),
                    reload_bar(),
                    filters(anos, governadores_edicao, orgaos),
                    metric_cards_container(),
                    html.Div(id="insights_filtros", style={"marginBottom": "16px"}),
                    explainer(
                        "Serie temporal",
                        (
                            "Mostra a evolucao mensal por governo ou representante. Nomeacoes ficam "
                            "acima do eixo; exoneracoes ficam abaixo para destacar entradas e saidas "
                            "no mesmo tempo."
                        ),
                    ),
                    html.Div(style={"marginTop": "10px"}, children=[dcc.Graph(id="serie_temporal_governo")]),
                    html.Div(
                        className="chart-grid-two",
                        style={
                            "display": "grid",
                            "gridTemplateColumns": "1fr 1fr",
                            "gap": "16px",
                            "marginTop": "16px",
                        },
                        children=[dcc.Graph(id="fluxo_governos"), dcc.Graph(id="saldo_governos")],
                    ),
                    explainer(
                        "Timeline e orgaos",
                        (
                            "A timeline mostra anos ou meses de maior intensidade administrativa. "
                            "O ranking por orgao aponta onde a rotatividade se concentra no recorte selecionado."
                        ),
                    ),
                    html.Div(style={"marginTop": "10px"}, children=[dcc.Graph(id="timeline_governo")]),
                    html.Div(style={"marginTop": "16px"}, children=[dcc.Graph(id="orgaos_governo")]),
                    html.Div(
                        style={"marginTop": "16px"},
                        children=[
                            html.H3("Resumo por Governo", style={"marginBottom": "10px"}),
                            html.Div(id="tabela_governos"),
                        ],
                    ),
                    methodology_details(),
                ],
            )
        ],
    )


def header_section(ano_min, ano_max):
    return html.Div(
        className="dashboard-hero",
        style={
            "display": "grid",
            "gridTemplateColumns": "minmax(0, 1.45fr) minmax(320px, 0.9fr)",
            "gap": "16px",
            "alignItems": "stretch",
            "marginBottom": "16px",
        },
        children=[
            html.Div(
                style=PANEL_STYLE | {"padding": "20px"},
                children=[
                    html.Div(
                        "Base publica de movimentacoes administrativas",
                        style={"fontSize": "13px", "fontWeight": "bold", "color": "#1f5eff"},
                    ),
                    html.H1(
                        "Exoneracoes e nomeacoes no Diario Oficial do RJ",
                        style={"fontSize": "30px", "margin": "8px 0 10px 0", "letterSpacing": "0"},
                    ),
                    html.P(
                        (
                            "Este painel acompanha atos de NOMEAR e EXONERAR extraidos do Diario "
                            "Oficial do Estado do Rio de Janeiro. A leitura combina volume, saldo "
                            "liquido, orgaos mais movimentados e evolucao temporal "
                            f"no periodo disponivel ({ano_min}-{ano_max})."
                        ),
                        style=MUTED_TEXT | {"margin": "0 0 14px 0"},
                    ),
                    html.A(
                        "Ver repositorio da base de dados",
                        href=DATA_SOURCE_URL,
                        target="_blank",
                        style={"color": "#1f5eff", "fontWeight": "bold", "textDecoration": "none"},
                    ),
                ],
            ),
            html.Div(
                style=PANEL_STYLE,
                children=[
                    html.H3("Como a base e produzida", style={"margin": "0 0 10px 0"}),
                    html.Ul(
                        style=MUTED_TEXT | {"paddingLeft": "18px", "margin": 0},
                        children=[
                            html.Li("Edicoes oficiais sao convertidas para Markdown com Docling."),
                            html.Li("O parser identifica atos de nomeacao e exoneracao."),
                            html.Li("Cada ato guarda data, caderno, pessoa, cargo, orgao, trecho e URL."),
                            html.Li("A coleta inicial usa o portal IOERJ/DOERJ e preserva CSVs auditaveis."),
                        ],
                    ),
                ],
            ),
        ],
    )


def context_tiles():
    return html.Div(
        className="context-grid",
        style={
            "display": "grid",
            "gridTemplateColumns": "repeat(4, minmax(0, 1fr))",
            "gap": "12px",
            "marginBottom": "18px",
        },
        children=[
            info_tile("O que medir", "Entradas, saidas, saldo liquido e rotatividade por governo, orgao e ano."),
            info_tile("Leitura central", "Nomeacoes entram como fluxo positivo; exoneracoes aparecem como saidas."),
            info_tile("Uso civico", "A base ajuda auditorias exploratorias, jornalismo de dados e estudos historicos."),
            info_tile("Cuidado", "O parser e heuristico; resultados sensiveis pedem validacao por amostragem."),
        ],
    )


def state_tabs(estados):
    return dcc.Tabs(
        id="filtro_estado",
        value=estados[0] if estados else None,
        children=[dcc.Tab(label=estado, value=estado) for estado in estados],
        style={"marginBottom": "16px"},
    )


def reload_bar():
    return html.Div(
        style={"display": "flex", "alignItems": "center", "gap": "12px", "marginBottom": "16px"},
        children=[
            html.Button(
                "Recarregar base",
                id="recarregar_base",
                n_clicks=0,
                style={
                    "backgroundColor": "#1f5eff",
                    "border": "0",
                    "borderRadius": "6px",
                    "color": "white",
                    "cursor": "pointer",
                    "fontWeight": "bold",
                    "padding": "10px 14px",
                },
            ),
            html.Div(id="recarregar_status", style={"color": "#555", "fontSize": "13px"}),
        ],
    )


def filters(anos, governadores_edicao, orgaos):
    return html.Div(
        className="filters-grid",
        style={
            "display": "grid",
            "gridTemplateColumns": "1fr 1.8fr 1.6fr 1.4fr 1fr",
            "gap": "12px",
            "marginBottom": "20px",
        },
        children=[
            filter_box(
                "Ano",
                dcc.Dropdown(
                    id="filtro_ano",
                    options=[{"label": str(a), "value": a} for a in anos],
                    multi=True,
                    placeholder="Todos",
                ),
            ),
            filter_box(
                "Governo",
                dcc.Dropdown(
                    id="filtro_governador_edicao",
                    options=[{"label": a, "value": a} for a in governadores_edicao],
                    multi=True,
                    placeholder="Todos",
                ),
            ),
            filter_box(
                "Orgao",
                dcc.Dropdown(
                    id="filtro_orgao",
                    options=[{"label": o, "value": o} for o in orgaos],
                    multi=True,
                    placeholder="Todos",
                ),
            ),
            filter_box(
                "Autoria do ato",
                dcc.Dropdown(
                    id="filtro_autoria",
                    options=[
                        {"label": "Governador", "value": "Governador"},
                        {"label": "Secretaria/Subsecretaria", "value": "Secretaria/Subsecretaria"},
                        {"label": "Outro/Nao identificado", "value": "Outro/Nao identificado"},
                    ],
                    multi=True,
                    placeholder="Todas",
                ),
            ),
            filter_box(
                "Movimentacao",
                dcc.Dropdown(
                    id="filtro_tipo_ato",
                    options=[
                        {"label": "Exoneracoes", "value": "exoneracao"},
                        {"label": "Nomeacoes", "value": "nomeacao"},
                    ],
                    multi=True,
                    placeholder="Todos",
                ),
            ),
        ],
    )


def metric_cards_container():
    return html.Div(
        id="cards",
        className="metrics-grid",
        style={
            "display": "grid",
            "gridTemplateColumns": "repeat(7, minmax(0, 1fr))",
            "gap": "12px",
            "marginBottom": "16px",
        },
    )


def filter_box(label, control):
    return html.Div(
        children=[
            html.Label(label, style={"fontWeight": "bold", "fontSize": "13px", "color": "#374151"}),
            control,
        ]
    )


def info_tile(title, text):
    return html.Div(
        style=PANEL_STYLE,
        children=[
            html.Div(title, style={"fontWeight": "bold", "marginBottom": "6px"}),
            html.Div(text, style=MUTED_TEXT),
        ],
    )


def explainer(title, text):
    return html.Div(
        style=PANEL_STYLE | {"padding": "14px 16px", "marginTop": "16px"},
        children=[
            html.Div(title, style={"fontWeight": "bold", "marginBottom": "4px"}),
            html.Div(text, style=MUTED_TEXT),
        ],
    )


def methodology_details():
    return html.Details(
        style=PANEL_STYLE | {"marginTop": "16px"},
        children=[
            html.Summary(
                "Metodologia, campos e limitacoes da base",
                style={"cursor": "pointer", "fontWeight": "bold"},
            ),
            html.Div(
                className="methodology-grid",
                style={
                    "display": "grid",
                    "gridTemplateColumns": "1fr 1fr 1fr",
                    "gap": "16px",
                    "marginTop": "14px",
                },
                children=[
                    methodology_block(
                        "Fluxo de coleta",
                        [
                            "Consulta o calendario online da IOERJ/DOERJ.",
                            "Reutiliza Markdown existente ou converte PDF oficial.",
                            "Procura atos NOMEAR e EXONERAR no texto convertido.",
                            "Atualiza CSVs anuais e analises temporais por UF.",
                        ],
                    ),
                    methodology_block(
                        "Campos principais",
                        [
                            "estado, diario, data_publicacao e caderno.",
                            "tipo_ato, nome, cargo, orgao e assinante.",
                            "trecho e fonte_url para rastreabilidade.",
                            "arquivo_markdown para auditoria da extracao.",
                        ],
                    ),
                    methodology_block(
                        "Limites conhecidos",
                        [
                            "O parser atual e heuristico.",
                            "A cobertura inicial prioriza Rio de Janeiro.",
                            "Edicoes pre-2008 podem exigir outra estrategia.",
                            "Amostragens humanas devem orientar ajustes futuros.",
                        ],
                    ),
                ],
            ),
            html.P(
                (
                    "Proximos passos sugeridos pela propria base: separar atos coletivos de individuais, "
                    "melhorar extracao de cargo e orgao, registrar metricas por edicao e criar conectores "
                    "para outros estados."
                ),
                style=MUTED_TEXT | {"marginTop": "12px"},
            ),
        ],
    )


def methodology_block(title, items):
    return html.Div(
        children=[
            html.Div(title, style={"fontWeight": "bold", "marginBottom": "8px"}),
            html.Ul(
                style=MUTED_TEXT | {"paddingLeft": "18px", "margin": 0},
                children=[html.Li(item) for item in items],
            ),
        ],
    )


def resumo_recorte(dff_mov):
    if dff_mov.empty:
        return html.Div(
            style=PANEL_STYLE,
            children=[
                html.Div("Leitura do recorte", style={"fontWeight": "bold", "marginBottom": "4px"}),
                html.Div("Sem dados para os filtros selecionados.", style=MUTED_TEXT),
            ],
        )

    total = len(dff_mov)
    pessoas = dff_mov["pessoa"].nunique()
    anos = sorted(int(ano) for ano in dff_mov["ano"].dropna().unique())
    periodo = f"{anos[0]}-{anos[-1]}" if len(anos) > 1 else str(anos[0]) if anos else "sem periodo"

    por_governo = dff_mov["representante_origem"].value_counts()
    governo_top = por_governo.index[0] if not por_governo.empty else "Nao identificado"
    governo_top_total = int(por_governo.iloc[0]) if not por_governo.empty else 0

    por_orgao = dff_mov["orgao"].dropna().astype(str).str.strip()
    por_orgao = por_orgao[por_orgao != ""].value_counts()
    orgao_top = por_orgao.index[0] if not por_orgao.empty else "Nao identificado"
    orgao_top_total = int(por_orgao.iloc[0]) if not por_orgao.empty else 0

    nomeacoes = int((dff_mov["tipo_ato"] == "nomeacao").sum())
    exoneracoes = int((dff_mov["tipo_ato"] == "exoneracao").sum())
    saldo = nomeacoes - exoneracoes
    direcao = "mais entradas que saidas" if saldo >= 0 else "mais saidas que entradas"

    items = [
        ("Periodo", periodo),
        ("Registros filtrados", f"{total:,}".replace(",", ".")),
        ("Pessoas unicas", f"{pessoas:,}".replace(",", ".")),
        ("Maior volume por governo", f"{governo_top} ({governo_top_total:,})".replace(",", ".")),
        ("Orgao mais citado", f"{orgao_top} ({orgao_top_total:,})".replace(",", ".")),
        ("Saldo do recorte", f"{saldo:,} ({direcao})".replace(",", ".")),
    ]

    return html.Div(
        style=PANEL_STYLE,
        children=[
            html.Div("Leitura do recorte filtrado", style={"fontWeight": "bold", "marginBottom": "10px"}),
            html.Div(
                className="insights-grid",
                style={
                    "display": "grid",
                    "gridTemplateColumns": "repeat(3, minmax(0, 1fr))",
                    "gap": "10px",
                },
                children=[
                    html.Div(
                        children=[
                            html.Div(label, style={"fontSize": "12px", "color": "#6b7280"}),
                            html.Div(value, style={"fontWeight": "bold", "marginTop": "2px"}),
                        ]
                    )
                    for label, value in items
                ],
            ),
        ],
    )


def card(titulo, valor):
    return html.Div(
        style={
            "backgroundColor": "white",
            "padding": "16px",
            "borderRadius": "8px",
            "boxShadow": "0 2px 8px rgba(0,0,0,0.08)",
        },
        children=[
            html.Div(titulo, style={"fontSize": "13px", "color": "#666"}),
            html.Div(valor, style={"fontSize": "24px", "fontWeight": "bold"}),
        ],
    )


def register_callbacks(app):
    @app.callback(
        Output("filtro_governador_edicao", "options"),
        Output("filtro_governador_edicao", "value"),
        Input("filtro_estado", "value"),
        Input("recarregar_base", "n_clicks"),
        State("filtro_governador_edicao", "value"),
    )
    def atualizar_opcoes_representante(estado, recarregar_clicks, selecionados):
        base = dados.df_mov.copy()
        if estado:
            base = base[base["estado"] == estado]
        representantes = sorted(base["representante_origem"].dropna().astype(str).unique().tolist())
        options = [{"label": representante, "value": representante} for representante in representantes]

        selecionados = selecionados or []
        selecionados_validos = [valor for valor in selecionados if valor in representantes]
        return options, selecionados_validos

    @app.callback(
        Output("cards", "children"),
        Output("fluxo_governos", "figure"),
        Output("saldo_governos", "figure"),
        Output("serie_temporal_governo", "figure"),
        Output("timeline_governo", "figure"),
        Output("orgaos_governo", "figure"),
        Output("tabela_governos", "children"),
        Output("insights_filtros", "children"),
        Output("recarregar_status", "children"),
        Input("recarregar_base", "n_clicks"),
        Input("filtro_estado", "value"),
        Input("filtro_ano", "value"),
        Input("filtro_governador_edicao", "value"),
        Input("filtro_orgao", "value"),
        Input("filtro_autoria", "value"),
        Input("filtro_tipo_ato", "value"),
    )
    def update(recarregar_clicks, estado, ano, governador_edicao, orgao, autoria, tipo_ato):
        reload_status = ""
        if recarregar_clicks and ctx.triggered_id == "recarregar_base":
            dados.df, dados.df_mov = dados.reload_analysis_base()
            reload_status = f"Base recarregada: {len(dados.df_mov):,} movimentacoes".replace(",", ".")

        dff_mov = dados.df_mov.copy()

        if estado:
            dff_mov = dff_mov[dff_mov["estado"] == estado]

        periodo_top_orgaos = periodo_anos(ano) if ano else periodo_movimentacoes(dff_mov)

        if ano:
            dff_mov = dff_mov[dff_mov["ano"].isin(ano)]

        if governador_edicao:
            dff_mov = dff_mov[dff_mov["representante_origem"].isin(governador_edicao)]

        if orgao:
            dff_mov = dff_mov[dff_mov["orgao"].isin(orgao)]

        if autoria:
            dff_mov = dff_mov[dff_mov["autoria_ato"].isin(autoria)]

        if tipo_ato:
            dff_mov = dff_mov[dff_mov["tipo_ato"].isin(tipo_ato)]

        total = len(dff_mov)
        pessoas = dff_mov["pessoa"].nunique() if not dff_mov.empty else 0
        total_exoneracoes = int((dff_mov["tipo_ato"] == "exoneracao").sum()) if not dff_mov.empty else 0
        total_nomeacoes = int((dff_mov["tipo_ato"] == "nomeacao").sum()) if not dff_mov.empty else 0
        total_governador = int((dff_mov["autoria_ato"] == "Governador").sum()) if not dff_mov.empty else 0
        total_secretarias = int((dff_mov["autoria_ato"] == "Secretaria/Subsecretaria").sum()) if not dff_mov.empty else 0
        saldo = total_nomeacoes - total_exoneracoes

        cards = [
            card("Atos no governo", f"{total:,}".replace(",", ".")),
            card("Atos do governador", f"{total_governador:,}".replace(",", ".")),
            card("Atos de secretarias", f"{total_secretarias:,}".replace(",", ".")),
            card("Exoneracoes", f"{total_exoneracoes:,}".replace(",", ".")),
            card("Nomeacoes", f"{total_nomeacoes:,}".replace(",", ".")),
            card("Saldo", f"{saldo:,}".replace(",", ".")),
            card("Pessoas unicas", f"{pessoas:,}".replace(",", ".")),
        ]

        return (
            cards,
            fig_fluxo_por_governo(dff_mov),
            fig_saldo_por_governo(dff_mov),
            fig_serie_temporal_governo(dff_mov),
            fig_timeline_governo(dff_mov),
            fig_orgaos_por_governo(dff_mov, periodo_top_orgaos),
            tabela_resumo_governos(dff_mov),
            resumo_recorte(dff_mov),
            reload_status,
        )
