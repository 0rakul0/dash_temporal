from __future__ import annotations

import re

import networkx as nx
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dash import html

TOP_N_TRANSICOES = 30
TOP_N_ORGAOS = 10

def normalizar_orgao_para_grafico(orgao):
    if pd.isna(orgao):
        return "", ""

    orgao = str(orgao or "").strip()
    if not orgao or orgao.lower() in {"nan", "none", "null"}:
        return "", ""

    rotulo = re.sub(r"\s+", " ", orgao)
    rotulo = re.sub(r"\s*-\s*", " - ", rotulo)
    rotulo = re.sub(r"\s*/\s*", "/", rotulo).strip()

    chave = rotulo.lower()
    chave = re.sub(r"\s*-\s*", " ", chave)
    chave = re.sub(r"\s+", " ", chave).strip()
    return chave, rotulo


def adicionar_orgao_grafico(base):
    base = base.copy()
    orgaos_normalizados = base["orgao"].astype("str").apply(normalizar_orgao_para_grafico)
    base["orgao_chave"] = orgaos_normalizados.map(lambda item: item[0])
    base["orgao_rotulo"] = orgaos_normalizados.map(lambda item: item[1])
    base = base[base["orgao_chave"] != ""]

    if base.empty:
        base["orgao_grafico"] = pd.Series(dtype="object")
        return base

    rotulos = (
        base.groupby(["orgao_chave", "orgao_rotulo"], observed=True)
        .size()
        .reset_index(name="quantidade")
        .sort_values(["orgao_chave", "quantidade", "orgao_rotulo"], ascending=[True, False, True])
        .drop_duplicates("orgao_chave")
        .set_index("orgao_chave")["orgao_rotulo"]
    )
    base["orgao_grafico"] = base["orgao_chave"].map(rotulos)
    return base


def periodo_movimentacoes(dff_mov):
    if dff_mov.empty or "ano" not in dff_mov.columns:
        return "sem período"

    return periodo_anos(dff_mov["ano"].dropna().unique().tolist())


def periodo_anos(anos):
    anos_filtrados = sorted(int(ano) for ano in anos if pd.notna(ano))
    if not anos_filtrados:
        return "sem período"

    if len(anos_filtrados) == 1:
        return str(anos_filtrados[0])

    if anos_filtrados == list(range(anos_filtrados[0], anos_filtrados[-1] + 1)):
        return f"{anos_filtrados[0]}-{anos_filtrados[-1]}"

    return ", ".join(str(ano) for ano in anos_filtrados)

def construir_eventos(dff):
    eventos = []

    for _, row in dff.iterrows():
        pessoa = row["pessoa"]

        if pd.notna(row["data_exoneracao"]):
            eventos.append({
                "pessoa": pessoa,
                "data": row["data_exoneracao"],
                "estado": "E"
            })

        if pd.notna(row["data_nomeacao"]):
            eventos.append({
                "pessoa": pessoa,
                "data": row["data_nomeacao"],
                "estado": row["estado_N"]
            })

    ev = pd.DataFrame(eventos)

    if ev.empty:
        return ev, pd.DataFrame(columns=["estado", "prox_estado", "count"])

    ev["data"] = pd.to_datetime(ev["data"], errors="coerce")
    ev = ev.dropna(subset=["data"])
    ev = ev.sort_values(["pessoa", "data"])

    ev["prox_estado"] = ev.groupby("pessoa")["estado"].shift(-1)

    trans = (
        ev.dropna(subset=["prox_estado"])
        .groupby(["estado", "prox_estado"], observed=True)
        .size()
        .reset_index(name="count")
    )

    return ev, trans


def matriz_transicao(trans):
    if trans.empty:
        return pd.DataFrame(), pd.DataFrame()

    estados = sorted(set(trans["estado"]).union(set(trans["prox_estado"])))

    matriz = (
        trans.pivot(index="estado", columns="prox_estado", values="count")
        .reindex(index=estados, columns=estados, fill_value=0)
    )

    row_sums = matriz.sum(axis=1)
    matriz_prob = matriz.div(row_sums.replace(0, 1), axis=0)

    return matriz, matriz_prob


def estado_estacionario(mat_prob):
    if mat_prob.empty:
        return {}

    P = mat_prob.values.copy()

    if P.shape[0] == 0 or P.shape[0] != P.shape[1]:
        return {}

    row_sums = P.sum(axis=1)
    for i, s in enumerate(row_sums):
        if s == 0:
            P[i, i] = 1.0

    try:
        eigvals, eigvecs = np.linalg.eig(P.T)
        vec = eigvecs[:, np.isclose(eigvals, 1)]

        if vec.size == 0:
            return {}

        vec = vec.real[:, 0]
        vec = vec / vec.sum()

        return dict(zip(mat_prob.index.tolist(), vec))

    except Exception:
        return {}


# =====================================================
# FIGURES
# =====================================================
def fig_sankey(trans):
    if trans.empty:
        return go.Figure().update_layout(title="Sem dados para Sankey")

    trans = trans.sort_values("count", ascending=False).head(TOP_N_TRANSICOES)

    labels = sorted(set(trans["estado"]).union(set(trans["prox_estado"])))
    idx = {label: i for i, label in enumerate(labels)}

    fig = go.Figure(data=[go.Sankey(
        node=dict(
            pad=18,
            thickness=18,
            line=dict(color="black", width=0.4),
            label=labels
        ),
        link=dict(
            source=trans["estado"].map(idx),
            target=trans["prox_estado"].map(idx),
            value=trans["count"],
            customdata=trans[["estado", "prox_estado", "count"]],
            hovertemplate=(
                "De: %{customdata[0]}<br>"
                "Para: %{customdata[1]}<br>"
                "Volume: %{customdata[2]}<extra></extra>"
            )
        )
    )])

    fig.update_layout(
        title="Sankey de Transições",
        height=520,
        font_size=11
    )

    return fig


def fig_barras_movimentacoes(dff_mov):
    if dff_mov.empty:
        return go.Figure().update_layout(title="Sem dados para quantitativos")

    base = (
        dff_mov.dropna(subset=["ano"])
        .assign(ano=lambda data: data["ano"].astype(int))
        .groupby(["ano", "tipo_ato"], observed=True)
        .size()
        .reset_index(name="quantidade")
    )

    fig = px.bar(
        base,
        x="ano",
        y="quantidade",
        color="tipo_ato",
        barmode="group",
        text="quantidade",
        category_orders={"tipo_ato": ["exoneracao", "nomeacao"]},
        labels={
            "ano": "Ano",
            "quantidade": "Quantidade",
            "tipo_ato": "Tipo de ato",
        },
        title="Quantitativo de Exonerações e Nomeações por Ano",
    )

    fig.update_traces(texttemplate="%{text:,}", textposition="outside")
    fig.update_layout(
        height=520,
        bargap=0.28,
        bargroupgap=0.1,
        font=dict(size=10),
        title_font_size=18,
        uniformtext_minsize=10,
        uniformtext_mode="hide",
        yaxis_title="Quantidade de atos",
        xaxis=dict(dtick=1),
    )

    return fig


