from __future__ import annotations

import os
import re
import unicodedata
from collections.abc import Callable
from dataclasses import dataclass

import pandas as pd
from flask import Flask, abort, jsonify, redirect, render_template, request, send_file, url_for
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from analise_temporal.services import dados


app = Flask(__name__)
server = app

NAV_ITEMS = [
    {"endpoint": "index", "label": "Visao Geral", "icon": "home"},
    {"endpoint": "nomeacoes_page", "label": "Nomeacoes", "icon": "users-plus"},
    {"endpoint": "exoneracoes_page", "label": "Exoneracoes", "icon": "user-minus"},
    {"endpoint": "orgaos_page", "label": "Orgaos & Secretarias", "icon": "building"},
    {"endpoint": "servidores_page", "label": "Servidores", "icon": "users"},
    {"endpoint": "publicacoes_page", "label": "Publicacoes", "icon": "file"},
    {"endpoint": "downloads_page", "label": "Downloads", "icon": "download"},
    {"endpoint": "alertas_page", "label": "Alertas", "icon": "bell"},
]

PAGE_SHELL = {
    "nomeacoes": {
        "template": "nomeacoes.html",
        "title": "Nomeacoes",
        "heading": "Nomeacoes mais recentes",
        "description": "Leitura direta das entradas publicadas no consolidado enviado pelo projeto fonte.",
        "active_endpoint": "nomeacoes_page",
    },
    "exoneracoes": {
        "template": "exoneracoes.html",
        "title": "Exoneracoes",
        "heading": "Exoneracoes mais recentes",
        "description": "Painel de saidas com foco em volume, destino institucional e recorrencia recente.",
        "active_endpoint": "exoneracoes_page",
    },
    "orgaos": {
        "template": "orgaos.html",
        "title": "Orgaos & Secretarias",
        "heading": "Orgaos com maior movimentacao",
        "description": "Comparativo entre entradas e saidas por orgao para localizar concentracao administrativa.",
        "active_endpoint": "orgaos_page",
    },
    "servidores": {
        "template": "servidores.html",
        "title": "Servidores",
        "heading": "Busca de servidores e trajetorias",
        "description": "Pesquise pelo nome para acompanhar a trajetoria completa da pessoa e veja quais servidores aparecem com mais recorrencia no consolidado.",
        "active_endpoint": "servidores_page",
    },
    "publicacoes": {
        "template": "publicacoes.html",
        "title": "Publicacoes",
        "heading": "Cadencia de publicacoes",
        "description": "Visao por mes e por dia para acompanhar ritmo de publicacao no Diario Oficial.",
        "active_endpoint": "publicacoes_page",
    },
    "downloads": {
        "template": "downloads.html",
        "title": "Downloads",
        "heading": "Arquivos entregues ao dash_temporal",
        "description": "Esta camada nao processa dados brutos; apenas disponibiliza o consolidado que chega do projeto principal.",
        "active_endpoint": "downloads_page",
    },
    "alertas": {
        "template": "alertas.html",
        "title": "Alertas",
        "heading": "Sinais de variacao recente",
        "description": "Comparacao simples entre os ultimos 30 dias e a janela imediatamente anterior para orientar acompanhamento.",
        "active_endpoint": "alertas_page",
    },
}


@dataclass(frozen=True)
class DashboardBounds:
    min_date: str
    max_date: str


def _prepare_dataframe() -> pd.DataFrame:
    frame = dados.df_mov.copy()
    frame["data_movimentacao"] = pd.to_datetime(frame["data_movimentacao"], errors="coerce")
    frame["orgao"] = frame["orgao"].astype("string").fillna("").str.strip()
    frame["cargo"] = frame["cargo"].astype("string").fillna("").str.strip()
    frame["pessoa"] = frame["pessoa"].astype("string").fillna("").str.strip()
    frame["representante_origem"] = frame["representante_origem"].astype("string").fillna("").str.strip()
    frame["tipo_ato"] = frame["tipo_ato"].astype("string").fillna("").str.strip().str.lower()
    frame = frame.dropna(subset=["data_movimentacao"]).copy()
    frame["ano_mes"] = frame["data_movimentacao"].dt.to_period("M").astype(str)
    return frame


def _load_dashboard_data() -> tuple[pd.DataFrame, DashboardBounds]:
    frame = _prepare_dataframe()
    bounds = DashboardBounds(
        min_date=frame["data_movimentacao"].min().date().isoformat(),
        max_date=frame["data_movimentacao"].max().date().isoformat(),
    )
    return frame, bounds


