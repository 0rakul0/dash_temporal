const pageKey = document.body.dataset.pageKey;

document.addEventListener("DOMContentLoaded", async () => {
  if (!pageKey || pageKey === "index") {
    return;
  }

  const response = await fetch(`/api/page/${pageKey}`);
  const payload = await response.json();
  renderPagePayload(pageKey, payload);
});

function renderPagePayload(key, payload) {
  renderSummaryGrid(payload.summary_cards || []);

  const renderers = {
    nomeacoes: renderNomeacoesPage,
    exoneracoes: renderExoneracoesPage,
    orgaos: renderOrgaosPage,
    servidores: renderServidoresPage,
    publicacoes: renderPublicacoesPage,
    downloads: renderDownloadsPage,
    alertas: renderAlertasPage,
  };

  const renderer = renderers[key];
  if (renderer) {
    renderer(payload);
  }
}

function renderSummaryGrid(cards) {
  const host = document.getElementById("summary-grid");
  if (!host) {
    return;
  }

  host.innerHTML = cards
    .map(
      (card) => `
        <article class="panel summary-card">
          <span>${escapeHtml(card.label)}</span>
          <strong>${escapeHtml(card.value)}</strong>
        </article>
      `,
    )
    .join("");
}

function renderNomeacoesPage(payload) {
  renderRecentActsTable(payload.table_rows || []);
  renderSimpleList("orgao-list", payload.orgao_rows || [], (row) => `
    <div class="list-row">
      <strong>${escapeHtml(row.orgao)}</strong>
      <span>${escapeHtml(String(row.total))} nomeacoes</span>
    </div>
  `);
}

function renderExoneracoesPage(payload) {
  renderRecentActsTable(payload.table_rows || []);
  renderSimpleList("orgao-list", payload.orgao_rows || [], (row) => `
    <div class="list-row">
      <strong>${escapeHtml(row.orgao)}</strong>
      <span>${escapeHtml(String(row.total))} exoneracoes</span>
    </div>
  `);
}

function renderOrgaosPage(payload) {
  const host = document.getElementById("ranking-body");
  if (host) {
    host.innerHTML = (payload.ranking_rows || [])
      .map(
        (row) => `
          <tr>
            <td>${escapeHtml(row.orgao)}</td>
            <td>${escapeHtml(String(row.nomeacoes))}</td>
            <td>${escapeHtml(String(row.exoneracoes))}</td>
            <td>${escapeHtml(String(row.saldo))}</td>
            <td>${escapeHtml(String(row.atos))}</td>
          </tr>
        `,
      )
      .join("");
  }

  renderSimpleList("recent-list", payload.recent_rows || [], (row) => `
    <div class="list-row">
      <strong>${escapeHtml(row.orgao)}</strong>
      <span>${escapeHtml(row.ano_mes)} | ${escapeHtml(String(row.total))} atos</span>
    </div>
  `);
}

function renderServidoresPage(payload) {
  const host = document.getElementById("server-body");
  if (!host) {
    return;
  }

  host.innerHTML = (payload.server_rows || [])
    .map(
      (row) => `
        <tr>
          <td>${escapeHtml(row.pessoa)}</td>
          <td>${escapeHtml(String(row.atos))}</td>
          <td>${escapeHtml(String(row.orgaos))}</td>
          <td>${escapeHtml(row.ultimo_ato)}</td>
          <td><button class="link-button person-shortcut" type="button" data-person="${escapeHtml(row.pessoa)}">Ver trajetoria</button></td>
        </tr>
      `,
    )
    .join("");
}

function renderPublicacoesPage(payload) {
  const host = document.getElementById("publication-body");
  if (host) {
    host.innerHTML = (payload.publication_rows || [])
      .map(
        (row) => `
          <tr>
            <td>${escapeHtml(row.ano_mes)}</td>
            <td>${escapeHtml(String(row.atos))}</td>
            <td>${escapeHtml(String(row.nomeacoes))}</td>
            <td>${escapeHtml(String(row.exoneracoes))}</td>
          </tr>
        `,
      )
      .join("");
  }

  renderSimpleList("day-list", payload.day_rows || [], (row) => `
    <div class="list-row">
      <strong>${escapeHtml(row.data_movimentacao)}</strong>
      <span>${escapeHtml(String(row.total))} atos</span>
    </div>
  `);
}

function renderDownloadsPage(payload) {
  const host = document.getElementById("downloads-grid");
  if (!host) {
    return;
  }

  host.innerHTML = (payload.download_rows || [])
    .map(
      (row) => `
        <article class="panel download-card">
          <h2>${escapeHtml(row.label)}</h2>
          <p>${escapeHtml(row.description)}</p>
          <a class="primary-button button-link" href="${escapeHtml(row.href)}">Abrir arquivo</a>
        </article>
      `,
    )
    .join("");
}

function renderAlertasPage(payload) {
  const host = document.getElementById("alert-body");
  if (host) {
    host.innerHTML = (payload.alert_rows || [])
      .map(
        (row) => {
          const variation = parseInt(row.variacao, 10) || 0;
          const variationLabel = variation > 0 ? `+${variation}` : String(variation);
          return `
          <tr>
            <td>${escapeHtml(row.orgao)}</td>
            <td>${escapeHtml(String(parseInt(row.recentes, 10) || 0))}</td>
            <td>${escapeHtml(String(parseInt(row.anteriores, 10) || 0))}</td>
            <td>${escapeHtml(variationLabel)}</td>
          </tr>
        `;
        },
      )
      .join("");
  }

  const timeline = document.getElementById("timeline-list");
  if (timeline) {
    timeline.innerHTML = (payload.timeline_rows || [])
      .map(
        (row) => `
          <article class="timeline-item ${escapeHtml(row.tipo.toLowerCase())}">
            <div class="timeline-dot"></div>
            <div class="timeline-content">
              <strong>${escapeHtml(row.tipo)}</strong>
              <p>${escapeHtml(row.cargo)}</p>
              <p>${escapeHtml(row.orgao)}</p>
              <span class="timeline-date">${escapeHtml(row.data)}</span>
            </div>
          </article>
        `,
      )
      .join("");
  }
}

function renderRecentActsTable(rows) {
  const host = document.getElementById("recent-table-body");
  if (!host) {
    return;
  }

  host.innerHTML = rows
    .map(
      (row) => `
        <tr>
          <td>${escapeHtml(row.data)}</td>
          <td>${escapeHtml(row.pessoa)}</td>
          <td>${escapeHtml(row.orgao)}</td>
          <td>${escapeHtml(row.cargo)}</td>
          <td>${escapeHtml(row.governo)}</td>
        </tr>
      `,
    )
    .join("");
}

function renderSimpleList(hostId, rows, renderer) {
  const host = document.getElementById(hostId);
  if (!host) {
    return;
  }
  host.innerHTML = rows.map(renderer).join("");
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}