def fig_barras_movimentacoes_por_orgao(dff_mov):
    if dff_mov.empty:
        return go.Figure().update_layout(title="Sem dados para órgãos")

    periodo = periodo_movimentacoes(dff_mov)
    base = adicionar_orgao_grafico(dff_mov)

    if base.empty:
        return go.Figure().update_layout(title="Sem órgãos identificados para os filtros selecionados")

    ranking = (
        base.groupby("orgao_chave", observed=True)
        .size()
        .sort_values(ascending=False)
        .head(TOP_N_ORGAOS)
        .index
    )
    base = base[base["orgao_chave"].isin(ranking)]

    barras = (
        base.groupby(["orgao_chave", "orgao_grafico", "tipo_ato"], observed=True)
        .size()
        .reset_index(name="quantidade")
    )
    barras["fluxo"] = barras.apply(
        lambda row: -row["quantidade"] if row["tipo_ato"] == "exoneracao" else row["quantidade"],
        axis=1,
    )
    barras["rotulo"] = barras["quantidade"].map(lambda value: f"{value:,}".replace(",", "."))

    ordem_orgaos = (
        barras.assign(abs_fluxo=barras["fluxo"].abs())
        .groupby("orgao_grafico", observed=True)["abs_fluxo"]
        .sum()
        .sort_values()
        .index
        .tolist()
    )

    fig = px.bar(
        barras,
        x="fluxo",
        y="orgao_grafico",
        color="tipo_ato",
        orientation="h",
        text="rotulo",
        category_orders={
            "tipo_ato": ["exoneracao", "nomeacao"],
            "orgao_grafico": ordem_orgaos,
        },
        labels={
            "fluxo": "Saídas / Entradas",
            "orgao_grafico": "Órgão",
            "tipo_ato": "Tipo de ato",
        },
        title=f"Entradas e Saídas por Órgão - Top {TOP_N_ORGAOS} órgãos identificados ({periodo})",
    )

    fig.add_vline(x=0, line_width=1, line_color="#444")
    fig.update_layout(
        height=760,
        bargap=0.36,
        bargroupgap=0.1,
        font=dict(size=10),
        title_font_size=18,
        xaxis=dict(
            title="Exonerações à esquerda, nomeações à direita",
            tickformat=",d",
        ),
        yaxis_title="",
        legend_title_text="Tipo de ato",
    )

    return fig


def fig_sankey_animado_por_ano(dff):
    anos = sorted(dff["ano"].dropna().unique())

    if len(anos) == 0:
        return go.Figure().update_layout(title="Sem dados para Sankey animado")

    trans_por_ano = {}

    labels_global = set()

    for ano in anos:
        _, trans = construir_eventos(dff[dff["ano"] == ano])
        trans = trans.sort_values("count", ascending=False).head(TOP_N_TRANSICOES)
        trans_por_ano[ano] = trans

        labels_global.update(trans["estado"].tolist())
        labels_global.update(trans["prox_estado"].tolist())

    labels = sorted(labels_global)
    idx = {label: i for i, label in enumerate(labels)}

    def sankey_data(ano):
        trans = trans_por_ano[ano]

        return go.Sankey(
            node=dict(
                pad=18,
                thickness=18,
                line=dict(color="black", width=0.4),
                label=labels
            ),
            link=dict(
                source=trans["estado"].map(idx),
                target=trans["prox_estado"].map(idx),
                value=trans["count"],
                customdata=trans[["estado", "prox_estado", "count"]],
                hovertemplate=(
                    "Ano: " + str(int(ano)) + "<br>"
                    "De: %{customdata[0]}<br>"
                    "Para: %{customdata[1]}<br>"
                    "Volume: %{customdata[2]}<extra></extra>"
                )
            )
        )

    fig = go.Figure(data=[sankey_data(anos[0])])

    frames = [
        go.Frame(
            data=[sankey_data(ano)],
            name=str(int(ano))
        )
        for ano in anos
    ]

    fig.frames = frames

    fig.update_layout(
        title=f"Sankey Animado por Ano — {int(anos[0])}",
        height=560,
        font_size=11,
        updatemenus=[{
            "type": "buttons",
            "showactive": False,
            "buttons": [
                {
                    "label": "▶ Play",
                    "method": "animate",
                    "args": [None, {
                        "frame": {"duration": 900, "redraw": True},
                        "fromcurrent": True
                    }]
                },
                {
                    "label": "⏸ Pause",
                    "method": "animate",
                    "args": [[None], {
                        "frame": {"duration": 0, "redraw": False},
                        "mode": "immediate"
                    }]
                }
            ]
        }],
        sliders=[{
            "active": 0,
            "steps": [
                {
                    "label": str(int(ano)),
                    "method": "animate",
                    "args": [[str(int(ano))], {
                        "frame": {"duration": 500, "redraw": True},
                        "mode": "immediate"
                    }]
                }
                for ano in anos
            ]
        }]
    )

    return fig


def fig_timeline_eventos(dff):
    if dff.empty:
        return go.Figure().update_layout(title="Sem dados para timeline")

    timeline = (
        dff.groupby(["ano", "tempo_cluster"], observed=True)
        .size()
        .reset_index(name="eventos")
        .sort_values("ano")
    )

    fig = px.line(
        timeline,
        x="ano",
        y="eventos",
        color="tempo_cluster",
        markers=True,
        title="Timeline de Retornos por Ano e Tipo de Tempo"
    )

    fig.update_layout(height=420)

    return fig


def fig_timeline_movimentacoes(dff_mov):
    if dff_mov.empty:
        return go.Figure().update_layout(title="Sem dados para timeline de movimentações")

    base = dff_mov.dropna(subset=["data_movimentacao"]).copy()
    if base.empty:
        return go.Figure().update_layout(title="Sem datas válidas para timeline de movimentações")

    base["mes"] = base["data_movimentacao"].dt.to_period("M").dt.to_timestamp()
    timeline = (
        base.groupby(["mes", "tipo_ato"], observed=True)
        .size()
        .reset_index(name="quantidade")
        .sort_values("mes")
    )

    fig = px.bar(
        timeline,
        x="mes",
        y="quantidade",
        color="tipo_ato",
        barmode="group",
        text="quantidade",
        category_orders={"tipo_ato": ["exoneracao", "nomeacao"]},
        labels={
            "mes": "Mês",
            "quantidade": "Quantidade",
            "tipo_ato": "Tipo de ato",
        },
        title="Timeline de Exonerações e Nomeações",
    )

    fig.update_traces(texttemplate="%{text:,}", textposition="outside")
    fig.update_layout(
        height=460,
        bargap=0.28,
        bargroupgap=0.1,
        font=dict(size=10),
        title_font_size=18,
        uniformtext_minsize=9,
        uniformtext_mode="hide",
        yaxis_title="Quantidade de atos",
    )

    return fig