df_dashboard, dashboard_bounds = _load_dashboard_data()
_NOISE_PAT = re.compile(
    r"^(?:"
    r"CORONEL|MAJOR\b|MAJ\b|CAPIT[AÃ]O|TENENTECORONEL|TENENTE\b|TEN\s+CEL\b|SUBTENENTE|SARGENTO|CABO|SOLDADO|ALMIRANTE|GENERAL|"
    r"DELEGADO|DEFENSOR|PROCURADOR|PERITO|INSPETOR\w*|FISCAL|AGENTE|ANALISTA|T[EÉ]CNICO|AUXILIAR|"
    r"SECRET[AÁ]RIO|SUBSECRET[AÁ]RIO|DIRETOR|PRESIDENTE|COORDENADOR|GERENTE|CHEFE|ASSESSOR|"
    r"AUDITOR|CONTADOR|ADVOGADO|MEDICO|M[EÉ]DICO|ENFERMEIRO|DENTISTA|FARMACEUTICO|FARMAC[EÊ]UTICO|TECNICO|"
    r"POLICIAL|ESPECIALISTA|"
    r"ANTERIORMENTE|NOS\s+TERMOS|E\s+NOS\s+TERMOS|ID\.?\s*FUNCIONAL|REGULAMENTADA|CLASSE\s+INICIAL|"
    r"INSCRITO\s+NO|MATR[IÍ]CULA|IDENTIDADE"
    r")\b",
    re.IGNORECASE,
)
_people_index: list[str] = []
_people_vectorizer: TfidfVectorizer | None = None
_people_matrix = None


def _fold(value: str) -> str:
    return unicodedata.normalize("NFKD", value).encode("ascii", errors="ignore").decode("ascii")


def _norm_text(value: object) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    if text.lower() == "nan":
        return ""
    return _fold(text).lower()


def _is_noise(name: str) -> bool:
    cleaned = str(name or "").strip()
    if len(cleaned) < 8:
        return True
    return bool(_NOISE_PAT.match(cleaned))


def _covers_text(candidate: str, reference: str) -> bool:
    if candidate == reference:
        return True
    if not reference:
        return bool(candidate)
    return bool(candidate) and reference in candidate


def _is_more_complete(candidate: dict[str, object], reference: dict[str, object]) -> bool:
    orgao_candidate = _norm_text(candidate.get("orgao"))
    orgao_reference = _norm_text(reference.get("orgao"))
    cargo_candidate = _norm_text(candidate.get("cargo"))
    cargo_reference = _norm_text(reference.get("cargo"))

    same_or_better_orgao = _covers_text(orgao_candidate, orgao_reference)
    same_or_better_cargo = _covers_text(cargo_candidate, cargo_reference)
    strictly_better_orgao = len(orgao_candidate) > len(orgao_reference)
    strictly_better_cargo = len(cargo_candidate) > len(cargo_reference)

    return same_or_better_orgao and same_or_better_cargo and (strictly_better_orgao or strictly_better_cargo)