def fig_serie_temporal_governo(dff_mov):
    if dff_mov.empty:
        return go.Figure().update_layout(title="Sem dados para serie temporal")

    base = dff_mov.dropna(subset=["data_movimentacao"]).copy()
    if base.empty:
        return go.Figure().update_layout(title="Sem datas validas para serie temporal")

    base["periodo"] = base["data_movimentacao"].dt.to_period("M").dt.to_timestamp()
    serie = (
        base.groupby(["periodo", "representante_governo", "tipo_ato"], observed=True)
        .agg(
            quantidade=("tipo_ato", "size"),
            papeis=("governador_edicao", papeis_governo),
            origem=("origem_representante", origem_representante_agregada),
        )
        .reset_index()
        .sort_values(["representante_governo", "tipo_ato", "periodo"])
    )
    if serie.empty:
        return go.Figure().update_layout(title="Sem dados para serie temporal")

    governos = (
        serie.groupby("representante_governo", observed=True)["quantidade"]
        .sum()
        .sort_values(ascending=False)
        .index
        .tolist()
    )
    palette = px.colors.qualitative.Dark24 + px.colors.qualitative.Set2 + px.colors.qualitative.Plotly
    color_by_government = {
        governo: palette[index % len(palette)]
        for index, governo in enumerate(governos)
    }
    origin_by_government = serie.groupby("representante_governo", observed=True)["origem"].first().to_dict()

    fig = go.Figure()
    action_config = {
        "nomeacao": {"label": "Nomeacoes", "sign": 1, "dash": "solid"},
        "exoneracao": {"label": "Exoneracoes", "sign": -1, "dash": "dot"},
    }
    eixo_label = eixo_representante_label(dff_mov)

    for governo in governos:
        origem = origin_by_government.get(governo, origem_representante_governo(governo))
        if eixo_label == "Setor":
            short_government = governo
        else:
            short_government = f"{rotulo_representante_curto(governo)} ({origem})"
        for action_type in ["nomeacao", "exoneracao"]:
            current = serie[
                (serie["representante_governo"] == governo)
                & (serie["tipo_ato"] == action_type)
            ]
            if current.empty:
                continue

            config = action_config[action_type]
            current = current.set_index("periodo").sort_index()
            periodos = pd.date_range(current.index.min(), current.index.max(), freq="MS")
            current = current.reindex(periodos).rename_axis("periodo").reset_index()
            current["representante_governo"] = current["representante_governo"].fillna(governo)
            current["origem"] = current["origem"].fillna(origem)
            current["papeis"] = current["papeis"].fillna("")
            current["tipo_ato"] = current["tipo_ato"].fillna(action_type)
            signed_quantity = current["quantidade"] * config["sign"]
            fig.add_trace(
                go.Scatter(
                    x=current["periodo"],
                    y=signed_quantity,
                    mode="lines+markers",
                    connectgaps=False,
                    name=f"{short_government} - {config['label']}",
                    legendgroup=governo,
                    line=dict(
                        color=color_by_government[governo],
                        width=2.5,
                        dash=config["dash"],
                    ),
                    marker=dict(size=6, color=color_by_government[governo]),
                    customdata=current[["representante_governo", "origem", "papeis", "tipo_ato", "quantidade"]],
                    hovertemplate=(
                        "Periodo: %{x|%Y-%m}<br>"
                        f"{eixo_label}: %{{customdata[0]}}<br>"
                        "Origem: %{customdata[1]}<br>"
                        "Papel na edicao: %{customdata[2]}<br>"
                        "Movimentacao: %{customdata[3]}<br>"
                        "Quantidade: %{customdata[4]:,}<extra></extra>"
                    ),
                )
            )

    max_quantity = int(serie["quantidade"].max())
    upper_tick = max(1, max_quantity)
    tick_step = max(1, int(np.ceil(upper_tick / 4)))
    positive_ticks = list(range(0, upper_tick + tick_step, tick_step))
    tickvals = sorted({-value for value in positive_ticks if value} | set(positive_ticks))

    fig.add_hline(
        y=0,
        line_width=2,
        line_color="#222",
        annotation_text="tempo",
        annotation_position="bottom right",
    )
    fig.update_layout(
        title=f"Serie Temporal por {eixo_label} - Nomeacoes Acima e Exoneracoes Abaixo",
        height=700,
        hovermode="closest",
        legend_title_text=f"{eixo_label}, origem e movimentacao",
        legend=dict(
            orientation="v",
            yanchor="top",
            y=1,
            xanchor="left",
            x=1.02,
            groupclick="toggleitem",
        ),
        margin=dict(l=24, r=300, t=70, b=70),
        xaxis=dict(
            title="Tempo",
            rangeslider=dict(visible=True, thickness=0.08),
            rangeselector=dict(
                buttons=[
                    dict(count=6, label="6m", step="month", stepmode="backward"),
                    dict(count=1, label="1a", step="year", stepmode="backward"),
                    dict(count=3, label="3a", step="year", stepmode="backward"),
                    dict(step="all", label="Tudo"),
                ]
            ),
        ),
        yaxis=dict(
            title="Quantidade de atos",
            tickvals=tickvals,
            ticktext=[f"{abs(value):,}".replace(",", ".") for value in tickvals],
            zeroline=False,
        ),
    )
    fig.add_annotation(
        xref="paper",
        yref="paper",
        x=0,
        y=1.03,
        text="Nomeacoes",
        showarrow=False,
        font=dict(size=12, color="#333"),
    )
    fig.add_annotation(
        xref="paper",
        yref="paper",
        x=0,
        y=-0.08,
        text="Exoneracoes",
        showarrow=False,
        font=dict(size=12, color="#333"),
    )
    return fig


def nome_representante_governo(governo: str) -> str:
    governo = str(governo or "Nao identificado").strip()
    if " - " not in governo:
        return governo
    return governo.split(" - ", 1)[0].strip() or "Nao identificado"


def origem_representante_governo(governo: str) -> str:
    nome = nome_representante_governo(governo)
    origem_por_nome = {
        "Andre Ceciliano": "ALERJ",
        "Claudio Bomfim de Castro e Silva": "Executivo estadual",
        "Francisco Dornelles": "Vice-governadoria",
        "Luiz Fernando de Souza": "Executivo estadual",
        "Paulo Melo": "ALERJ",
        "Rodrigo Bacellar": "ALERJ",
        "Ricardo Couto de Castro": "TJ-RJ",
        "Sergio Cabral": "Executivo estadual",
        "Thiago Pampolha": "Vice-governadoria",
        "Wilson Jose Witzel": "Executivo estadual",
    }
    if nome in origem_por_nome:
        return origem_por_nome[nome]
    if "Governador em exerc" in str(governo or ""):
        return "Vice-governadoria"
    return "Executivo estadual"


def origem_representante_agregada(values) -> str:
    origens = []
    for value in values.dropna().astype(str):
        if value and value not in origens:
            origens.append(value)
    return " / ".join(origens) if origens else "Nao identificado"


def papeis_governo(values) -> str:
    papeis = []
    for value in values.dropna().astype(str):
        if " - " in value:
            papel = value.split(" - ", 1)[1].strip()
        else:
            papel = value.strip()
        if papel and papel not in papeis:
            papeis.append(papel)
    return " / ".join(papeis) if papeis else "Nao identificado"


def rotulo_representante_curto(governo: str) -> str:
    nome = nome_representante_governo(governo)
    partes = nome.split()
    if len(partes) >= 2:
        return f"{partes[0]} {partes[-1]}"
    return nome


def rotulo_governo_curto(governo: str) -> str:
    governo = str(governo or "Nao identificado").strip()
    if " - " not in governo:
        return governo
    nome, cargo = governo.split(" - ", 1)
    partes = nome.split()
    if len(partes) >= 2:
        nome = f"{partes[0]} {partes[-1]}"
    return f"{nome} - {cargo}"


def eixo_representante_label(dff_mov) -> str:
    if not dff_mov.empty and set(dff_mov["origem_representante"].dropna().astype(str).unique()) == {"Setor"}:
        return "Setor"
    return "Governo"


def fig_fluxo_por_governo(dff_mov):
    if dff_mov.empty:
        return go.Figure().update_layout(title="Sem dados para governos")

    eixo_label = eixo_representante_label(dff_mov)
    base = (
        dff_mov.groupby(["representante_origem", "tipo_ato"], observed=True)
        .size()
        .reset_index(name="quantidade")
    )
    base["fluxo"] = base.apply(
        lambda row: -row["quantidade"] if row["tipo_ato"] == "exoneracao" else row["quantidade"],
        axis=1,
    )
    base["rotulo"] = base["quantidade"].map(lambda value: f"{value:,}".replace(",", "."))
    ordem = (
        base.assign(abs_fluxo=base["fluxo"].abs())
        .groupby("representante_origem", observed=True)["abs_fluxo"]
        .sum()
        .sort_values()
        .index
        .tolist()
    )
    title_suffix = ""
    if eixo_label == "Setor":
        ordem = ordem[-10:]
        base = base[base["representante_origem"].isin(ordem)]
        title_suffix = " - Top 10"

    fig = px.bar(
        base,
        x="fluxo",
        y="representante_origem",
        color="tipo_ato",
        orientation="h",
        text="rotulo",
        category_orders={
            "tipo_ato": ["exoneracao", "nomeacao"],
            "representante_origem": ordem,
        },
        labels={
            "fluxo": "Saídas / Entradas",
            "representante_origem": eixo_label,
            "tipo_ato": "Movimentação",
        },
        title=f"Entradas e Saídas por {eixo_label}{title_suffix}",
    )
    fig.add_vline(x=0, line_width=1, line_color="#444")
    fig.update_layout(
        height=max(380, 32 * max(1, len(ordem)) + 130),
        bargap=0.36,
        bargroupgap=0.1,
        font=dict(size=10),
        title_font_size=18,
        xaxis_title="Exonerações à esquerda, nomeações à direita",
        yaxis_title="",
        legend_title_text="Movimentação",
        margin=dict(l=24, r=24, t=70, b=50),
    )
    return fig


def fig_saldo_por_governo(dff_mov):
    if dff_mov.empty:
        return go.Figure().update_layout(title="Sem dados para saldo")

    eixo_label = eixo_representante_label(dff_mov)
    base = (
        dff_mov.groupby(["representante_origem", "tipo_ato"], observed=True)
        .size()
        .unstack(fill_value=0)
        .reset_index()
    )
    for col in ["exoneracao", "nomeacao"]:
        if col not in base.columns:
            base[col] = 0
    base["saldo"] = base["nomeacao"] - base["exoneracao"]
    base = base.sort_values("saldo")
    base["cor"] = base["saldo"].apply(lambda value: "Mais entradas" if value >= 0 else "Mais saídas")
    title_suffix = ""
    if eixo_label == "Setor":
        base = base.assign(abs_saldo=base["saldo"].abs()).sort_values("abs_saldo").tail(10).drop(columns="abs_saldo")
        title_suffix = " - Top 10"

    fig = px.bar(
        base,
        x="saldo",
        y="representante_origem",
        color="cor",
        orientation="h",
        text=base["saldo"].map(lambda value: f"{value:,}".replace(",", ".")),
        labels={"saldo": "Nomeações menos exonerações", "representante_origem": eixo_label, "cor": ""},
        title=f"Saldo Líquido por {eixo_label}{title_suffix}",
        color_discrete_map={"Mais entradas": "#287c5a", "Mais saídas": "#b4423c"},
    )
    fig.add_vline(x=0, line_width=1, line_color="#444")
    fig.update_layout(
        height=max(360, 30 * max(1, len(base)) + 120),
        bargap=0.4,
        font=dict(size=10),
        title_font_size=18,
        yaxis_title="",
        showlegend=True,
        margin=dict(l=24, r=24, t=70, b=50),
    )
    return fig


def fig_timeline_governo(dff_mov):
    if dff_mov.empty:
        return go.Figure().update_layout(title="Sem dados para timeline")

    base = dff_mov.dropna(subset=["data_movimentacao"]).copy()
    if base.empty:
        return go.Figure().update_layout(title="Sem datas válidas para timeline")

    selected_governments = base["representante_origem"].nunique()
    if selected_governments <= 3:
        month_period = base["data_movimentacao"].dt.to_period("M")
        base["periodo"] = month_period.dt.to_timestamp(how="end").dt.normalize()
        latest_date_by_month = base.groupby(month_period)["data_movimentacao"].transform("max")
        current_month = month_period == base["data_movimentacao"].max().to_period("M")
        base.loc[current_month, "periodo"] = latest_date_by_month[current_month] + pd.Timedelta(days=1)
        x_label = "Mês"
    else:
        base["periodo"] = base["data_movimentacao"].dt.year.astype(int)
        x_label = "Ano"

    timeline = (
        base.groupby(["periodo", "representante_origem", "tipo_ato"], observed=True)
        .size()
        .reset_index(name="quantidade")
        .sort_values("periodo")
    )

    eixo_label = eixo_representante_label(dff_mov)
    fig = px.bar(
        timeline,
        x="periodo",
        y="quantidade",
        color="tipo_ato",
        facet_row="representante_origem" if selected_governments <= 3 else None,
        barmode="group",
        labels={
            "periodo": x_label,
            "quantidade": "Quantidade",
            "tipo_ato": "Movimentação",
            "representante_origem": eixo_label,
        },
        title=f"Timeline de Movimentações por {eixo_label}",
        category_orders={"tipo_ato": ["exoneracao", "nomeacao"]},
    )
    fig.update_layout(
        height=520 if selected_governments > 3 else max(420, selected_governments * 280),
        bargap=0.3,
        bargroupgap=0.1,
        font=dict(size=10),
        title_font_size=18,
        legend_title_text="Movimentação",
        margin=dict(l=24, r=24, t=70, b=50),
    )
    fig.for_each_annotation(lambda annotation: annotation.update(text=annotation.text.split("=")[-1]))
    return fig