def _deduplicate_person_rows(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty:
        return frame

    group_cols = ["pessoa", "data_movimentacao", "tipo_ato"]
    if "representante_origem" in frame.columns:
        group_cols.append("representante_origem")

    deduped_groups: list[list[dict[str, object]]] = []
    for _, group in frame.groupby(group_cols, dropna=False, sort=False, observed=False):
        records = group.to_dict("records")
        kept: list[dict[str, object]] = []
        for record in records:
            if any(_is_more_complete(other, record) for other in records if other is not record):
                continue
            kept.append(record)
        deduped_groups.append(kept or records)

    deduped = [record for group in deduped_groups for record in group]
    return pd.DataFrame(deduped).reindex(columns=frame.columns)


def _valid_people(frame: pd.DataFrame) -> pd.DataFrame:
    return frame[(frame["pessoa"] != "") & (~frame["pessoa"].apply(_is_noise))].copy()


def _refresh_people_index() -> None:
    global _people_index, _people_vectorizer, _people_matrix

    names = sorted(_valid_people(df_dashboard)["pessoa"].dropna().unique().tolist())
    _people_index = names
    if not names:
        _people_vectorizer = None
        _people_matrix = None
        return

    _people_vectorizer = TfidfVectorizer(analyzer="char", ngram_range=(1, 3), lowercase=True)
    _people_matrix = _people_vectorizer.fit_transform([_fold(name) for name in names])


def _search_people(query: str, top_n: int = 12) -> list[dict[str, object]]:
    query = str(query or "").strip()
    if len(query) < 3 or _people_vectorizer is None or _people_matrix is None:
        return []

    query_fold = _fold(query).lower()
    query_vec = _people_vectorizer.transform([_fold(query)])
    sim = cosine_similarity(query_vec, _people_matrix).flatten()
    best = sim.argsort()[-top_n:][::-1]
    ranked: list[tuple[float, str]] = []
    seen: set[str] = set()

    for idx in best:
        score = float(sim[idx])
        if score <= 0:
            continue
        name = _people_index[idx]
        if name in seen:
            continue
        name_fold = _fold(name).lower()
        boost = 0.0
        if name_fold == query_fold:
            boost = 10.0
        elif query_fold in name_fold:
            boost = 2.0
        elif all(token in name_fold for token in query_fold.split() if token):
            boost = 1.0
        ranked.append((score + boost, name))
        seen.add(name)

    substring_matches = [name for name in _people_index if query_fold in _fold(name).lower()]
    for name in substring_matches:
        if name in seen:
            continue
        ranked.append((2.0, name))
        seen.add(name)

    ranked.sort(key=lambda item: item[0], reverse=True)
    return [{"nome": name, "score": round(score, 4)} for score, name in ranked[:top_n]]


def _person_trajectory_payload(name: str) -> dict[str, object]:
    person_name = str(name or "").strip()
    if not person_name:
        return {"nome": "", "stats": {}, "resumo": "", "rows": []}

    frame = _current_frame()
    dff = frame[frame["pessoa"] == person_name].copy().sort_values("data_movimentacao")
    dff = _deduplicate_person_rows(dff)

    if dff.empty:
        return {"nome": person_name, "stats": {}, "resumo": "", "rows": []}

    total_atos = int(len(dff))
    governos = int(dff.loc[dff["representante_origem"] != "", "representante_origem"].nunique())
    orgaos = int(dff.loc[dff["orgao"] != "", "orgao"].nunique())
    resumo = (
        f"{total_atos} atos | "
        f"{governos} {'governos' if governos != 1 else 'governo'} | "
        f"{orgaos} {'orgaos' if orgaos != 1 else 'orgao'}"
    )

    rows: list[dict[str, str]] = []
    for row in dff.itertuples(index=False):
        rows.append(
            {
                "data": row.data_movimentacao.strftime("%Y-%m-%d"),
                "tipo": row.tipo_ato,
                "orgao": row.orgao or "",
                "cargo": row.cargo or "",
                "governo": row.representante_origem or "",
            }
        )

    return {
        "nome": person_name,
        "stats": {"atos": total_atos, "governos": governos, "orgaos": orgaos},
        "resumo": resumo,
        "rows": rows,
    }


_refresh_people_index()


def _format_int(value: int) -> str:
    return f"{int(value):,}".replace(",", ".")


def _clean_governor_name(value: str | None) -> str:
    text = str(value or "").strip()
    if not text:
        return "Nao identificado"
    text = re.sub(r"\s*\([^)]*\)\s*$", "", text).strip()
    text = re.sub(r"\s*-\s*Governador.*$", "", text, flags=re.IGNORECASE).strip()
    return text or "Nao identificado"


def _current_governor_name(frame: pd.DataFrame) -> str:
    recentes = frame.loc[frame["representante_origem"] != ""].sort_values("data_movimentacao", ascending=False)
    if recentes.empty:
        return "Nao identificado"
    return _clean_governor_name(recentes.iloc[0]["representante_origem"])


def _current_frame() -> pd.DataFrame:
    # Reuse the shared base frame and only copy at mutation points.
    return df_dashboard


def _sidebar_status() -> dict[str, str]:
    frame = _current_frame()
    latest = frame["data_movimentacao"].max()
    return {
        "updated_at": latest.strftime("%d/%m/%Y") if pd.notna(latest) else "--/--/----",
        "source": "DOU-RJ",
    }


def _empty_to_none(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = str(value).strip()
    return cleaned or None


def _split_csv_param(value: str | None) -> list[str]:
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def _apply_filters(
    frame: pd.DataFrame,
    start: str | None,
    end: str | None,
    tipos: list[str],
    orgaos: list[str],
    cargos: list[str],
    governos: list[str],
) -> pd.DataFrame:
    filtered = frame

    if start:
        filtered = filtered[filtered["data_movimentacao"] >= pd.to_datetime(start)]
    if end:
        filtered = filtered[filtered["data_movimentacao"] <= pd.to_datetime(end)]
    if tipos:
        filtered = filtered[filtered["tipo_ato"].isin(tipos)]
    if orgaos:
        filtered = filtered[filtered["orgao"].isin(orgaos)]
    if cargos:
        filtered = filtered[filtered["cargo"].isin(cargos)]
    if governos:
        filtered = filtered[filtered["representante_origem"].isin(governos)]

    return filtered.copy()


def _metric_delta(current: int, previous: int) -> dict[str, str]:
    if previous <= 0:
        return {"label": "sem base anterior", "tone": "neutral"}
    change = ((current - previous) / previous) * 100
    prefix = "+" if change >= 0 else "-"
    return {
        "label": f"{prefix} {abs(change):.1f}% vs. periodo anterior".replace(".", ","),
        "tone": "positive" if change >= 0 else "negative",
    }


def _build_previous_period(frame: pd.DataFrame, start: str | None, end: str | None) -> pd.DataFrame:
    if not start or not end:
        return frame.iloc[0:0].copy()

    start_ts = pd.to_datetime(start)
    end_ts = pd.to_datetime(end)
    span_days = max((end_ts - start_ts).days, 1)
    previous_end = start_ts - pd.Timedelta(days=1)
    previous_start = previous_end - pd.Timedelta(days=span_days)
    return frame[
        (frame["data_movimentacao"] >= previous_start) & (frame["data_movimentacao"] <= previous_end)
    ].copy()


def _series_payload(filtered: pd.DataFrame) -> list[dict[str, object]]:
    grouped = (
        filtered.groupby(["ano_mes", "tipo_ato"])
        .size()
        .unstack(fill_value=0)
        .sort_index()
        .reset_index()
    )
    records: list[dict[str, object]] = []
    running_balance = 0
    for row in grouped.itertuples(index=False):
        nomeacoes = int(getattr(row, "nomeacao", 0))
        exoneracoes = int(getattr(row, "exoneracao", 0))
        running_balance += nomeacoes - exoneracoes
        records.append(
            {
                "periodo": row.ano_mes,
                "nomeacoes": nomeacoes,
                "exoneracoes": exoneracoes,
                "saldo": nomeacoes - exoneracoes,
                "saldo_acumulado": running_balance,
            }
        )
    return records


def _ranking_payload(filtered: pd.DataFrame) -> list[dict[str, object]]:
    valid = filtered[filtered["orgao"] != ""].copy()
    if valid.empty:
        return []

    grouped = (
        valid.groupby(["orgao", "tipo_ato"])
        .size()
        .unstack(fill_value=0)
        .rename(columns={"nomeacao": "nomeacoes", "exoneracao": "exoneracoes"})
    )
    grouped["saldo"] = grouped.get("nomeacoes", 0) - grouped.get("exoneracoes", 0)
    grouped["atos"] = grouped.get("nomeacoes", 0) + grouped.get("exoneracoes", 0)
    grouped = grouped.sort_values(["saldo", "atos"], ascending=[False, False]).head(10).reset_index()

    ranking: list[dict[str, object]] = []
    for row in grouped.itertuples(index=False):
        ranking.append(
            {
                "orgao": row.orgao,
                "nomeacoes": int(getattr(row, "nomeacoes", 0)),
                "exoneracoes": int(getattr(row, "exoneracoes", 0)),
                "saldo": int(getattr(row, "saldo", 0)),
                "atos": int(getattr(row, "atos", 0)),
            }
        )
    return ranking


def _timeline_payload(filtered: pd.DataFrame, limit: int = 6) -> list[dict[str, str]]:
    recent = filtered.sort_values("data_movimentacao", ascending=False).head(limit)
    items: list[dict[str, str]] = []
    for row in recent.itertuples(index=False):
        items.append(
            {
                "tipo": "Nomeacao" if row.tipo_ato == "nomeacao" else "Exoneracao",
                "pessoa": row.pessoa or "Pessoa nao identificada",
                "orgao": row.orgao or "Orgao nao identificado",
                "cargo": row.cargo or "Cargo nao informado",
                "governo": row.representante_origem or "Governo nao identificado",
                "data": row.data_movimentacao.strftime("%d/%m/%Y"),
            }
        )
    return items


def _sankey_payload(nomeacoes: int, exoneracoes: int) -> dict[str, object]:
    saldo = nomeacoes - exoneracoes
    labels = ["Nomeacoes", "Exoneracoes", "Saldo positivo" if saldo >= 0 else "Deficit"]
    colors = ["#2563eb", "#94a3b8", "#16a34a" if saldo >= 0 else "#dc2626"]
    links = {
        "source": [0, 1],
        "target": [2, 2],
        "value": [nomeacoes, exoneracoes],
        "color": ["rgba(37, 99, 235, 0.35)", "rgba(148, 163, 184, 0.35)"],
    }
    return {"labels": labels, "colors": colors, "links": links, "saldo": saldo}


def _options_payload(frame: pd.DataFrame) -> dict[str, object]:
    orgaos = sorted(item for item in frame["orgao"].dropna().unique().tolist() if item)[:250]
    cargos = sorted(item for item in frame["cargo"].dropna().unique().tolist() if item)[:250]
    governos = sorted(item for item in frame["representante_origem"].dropna().unique().tolist() if item)[:250]
    return {
        "bounds": {
            "min_date": dashboard_bounds.min_date,
            "max_date": dashboard_bounds.max_date,
        },
        "tipos": [
            {"label": "Nomeacoes", "value": "nomeacao"},
            {"label": "Exoneracoes", "value": "exoneracao"},
        ],
        "orgaos": orgaos,
        "cargos": cargos,
        "governos": governos,
    }


def _dashboard_payload(
    start: str | None,
    end: str | None,
    tipos: list[str],
    orgaos: list[str],
    cargos: list[str],
    governos: list[str],
) -> dict[str, object]:
    frame = _current_frame()
    filtered = _apply_filters(frame, start, end, tipos, orgaos, cargos, governos)
    previous = _build_previous_period(frame, start, end)

    nomeacoes = int((filtered["tipo_ato"] == "nomeacao").sum())
    exoneracoes = int((filtered["tipo_ato"] == "exoneracao").sum())
    saldo = nomeacoes - exoneracoes
    pessoas = int(filtered.loc[filtered["pessoa"] != "", "pessoa"].nunique())
    orgaos_unicos = int(filtered.loc[filtered["orgao"] != "", "orgao"].nunique())

    prev_nomeacoes = int((previous["tipo_ato"] == "nomeacao").sum())
    prev_exoneracoes = int((previous["tipo_ato"] == "exoneracao").sum())
    prev_pessoas = int(previous.loc[previous["pessoa"] != "", "pessoa"].nunique())
    prev_orgaos = int(previous.loc[previous["orgao"] != "", "orgao"].nunique())
    prev_saldo = prev_nomeacoes - prev_exoneracoes

    start_label = pd.to_datetime(start or dashboard_bounds.min_date).strftime("%d/%m/%Y")
    end_label = pd.to_datetime(end or dashboard_bounds.max_date).strftime("%d/%m/%Y")

    return {
        "periodo": {"inicio": start_label, "fim": end_label},
        "resumo": {
            "nomeacoes": nomeacoes,
            "exoneracoes": exoneracoes,
            "orgaos": orgaos_unicos,
            "pessoas": pessoas,
            "saldo": saldo,
            "atos": int(len(filtered)),
        },
        "metricas": [
            {
                "titulo": "Nomeacoes",
                "valor": _format_int(nomeacoes),
                "delta": _metric_delta(nomeacoes, prev_nomeacoes),
                "icone": "users-plus",
            },
            {
                "titulo": "Exoneracoes",
                "valor": _format_int(exoneracoes),
                "delta": _metric_delta(exoneracoes, prev_exoneracoes),
                "icone": "user-minus",
            },
            {
                "titulo": "Orgaos envolvidos",
                "valor": _format_int(orgaos_unicos),
                "delta": _metric_delta(orgaos_unicos, prev_orgaos),
                "icone": "building",
            },
            {
                "titulo": "Servidores afetados",
                "valor": _format_int(pessoas),
                "delta": _metric_delta(pessoas, prev_pessoas),
                "icone": "users",
            },
            {
                "titulo": "Saldo no periodo",
                "valor": f"{saldo:+,}".replace(",", "."),
                "delta": _metric_delta(saldo, prev_saldo) if prev_saldo != 0 else {"label": "sem base anterior", "tone": "neutral"},
                "icone": "scale",
            },
        ],
        "series": _series_payload(filtered),
        "ranking": _ranking_payload(filtered),
        "timeline": _timeline_payload(filtered),
        "sankey": _sankey_payload(nomeacoes, exoneracoes),
        "meta": {
            "fonte": "Diario Oficial do Estado do Rio de Janeiro (DOU-RJ)",
            "atualizacao": "Diaria, a partir do consolidado sincronizado do projeto fonte.",
            "cobertura": "Nomeacoes e exoneracoes publicadas em atos oficiais.",
            "granularidade": "Pessoa, cargo, orgao, data e governo de origem.",
        },
    }


def _summary_cards(frame: pd.DataFrame, tipo: str | None = None) -> list[dict[str, str]]:
    base = frame.copy()
    if tipo:
        base = base[base["tipo_ato"] == tipo]

    total = len(base)
    pessoas = int(base.loc[base["pessoa"] != "", "pessoa"].nunique())
    orgaos = int(base.loc[base["orgao"] != "", "orgao"].nunique())
    latest = base["data_movimentacao"].max()
    governador_atual = _current_governor_name(_current_frame())
    return [
        {"label": "Atos no recorte", "value": _format_int(total)},
        {"label": "Pessoas unicas", "value": _format_int(pessoas)},
        {"label": "Orgaos citados", "value": _format_int(orgaos)},
        {"label": "Ultima publicacao", "value": latest.strftime("%d/%m/%Y") if pd.notna(latest) else "--/--/----"},
        {"label": "Governador atual", "value": governador_atual},
    ]


def _recent_table(frame: pd.DataFrame, limit: int = 20) -> list[dict[str, str]]:
    recent = frame.sort_values("data_movimentacao", ascending=False).head(limit)
    rows: list[dict[str, str]] = []
    for row in recent.itertuples(index=False):
        rows.append(
            {
                "data": row.data_movimentacao.strftime("%d/%m/%Y"),
                "tipo": "Nomeacao" if row.tipo_ato == "nomeacao" else "Exoneracao",
                "pessoa": row.pessoa or "Pessoa nao identificada",
                "orgao": row.orgao or "Orgao nao identificado",
                "cargo": row.cargo or "Cargo nao informado",
                "governo": row.representante_origem or "Nao identificado",
            }
        )
    return rows


def _nomeacoes_context() -> dict[str, object]:
    frame = _current_frame()
    nomeacoes = frame[frame["tipo_ato"] == "nomeacao"].copy()
    orgaos = (
        nomeacoes[nomeacoes["orgao"] != ""]
        .groupby("orgao")
        .size()
        .sort_values(ascending=False)
        .head(12)
        .reset_index(name="total")
        .to_dict("records")
    )
    return {
        "page_title": "Nomeacoes",
        "page_heading": "Nomeacoes mais recentes",
        "page_description": "Leitura direta das entradas publicadas no consolidado enviado pelo projeto fonte.",
        "summary_cards": _summary_cards(nomeacoes, "nomeacao"),
        "table_rows": _recent_table(nomeacoes),
        "orgao_rows": orgaos,
    }


def _exoneracoes_context() -> dict[str, object]:
    frame = _current_frame()
    exoneracoes = frame[frame["tipo_ato"] == "exoneracao"].copy()
    orgaos = (
        exoneracoes[exoneracoes["orgao"] != ""]
        .groupby("orgao")
        .size()
        .sort_values(ascending=False)
        .head(12)
        .reset_index(name="total")
        .to_dict("records")
    )
    return {
        "page_title": "Exoneracoes",
        "page_heading": "Exoneracoes mais recentes",
        "page_description": "Painel de saidas com foco em volume, destino institucional e recorrencia recente.",
        "summary_cards": _summary_cards(exoneracoes, "exoneracao"),
        "table_rows": _recent_table(exoneracoes),
        "orgao_rows": orgaos,
    }


def _orgaos_context() -> dict[str, object]:
    frame = _current_frame()
    ranking = _ranking_payload(frame)
    recent = (
        frame[frame["orgao"] != ""]
        .groupby(["ano_mes", "orgao"])
        .size()
        .reset_index(name="total")
        .sort_values(["ano_mes", "total"], ascending=[False, False])
        .head(12)
    )
    return {
        "page_title": "Orgaos & Secretarias",
        "page_heading": "Orgaos com maior movimentacao",
        "page_description": "Comparativo entre entradas e saidas por orgao para localizar concentracao administrativa.",
        "summary_cards": _summary_cards(frame),
        "ranking_rows": ranking,
        "recent_rows": recent.to_dict("records"),
    }


def _servidores_context() -> dict[str, object]:
    frame = _current_frame()
    valid = _valid_people(frame)
    servidores = (
        valid
        .groupby("pessoa")
        .agg(
            atos=("pessoa", "size"),
            orgaos=("orgao", pd.Series.nunique),
            ultimo_ato=("data_movimentacao", "max"),
        )
        .sort_values(["atos", "ultimo_ato"], ascending=[False, False])
        .head(20)
        .reset_index()
    )
    servidores["ultimo_ato"] = servidores["ultimo_ato"].dt.strftime("%d/%m/%Y")
    return {
        "page_title": "Servidores",
        "page_heading": "Busca de servidores e trajetorias",
        "page_description": "Pesquise pelo nome para acompanhar a trajetoria completa da pessoa e veja quais servidores aparecem com mais recorrencia no consolidado.",
        "summary_cards": _summary_cards(frame),
        "server_rows": servidores.to_dict("records"),
    }


def _publicacoes_context() -> dict[str, object]:
    frame = _current_frame()
    publicacoes = (
        frame.groupby("ano_mes")
        .agg(
            atos=("tipo_ato", "size"),
            nomeacoes=("tipo_ato", lambda s: int((s == "nomeacao").sum())),
            exoneracoes=("tipo_ato", lambda s: int((s == "exoneracao").sum())),
        )
        .sort_index(ascending=False)
        .head(18)
        .reset_index()
    )
    dias = (
        frame.groupby(frame["data_movimentacao"].dt.strftime("%d/%m/%Y"))
        .size()
        .sort_values(ascending=False)
        .head(12)
        .reset_index(name="total")
    )
    return {
        "page_title": "Publicacoes",
        "page_heading": "Cadencia de publicacoes",
        "page_description": "Visao por mes e por dia para acompanhar ritmo de publicacao no Diario Oficial.",
        "summary_cards": _summary_cards(frame),
        "publication_rows": publicacoes.to_dict("records"),
        "day_rows": dias.to_dict("records"),
    }


def _downloads_context() -> dict[str, object]:
    frame = _current_frame()
    files = [
        {
            "label": "movimentacoes.parquet",
            "description": "Base principal consumida pelo painel, com nomeacoes e exoneracoes consolidadas.",
            "href": "/download/movimentacoes",
        },
        {
            "label": "retornos.parquet",
            "description": "Relacionamentos e retornos usados para leituras temporais complementares.",
            "href": "/download/retornos",
        },
        {
            "label": "Resumo JSON da home",
            "description": "Exportacao rapida do resumo atual para validacao externa.",
            "href": "/api/dashboard",
        },
    ]
    return {
        "page_title": "Downloads",
        "page_heading": "Arquivos entregues ao dash_temporal",
        "page_description": "Esta camada nao processa dados brutos; apenas disponibiliza o consolidado que chega do projeto principal.",
        "summary_cards": [
            {"label": "Movimentacoes", "value": _format_int(len(frame))},
            {"label": "Janela temporal", "value": f"{dashboard_bounds.min_date} ate {dashboard_bounds.max_date}"},
            {"label": "Arquivos expostos", "value": "3"},
        ],
        "download_rows": files,
    }


def _alertas_context() -> dict[str, object]:
    frame = _current_frame()
    latest = frame["data_movimentacao"].max()
    if pd.isna(latest):
        latest = pd.Timestamp.today().normalize()
    recent_start = latest - pd.Timedelta(days=30)
    previous_start = recent_start - pd.Timedelta(days=30)

    recent = frame[frame["data_movimentacao"] >= recent_start].copy()
    previous = frame[
        (frame["data_movimentacao"] >= previous_start) & (frame["data_movimentacao"] < recent_start)
    ].copy()

    recent_counts = recent[recent["orgao"] != ""].groupby("orgao").size()
    previous_counts = previous[previous["orgao"] != ""].groupby("orgao").size()
    delta = (
        pd.DataFrame({"recentes": recent_counts, "anteriores": previous_counts})
        .fillna(0)
        .assign(variacao=lambda df: df["recentes"] - df["anteriores"])
        .sort_values("variacao", ascending=False)
        .head(12)
        .reset_index()
        .rename(columns={"index": "orgao"})
    )

    return {
        "page_title": "Alertas",
        "page_heading": "Sinais de variacao recente",
        "page_description": "Comparacao simples entre os ultimos 30 dias e a janela imediatamente anterior para orientar acompanhamento.",
        "summary_cards": [
            {"label": "Atos nos ultimos 30 dias", "value": _format_int(len(recent))},
            {"label": "Janela comparada", "value": f"{recent_start.strftime('%d/%m/%Y')} ate {latest.strftime('%d/%m/%Y')}"},
            {"label": "Orgaos com alta", "value": _format_int(int((delta['variacao'] > 0).sum())) if not delta.empty else "0"},
        ],
        "alert_rows": delta.to_dict("records"),
        "timeline_rows": _timeline_payload(recent, limit=10),
    }


PAGE_PAYLOAD_BUILDERS: dict[str, Callable[[], dict[str, object]]] = {
    "nomeacoes": _nomeacoes_context,
    "exoneracoes": _exoneracoes_context,
    "orgaos": _orgaos_context,
    "servidores": _servidores_context,
    "publicacoes": _publicacoes_context,
    "downloads": _downloads_context,
    "alertas": _alertas_context,
}


def _render_page_shell(page_key: str):
    meta = PAGE_SHELL[page_key]
    return render_template(
        meta["template"],
        page_key=page_key,
        page_title=meta["title"],
        page_heading=meta["heading"],
        page_description=meta["description"],
        active_endpoint=meta["active_endpoint"],
    )


@app.context_processor
def inject_shell_defaults():
    return {"nav_items": NAV_ITEMS, "sidebar_status": _sidebar_status()}


@app.get("/")
def index():
    return render_template("index.html", page_title="Visao Geral", active_endpoint="index", page_key="index")


@app.get("/nomeacoes")
def nomeacoes_page():
    return _render_page_shell("nomeacoes")


@app.get("/exoneracoes")
def exoneracoes_page():
    return _render_page_shell("exoneracoes")


@app.get("/orgaos")
def orgaos_page():
    return _render_page_shell("orgaos")


@app.get("/servidores")
def servidores_page():
    return _render_page_shell("servidores")


@app.get("/trajetorias")
def trajetorias_page():
    return redirect(url_for("servidores_page"), code=302)


@app.get("/publicacoes")
def publicacoes_page():
    return _render_page_shell("publicacoes")


@app.get("/downloads")
def downloads_page():
    return _render_page_shell("downloads")


@app.get("/alertas")
def alertas_page():
    return _render_page_shell("alertas")


@app.get("/download/<dataset>")
def download_data(dataset: str):
    mapping = {
        "movimentacoes": dados.CONSOLIDATED_MOV,
        "retornos": dados.CONSOLIDATED_RET,
    }
    path = mapping.get(dataset)
    if path is None or not path.exists():
        abort(404)
    return send_file(path, as_attachment=True, download_name=path.name)


@app.get("/api/options")
def api_options():
    return jsonify(_options_payload(_current_frame()))


@app.get("/api/dashboard")
def api_dashboard():
    start = _empty_to_none(request.args.get("start"))
    end = _empty_to_none(request.args.get("end"))
    tipos = _split_csv_param(request.args.get("tipo"))
    orgaos = _split_csv_param(request.args.get("orgao"))
    cargos = _split_csv_param(request.args.get("cargo"))
    governos = _split_csv_param(request.args.get("governo"))
    return jsonify(_dashboard_payload(start, end, tipos, orgaos, cargos, governos))


@app.get("/api/page/<page_key>")
def api_page_payload(page_key: str):
    builder = PAGE_PAYLOAD_BUILDERS.get(page_key)
    if builder is None:
        abort(404)
    return jsonify(builder())


@app.get("/api/pessoas/search")
def api_people_search():
    query = _empty_to_none(request.args.get("q")) or ""
    return jsonify({"results": _search_people(query)})


@app.get("/api/pessoas/trajetoria")
def api_people_trajectory():
    name = _empty_to_none(request.args.get("nome")) or ""
    return jsonify(_person_trajectory_payload(name))


@app.post("/api/reload")
def api_reload():
    global df_dashboard, dashboard_bounds
    dados.df, dados.df_mov = dados.reload_consolidated_base()
    df_dashboard, dashboard_bounds = _load_dashboard_data()
    _refresh_people_index()
    return jsonify(
        {
            "status": "ok",
            "message": f"Consolidado recarregado com {_format_int(len(df_dashboard))} movimentacoes.",
            "bounds": {
                "min_date": dashboard_bounds.min_date,
                "max_date": dashboard_bounds.max_date,
            },
        }
    )


@app.get("/healthz")
def healthz():
    return {"status": "ok"}


if __name__ == "__main__":
    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", "8052"))
    app.run(host=host, port=port, debug=False)