def fig_orgaos_por_governo(dff_mov, periodo=None):
    if dff_mov.empty:
        return go.Figure().update_layout(title="Sem dados para órgãos")

    periodo = periodo or periodo_movimentacoes(dff_mov)
    base = adicionar_orgao_grafico(dff_mov)
    if base.empty:
        return go.Figure().update_layout(title="Sem órgãos identificados para os filtros selecionados")

    ranking = (
        base.groupby("orgao_chave", observed=True)
        .size()
        .sort_values(ascending=False)
        .head(TOP_N_ORGAOS)
        .index
    )
    base = base[base["orgao_chave"].isin(ranking)]
    barras = base.groupby(["orgao_chave", "orgao_grafico", "tipo_ato"], observed=True).size().reset_index(name="quantidade")
    barras["fluxo"] = barras.apply(
        lambda row: -row["quantidade"] if row["tipo_ato"] == "exoneracao" else row["quantidade"],
        axis=1,
    )
    ordem = (
        barras.assign(abs_fluxo=barras["fluxo"].abs())
        .groupby("orgao_grafico", observed=True)["abs_fluxo"]
        .sum()
        .sort_values()
        .index
        .tolist()
    )

    fig = px.bar(
        barras,
        x="fluxo",
        y="orgao_grafico",
        color="tipo_ato",
        orientation="h",
        category_orders={"tipo_ato": ["exoneracao", "nomeacao"], "orgao_grafico": ordem},
        labels={"fluxo": "Saídas / Entradas", "orgao_grafico": "Órgão", "tipo_ato": "Movimentação"},
        title=f"Órgãos Mais Movimentados - Top {TOP_N_ORGAOS} ({periodo})",
    )
    fig.add_vline(x=0, line_width=1, line_color="#444")
    fig.update_layout(
        height=560,
        bargap=0.36,
        bargroupgap=0.1,
        font=dict(size=10),
        title_font_size=18,
        xaxis_title="Exonerações à esquerda, nomeações à direita",
        yaxis_title="",
        legend_title_text="Movimentação",
        margin=dict(l=24, r=24, t=70, b=50),
    )
    return fig


def tabela_resumo_governos(dff_mov):
    if dff_mov.empty:
        return html.Div("Sem dados para os filtros selecionados.")

    base = (
        dff_mov.groupby(["representante_origem", "tipo_ato"], observed=True)
        .size()
        .unstack(fill_value=0)
        .reset_index()
    )
    for col in ["exoneracao", "nomeacao"]:
        if col not in base.columns:
            base[col] = 0
    base["saldo"] = base["nomeacao"] - base["exoneracao"]
    base["atos"] = base["nomeacao"] + base["exoneracao"]
    base = base.sort_values("atos", ascending=False)

    eixo_label = eixo_representante_label(dff_mov)
    header = html.Tr([
        html.Th(eixo_label),
        html.Th("Exonerações"),
        html.Th("Nomeações"),
        html.Th("Saldo"),
        html.Th("Atos"),
    ])
    rows = [
        html.Tr([
            html.Td(row["representante_origem"]),
            html.Td(f"{int(row['exoneracao']):,}".replace(",", ".")),
            html.Td(f"{int(row['nomeacao']):,}".replace(",", ".")),
            html.Td(f"{int(row['saldo']):,}".replace(",", ".")),
            html.Td(f"{int(row['atos']):,}".replace(",", ".")),
        ])
        for _, row in base.iterrows()
    ]
    return html.Table(
        [html.Thead(header), html.Tbody(rows)],
        style={
            "width": "100%",
            "borderCollapse": "collapse",
            "backgroundColor": "white",
        },
    )


def fig_timeline_mobilidade(dff):
    if dff.empty:
        return go.Figure().update_layout(title="Sem dados para mobilidade")

    base = (
        dff.groupby("ano")
        .agg(
            total=("pessoa", "count"),
            mudou_cargo=("mudou_cargo", "sum"),
            mudou_orgao=("mudou_orgao", "sum")
        )
        .reset_index()
    )

    base["tx_mudou_cargo"] = base["mudou_cargo"] / base["total"]
    base["tx_mudou_orgao"] = base["mudou_orgao"] / base["total"]

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=base["ano"],
        y=base["tx_mudou_cargo"],
        mode="lines+markers",
        name="Taxa mudança de cargo"
    ))

    fig.add_trace(go.Scatter(
        x=base["ano"],
        y=base["tx_mudou_orgao"],
        mode="lines+markers",
        name="Taxa mudança de órgão"
    ))

    fig.update_layout(
        title="Timeline de Mobilidade",
        yaxis_tickformat=".0%",
        height=420
    )

    return fig


def fig_heatmap(mat_prob):
    if mat_prob.empty:
        return go.Figure().update_layout(title="Sem dados para matriz")

    fig = px.imshow(
        mat_prob,
        text_auto=".2f",
        aspect="auto",
        title="Matriz de Transição"
    )

    fig.update_layout(height=520)

    return fig


def fig_network_3d(trans):
    if trans.empty:
        return go.Figure().update_layout(title="Sem dados para rede 3D")

    trans = trans.sort_values("count", ascending=False).head(TOP_N_TRANSICOES)

    G = nx.DiGraph()

    for _, row in trans.iterrows():
        G.add_edge(row["estado"], row["prox_estado"], weight=row["count"])

    pos = nx.spring_layout(G, dim=3, k=0.75, seed=42)

    edge_x, edge_y, edge_z = [], [], []

    for u, v in G.edges():
        x0, y0, z0 = pos[u]
        x1, y1, z1 = pos[v]

        edge_x += [x0, x1, None]
        edge_y += [y0, y1, None]
        edge_z += [z0, z1, None]

    edge_trace = go.Scatter3d(
        x=edge_x,
        y=edge_y,
        z=edge_z,
        mode="lines",
        line=dict(width=2),
        hoverinfo="none"
    )

    node_x, node_y, node_z, node_text, node_size = [], [], [], [], []

    for node in G.nodes():
        x, y, z = pos[node]
        grau = G.degree(node)

        node_x.append(x)
        node_y.append(y)
        node_z.append(z)
        node_text.append(f"{node}<br>Grau: {grau}")
        node_size.append(8 + grau * 4)

    node_trace = go.Scatter3d(
        x=node_x,
        y=node_y,
        z=node_z,
        mode="markers+text",
        text=[n.split("<br>")[0] for n in node_text],
        hovertext=node_text,
        hoverinfo="text",
        textposition="top center",
        marker=dict(
            size=node_size,
            opacity=0.85,
            color=node_size,
            colorscale="Viridis"
        )
    )

    fig = go.Figure(data=[edge_trace, node_trace])

    fig.update_layout(
        title="Rede de Transições 3D",
        height=620,
        showlegend=False,
        margin=dict(l=0, r=0, b=0, t=40),
        scene=dict(
            xaxis=dict(showbackground=False, showticklabels=False, title=""),
            yaxis=dict(showbackground=False, showticklabels=False, title=""),
            zaxis=dict(showbackground=False, showticklabels=False, title="")
        )
    )

    return fig


def gerar_resumo(dff, trans, mat_prob):
    if dff.empty:
        return "Sem dados para os filtros selecionados."

    total = len(dff)
    pessoas = dff["pessoa"].nunique()
    media_dias = dff["dias_desde_exoneracao"].mean()
    mediana_dias = dff["dias_desde_exoneracao"].median()
    tx_cargo = dff["mudou_cargo"].mean()
    tx_orgao = dff["mudou_orgao"].mean()

    steady = estado_estacionario(mat_prob)

    linhas = [
        "RESUMO ANALÍTICO",
        "",
        f"Registros filtrados: {total:,}".replace(",", "."),
        f"Pessoas únicas: {pessoas:,}".replace(",", "."),
        f"Tempo médio de retorno: {media_dias:.2f} dias",
        f"Mediana do retorno: {mediana_dias:.2f} dias",
        f"Taxa de mudança de cargo: {tx_cargo:.2%}",
        f"Taxa de mudança de órgão: {tx_orgao:.2%}",
        "",
        "Top transições:"
    ]

    top = trans.sort_values("count", ascending=False).head(10)

    for _, row in top.iterrows():
        linhas.append(f"{row['estado']} → {row['prox_estado']}: {row['count']}")

    linhas.append("")
    linhas.append("Estado estacionário:")

    if steady:
        for k, v in sorted(steady.items(), key=lambda x: x[1], reverse=True):
            linhas.append(f"{k}: {v:.4f}")
    else:
        linhas.append("Não calculável para o filtro atual.")

    return "\n".join(linhas)


# =====================================================
# ROTATIVIDADE POR ORGAO
# =====================================================
def fig_rotatividade_orgaos(dff_mov, top_n=20):
    if dff_mov.empty:
        return go.Figure().update_layout(title="Sem dados")

    base = dff_mov.dropna(subset=["orgao"]).copy()
    base["orgao"] = base["orgao"].astype(str).str.strip()
    base = base[base["orgao"] != ""]

    agrupado = base.groupby(["orgao", "tipo_ato"], observed=True).size().reset_index(name="quantidade")
    total_por_orgao = agrupado.groupby("orgao", observed=True)["quantidade"].sum().sort_values(ascending=False)

    top_orgaos = total_por_orgao.head(top_n).index
    agrupado = agrupado[agrupado["orgao"].isin(top_orgaos)]

    fig = px.bar(
        agrupado,
        x="orgao",
        y="quantidade",
        color="tipo_ato",
        barmode="group",
        category_orders={"tipo_ato": ["exoneracao", "nomeacao"]},
        labels={"orgao": "Órgão", "quantidade": "Atos", "tipo_ato": "Tipo"},
        title=f"Rotatividade por Órgão - Top {top_n}",
    )
    fig.update_layout(
        height=600, xaxis_tickangle=-45, bargap=0.3, bargroupgap=0.08,
        font=dict(size=10), title_font_size=18,
    )
    fig.update_traces(texttemplate="%{y:,}", textposition="outside", textfont_size=9)
    return fig


# =====================================================
# SAZONALIDADE
# =====================================================
def fig_sazonalidade_mensal(dff_mov):
    if dff_mov.empty:
        return go.Figure().update_layout(title="Sem dados")

    base = dff_mov.dropna(subset=["data_movimentacao", "tipo_ato"]).copy()
    base["mes"] = base["data_movimentacao"].dt.month
    base["ano"] = base["data_movimentacao"].dt.year

    agrupado = base.groupby(["ano", "mes", "tipo_ato"], observed=True).size().reset_index(name="quantidade")
    media_mensal = agrupado.groupby(["mes", "tipo_ato"], observed=True)["quantidade"].mean().reset_index()

    fig = px.bar(
        media_mensal,
        x="mes",
        y="quantidade",
        color="tipo_ato",
        barmode="group",
        category_orders={"tipo_ato": ["exoneracao", "nomeacao"]},
        labels={"mes": "Mês", "quantidade": "Média de atos", "tipo_ato": "Tipo"},
        title="Sazonalidade Mensal - Média Histórica por Mês",
    )
    fig.update_layout(
        height=450, bargap=0.25, bargroupgap=0.08,
        font=dict(size=10), title_font_size=18,
        xaxis=dict(tickmode="array", tickvals=list(range(1, 13)), ticktext=[
            "Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"
        ]),
    )
    fig.update_traces(texttemplate="%{y:,.0f}", textposition="outside", textfont_size=9)
    return fig


def fig_sazonalidade_heatmap(dff_mov):
    if dff_mov.empty:
        return go.Figure().update_layout(title="Sem dados")

    base = dff_mov.dropna(subset=["data_movimentacao"]).copy()
    base["ano"] = base["data_movimentacao"].dt.year.astype(int)
    base["mes"] = base["data_movimentacao"].dt.month

    agrupado = base.groupby(["ano", "mes"]).size().reset_index(name="quantidade")
    pivot = agrupado.pivot(index="ano", columns="mes", values="quantidade").fillna(0)

    fig = px.imshow(
        pivot,
        labels=dict(x="Mês", y="Ano", color="Atos"),
        title="Intensidade Mensal de Movimentações",
        aspect="auto",
        color_continuous_scale="Viridis",
    )
    fig.update_layout(height=500, title_font_size=18)
    fig.update_xaxes(tickmode="array", tickvals=list(range(12)), ticktext=[
        "Jan","Fev","Mar","Abr","Mai","Jun","Jul","Ago","Set","Out","Nov","Dez"
    ])
    return fig


# =====================================================
# CICLO POLITICO
# =====================================================
def fig_ciclo_politico(dff_mov):
    if dff_mov.empty:
        return go.Figure().update_layout(title="Sem dados")

    base = dff_mov.dropna(subset=["ano", "representante_governo"]).copy()
    base["ano"] = base["ano"].astype(int)

    serie = base.groupby(["ano", "representante_governo", "tipo_ato"], observed=True).size().reset_index(name="quantidade")
    serie["ano"] = serie["ano"].astype(int)

    fig = px.bar(
        serie,
        x="ano",
        y="quantidade",
        color="representante_governo",
        pattern_shape="tipo_ato",
        barmode="stack",
        labels={
            "ano": "Ano", "quantidade": "Atos",
            "representante_governo": "Governo", "tipo_ato": "Tipo",
        },
        title="Ciclo Político - Volume de Atos por Governo",
    )
    fig.update_layout(
        height=500, title_font_size=18, bargap=0.12,
        hovermode="x unified",
        legend=dict(orientation="h", y=-0.3, font=dict(size=10)),
    )
    fig.update_xaxes(dtick=1)
    fig.update_traces(texttemplate="%{y:,}", textposition="inside", textfont_size=9)
    return fig


def fig_transicoes_governo(dff_mov):
    if dff_mov.empty:
        return go.Figure().update_layout(title="Sem dados")

    base = dff_mov.dropna(subset=["ano", "representante_governo"]).copy()
    base["ano"] = base["ano"].astype(int)

    comparacao = base.groupby(["ano", "representante_governo", "tipo_ato"], observed=True).size().reset_index(name="quantidade")
    governos_por_ano = base.groupby("ano")["representante_governo"].unique()

    linhas = []
    for ano in sorted(governos_por_ano.index):
        govs = governos_por_ano[ano]
        for gov in govs:
            dados_gov = comparacao[(comparacao["ano"] == ano) & (comparacao["representante_governo"] == gov)]
            total = dados_gov["quantidade"].sum()
            eh_transicao = len(govs) > 1
            linhas.append({"ano": ano, "governo": gov, "total_atos": total, "transicao": eh_transicao})

    df_trans = pd.DataFrame(linhas)

    fig = px.bar(
        df_trans,
        x="ano",
        y="total_atos",
        color="governo",
        barmode="stack",
        labels={"ano": "Ano", "total_atos": "Atos", "governo": "Governo"},
        title="Atos por Governo e Ano",
    )

    # Add triangle markers for transition years
    for _, row in df_trans.drop_duplicates("ano").iterrows():
        if row["transicao"]:
            fig.add_annotation(
                x=row["ano"], y=1,
                text="▲", showarrow=False,
                yref="paper", yanchor="bottom",
                font=dict(size=14, color="#eab308"),
            )

    fig.update_layout(
        height=450, title_font_size=18, bargap=0.12,
        hovermode="x unified",
        legend=dict(orientation="h", y=-0.3, font=dict(size=10)),
    )
    fig.update_xaxes(dtick=1)
    return fig


# =====================================================
# TEMPO DE PREENCHIMENTO
# =====================================================
def fig_tempo_preenchimento(df, dff_mov):
    if df.empty or dff_mov.empty:
        return go.Figure().update_layout(title="Sem dados")

    base = df.dropna(subset=["dias_desde_exoneracao"]).copy()
    base = base[base["dias_desde_exoneracao"] >= 0]

    fig = go.Figure()
    fig.add_trace(go.Histogram(
        x=base["dias_desde_exoneracao"],
        nbinsx=50,
        marker_color="#1f5eff",
        name="Distribuição",
    ))
    media = base["dias_desde_exoneracao"].mean()
    mediana = base["dias_desde_exoneracao"].median()
    fig.add_vline(x=media, line_dash="dash", line_color="red",
                  annotation_text=f"Média: {media:.0f}d", annotation_position="top right")
    fig.add_vline(x=mediana, line_dash="dot", line_color="green",
                  annotation_text=f"Mediana: {mediana:.0f}d", annotation_position="top left")

    fig.update_layout(
        title="Distribuição do Tempo entre Exoneração e Nova Nomeação",
        xaxis_title="Dias", yaxis_title="Pessoas",
        height=450, title_font_size=18, bargap=0.08,
    )
    return fig

def fig_preenchimento_por_tempo(df):
    if df.empty:
        return go.Figure().update_layout(title="Sem dados", height=300)

    base = df["tempo_cluster"].value_counts().reset_index()
    base.columns = ["tempo_cluster", "pessoas"]

    fig = px.bar(
        base,
        x="tempo_cluster",
        y="pessoas",
        color="tempo_cluster",
        category_orders={
            "tempo_cluster": ["imediato", "curto", "medio", "longo", "desconhecido"],
        },
        labels={"tempo_cluster": "Tempo de Retorno", "pessoas": "Pessoas"},
        title="Retornos por Categoria de Tempo",
        color_discrete_sequence=["#1f5eff", "#3b82f6", "#60a5fa", "#93c5fd", "#d1d5db"],
    )
    fig.update_layout(height=400, title_font_size=18, showlegend=False)
    fig.update_traces(texttemplate="%{y:,}", textposition="outside")
    return fig


# =====================================================
# CARREIRAS INDIVIDUAIS - Top pessoas
# =====================================================
def fig_top_pessoas(dff_mov, top_n=20):
    if dff_mov.empty:
        return go.Figure().update_layout(title="Sem dados")

    top = dff_mov["pessoa"].value_counts().head(top_n).reset_index()
    top.columns = ["pessoa", "quantidade"]

    fig = px.bar(
        top,
        x="quantidade",
        y="pessoa",
        orientation="h",
        labels={"quantidade": "Atos", "pessoa": "Pessoa"},
        title=f"Top {top_n} Pessoas com Mais Movimentações",
        color="quantidade",
        color_continuous_scale="Blues",
    )
    fig.update_layout(height=max(400, top_n * 22), title_font_size=18, yaxis=dict(autorange="reversed"))
    fig.update_traces(texttemplate="%{x:,}", textposition="outside")
    return fig


def fig_trajetoria_pessoa(dff_mov, pessoa_nome):
    if dff_mov.empty or not pessoa_nome:
        return go.Figure().update_layout(title="Selecione uma pessoa")

    traj = dff_mov[dff_mov["pessoa"] == pessoa_nome].copy()
    if traj.empty:
        return go.Figure().update_layout(title=f"Sem dados para {pessoa_nome}")

    traj = traj.dropna(subset=["data_movimentacao"]).sort_values("data_movimentacao")
    traj["sequencia"] = range(1, len(traj) + 1)
    traj["cor"] = traj["tipo_ato"].map({"nomeacao": "#287c5a", "exoneracao": "#b4423c"})

    fig = go.Figure()
    for _, row in traj.iterrows():
        cor = row.get("cor", "#888")
        fig.add_trace(go.Scatter(
            x=[row["data_movimentacao"]],
            y=[row["sequencia"]],
            mode="markers+text",
            marker=dict(size=12, color=cor, line=dict(color="black", width=1)),
            text=row["tipo_ato"][:4],
            textposition="middle right",
            textfont=dict(size=9, color=cor),
            showlegend=False,
            hovertemplate=(
                f"Data: %{{x|%d/%m/%Y}}<br>"
                f"Tipo: {row['tipo_ato']}<br>"
                f"Órgão: {row.get('orgao', 'N/I')}<br>"
                f"<extra></extra>"
            ),
        ))

    fig.update_layout(
        title=f"Trajetória de {pessoa_nome} ({len(traj)} atos)",
        xaxis_title="Data", yaxis_title="Sequência de atos",
        height=400, title_font_size=16,
        yaxis=dict(dtick=1),
    )
    return fig


# =====================================================
# INDICACAO VS CARREIRA
# =====================================================
def fig_indicacao_vs_carreira(dff_mov):
    if dff_mov.empty:
        return go.Figure().update_layout(title="Sem dados")

    base = dff_mov.dropna(subset=["autoria_ato", "ano"]).copy()
    base["ano"] = base["ano"].astype(int)

    serie = base.groupby(["ano", "autoria_ato"], observed=True).size().reset_index(name="quantidade")

    fig = px.area(
        serie,
        x="ano",
        y="quantidade",
        color="autoria_ato",
        labels={"ano": "Ano", "quantidade": "Atos", "autoria_ato": "Autoria"},
        title="Evolução: Indicação Política vs Carreira por Ano",
        category_orders={"autoria_ato": ["Governador", "Secretaria/Subsecretaria", "Outro/Nao identificado"]},
    )
    fig.update_layout(height=450, title_font_size=18, hovermode="x unified")
    return fig


def fig_indicacao_por_governo(dff_mov):
    if dff_mov.empty:
        return go.Figure().update_layout(title="Sem dados")

    base = dff_mov.dropna(subset=["autoria_ato", "representante_governo"]).copy()

    agrupado = base.groupby(["representante_governo", "autoria_ato"], observed=True).size().reset_index(name="quantidade")
    total_por_governo = agrupado.groupby("representante_governo", observed=True)["quantidade"].sum()
    agrupado["pct"] = agrupado.apply(
        lambda r: r["quantidade"] / total_por_governo[r["representante_governo"]] * 100, axis=1
    )

    fig = px.bar(
        agrupado,
        x="representante_governo",
        y="pct",
        color="autoria_ato",
        barmode="stack",
        category_orders={"autoria_ato": ["Governador", "Secretaria/Subsecretaria", "Outro/Nao identificado"]},
        labels={"representante_governo": "Governo", "pct": "Percentual", "autoria_ato": "Autoria"},
        title="Composição de Autoria por Governo",
    )
    fig.update_layout(height=450, title_font_size=18)
    fig.update_traces(texttemplate="%{y:.1f}%", textposition="inside", textfont_size=10)
    return fig


# =====================================================
# ANOMALIAS
# =====================================================
def fig_anomalias_por_ano(dff_mov):
    if dff_mov.empty:
        return go.Figure().update_layout(title="Sem dados")

    base = dff_mov.dropna(subset=["ano"]).copy()
    base["ano"] = base["ano"].astype(int)

    serie = base.groupby("ano").size().reset_index(name="quantidade")
    media = serie["quantidade"].mean()
    desvio = serie["quantidade"].std()

    serie["anomalia"] = serie["quantidade"].apply(
        lambda x: "Acima" if x > media + 2 * desvio else ("Abaixo" if x < media - 2 * desvio else "Normal")
    )

    fig = px.bar(
        serie,
        x="ano",
        y="quantidade",
        color="anomalia",
        color_discrete_map={"Normal": "#94a3b8", "Acima": "#ef4444", "Abaixo": "#3b82f6"},
        labels={"ano": "Ano", "quantidade": "Atos", "anomalia": "Classificação"},
        title=f"Anomalias por Ano (média={media:.0f}, desvio={desvio:.0f}, limites=±2σ)",
    )
    fig.add_hline(y=media, line_dash="dash", line_color="#64748b",
                  annotation_text=f"Média {media:.0f}", annotation_position="bottom right")
    fig.add_hrect(y0=media - 2 * desvio, y1=media + 2 * desvio,
                  fillcolor="green", opacity=0.05, line_width=0)
    fig.update_layout(height=450, title_font_size=18, bargap=0.15)
    fig.update_traces(texttemplate="%{y:,}", textposition="outside", textfont_size=9)
    return fig


def fig_anomalias_orgaos(dff_mov, top_n=15):
    if dff_mov.empty:
        return go.Figure().update_layout(title="Sem dados")

    base = dff_mov.dropna(subset=["orgao"]).copy()
    base["orgao"] = base["orgao"].astype(str).str.strip()
    base = base[base["orgao"] != ""]

    total = base.groupby("orgao", observed=True).size()
    media_t = total.mean()
    desvio_t = total.std()

    anomalos = total[(total > media_t + 3 * desvio_t) | (total < media_t - 3 * desvio_t)].head(top_n)
    if anomalos.empty:
        anomalos = total.sort_values(ascending=False).head(top_n)

    df_plot = anomalos.reset_index()
    df_plot.columns = ["orgao", "quantidade"]
    df_plot["cor"] = df_plot["quantidade"].apply(
        lambda x: "Acima do esperado" if x > media_t + 3 * desvio_t else "Normal"
    )

    fig = px.bar(
        df_plot,
        x="quantidade",
        y="orgao",
        color="cor",
        orientation="h",
        color_discrete_map={"Acima do esperado": "#ef4444", "Normal": "#94a3b8"},
        labels={"quantidade": "Atos", "orgao": "Órgão", "cor": ""},
        title=f"Órgãos com Volume Atípico (Top {top_n})",
    )
    fig.update_layout(height=max(400, top_n * 24), title_font_size=18)
    fig.update_traces(texttemplate="%{x:,}", textposition="outside")
    return fig


# =====================================================
# CO-OCORRENCIA
# =====================================================
def fig_coccurrencias(dff_mov, top_n=20):
    if dff_mov.empty:
        return go.Figure().update_layout(title="Sem dados")

    base = dff_mov.dropna(subset=["data_movimentacao"]).copy()
    base["data"] = base["data_movimentacao"].dt.strftime("%Y-%m-%d")

    atos_por_data = base.groupby("data").agg(
        pessoas=("pessoa", "nunique"),
        total=("pessoa", "count"),
        orgaos=("orgao", "nunique"),
    ).reset_index().sort_values("total", ascending=False)

    top = atos_por_data.head(top_n)

    fig = px.scatter(
        top,
        x="pessoas",
        y="total",
        size="orgaos",
        hover_name="data",
        labels={"pessoas": "Pessoas únicas", "total": "Total de atos", "orgaos": "Órgãos envolvidos"},
        title=f"Top {top_n} Edições com Maior Concentração de Atos",
        color="orgaos",
        color_continuous_scale="Viridis",
    )
    fig.update_layout(height=500, title_font_size=18)
    return fig


def fig_distribuicao_por_edicao(dff_mov):
    if dff_mov.empty:
        return go.Figure().update_layout(title="Sem dados")

    base = dff_mov.dropna(subset=["data_movimentacao"]).copy()
    base["data"] = base["data_movimentacao"].dt.strftime("%Y-%m-%d")

    atos_por_data = base.groupby("data")["pessoa"].nunique().reset_index()
    atos_por_data.columns = ["data", "pessoas"]

    fig = px.histogram(
        atos_por_data,
        x="pessoas",
        nbins=40,
        labels={"pessoas": "Pessoas por edição", "count": "Frequência"},
        title="Distribuição de Pessoas por Edição do Diário Oficial",
        color_discrete_sequence=["#1f5eff"],
    )
    fig.update_layout(height=400, title_font_size=18, bargap=0.05)
    fig.update_traces(texttemplate="%{y:,}", textposition="outside", textfont_size=9)

    media = atos_por_data["pessoas"].mean()
    mediana = atos_por_data["pessoas"].median()
    fig.add_vline(x=media, line_dash="dash", line_color="red",
                  annotation_text=f"Média {media:.0f}", annotation_position="top right")
    fig.add_vline(x=mediana, line_dash="dot", line_color="green",
                  annotation_text=f"Mediana {mediana:.0f}", annotation_position="top left")
    return fig

