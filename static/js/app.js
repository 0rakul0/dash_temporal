const state = {
  options: null,
  dashboard: null,
};

document.addEventListener("DOMContentLoaded", async () => {
  wireDashboard();
  await loadOptions();
  await loadDashboard();
});

function wireDashboard() {
  ["start-date", "end-date", "tipo-ato", "orgao", "cargo", "governo"].forEach((id) => {
    document.getElementById(id).addEventListener("change", () => loadDashboard());
  });

  document.getElementById("clear-filters").addEventListener("click", clearFilters);
  document.getElementById("reload-data").addEventListener("click", reloadConsolidated);
  document.getElementById("export-json").addEventListener("click", exportSummary);
}

async function loadOptions() {
  const response = await fetch("/api/options");
  state.options = await response.json();

  const { bounds, tipos, orgaos, cargos, governos } = state.options;
  const startDate = document.getElementById("start-date");
  const endDate = document.getElementById("end-date");

  startDate.min = bounds.min_date;
  startDate.max = bounds.max_date;
  endDate.min = bounds.min_date;
  endDate.max = bounds.max_date;
  startDate.value = "2025-01-01";
  endDate.value = bounds.max_date;

  fillSelect("tipo-ato", tipos.map((item) => ({ value: item.value, label: item.label })));
  fillSelect("orgao", orgaos.map((value) => ({ value, label: value })));
  fillSelect("cargo", cargos.map((value) => ({ value, label: value })));
  fillSelect("governo", governos.map((value) => ({ value, label: value })));
}

function fillSelect(id, items) {
  const select = document.getElementById(id);
  select.innerHTML = "";

  const emptyOption = document.createElement("option");
  emptyOption.value = "";
  emptyOption.textContent = "Todos";
  select.appendChild(emptyOption);

  items.forEach((item) => {
    const option = document.createElement("option");
    option.value = item.value;
    option.textContent = item.label;
    select.appendChild(option);
  });
}

function selectedValue(id) {
  return document.getElementById(id).value;
}

function buildQueryString() {
  const params = new URLSearchParams();
  const start = document.getElementById("start-date").value;
  const end = document.getElementById("end-date").value;
  const tipo = selectedValue("tipo-ato");
  const orgao = selectedValue("orgao");
  const cargo = selectedValue("cargo");
  const governo = selectedValue("governo");

  if (start) params.set("start", start);
  if (end) params.set("end", end);
  if (tipo) params.set("tipo", tipo);
  if (orgao) params.set("orgao", orgao);
  if (cargo) params.set("cargo", cargo);
  if (governo) params.set("governo", governo);

  return params.toString();
}

async function loadDashboard() {
  const response = await fetch(`/api/dashboard?${buildQueryString()}`);
  state.dashboard = await response.json();
  renderMetrics();
  renderCharts();
  renderRanking();
  renderTimeline();
  renderMeta();
  updatePeriodLabels();
}

function updatePeriodLabels() {
  const label = `${state.dashboard.periodo.inicio} - ${state.dashboard.periodo.fim}`;
  document.getElementById("hero-period-label").textContent = label;
}

function renderMetrics() {
  const grid = document.getElementById("metricas");
  grid.innerHTML = "";

  state.dashboard.metricas.forEach((metric) => {
    const article = document.createElement("article");
    article.className = "metric-card";
    article.innerHTML = `
      <div class="metric-icon">${sharedIconSvg[metric.icone] || ""}</div>
      <div>
        <h3>${metric.titulo}</h3>
        <strong>${metric.valor}</strong>
        <span class="metric-delta ${metric.delta.tone}">${metric.delta.label}</span>
      </div>
    `;
    grid.appendChild(article);
  });
}

function renderCharts() {
  const periods = state.dashboard.series.map((item) => item.periodo);
  const nomeacoes = state.dashboard.series.map((item) => item.nomeacoes);
  const exoneracoes = state.dashboard.series.map((item) => item.exoneracoes);
  const saldoAcumulado = state.dashboard.series.map((item) => item.saldo_acumulado);

  Plotly.newPlot(
    "monthly-chart",
    [
      {
        x: periods,
        y: nomeacoes,
        mode: "lines+markers",
        name: "Nomeacoes",
        line: { color: "#2563eb", width: 2.4 },
        marker: { size: 5, color: "#2563eb" },
      },
      {
        x: periods,
        y: exoneracoes,
        mode: "lines+markers",
        name: "Exoneracoes",
        line: { color: "#9aa8bb", width: 2.2 },
        marker: { size: 4, color: "#9aa8bb" },
      },
    ],
    baseLayout({
      height: 250,
      margin: { l: 34, r: 10, t: 8, b: 34 },
      yaxis: { gridcolor: "rgba(148,163,184,0.16)", zeroline: false },
    })
  );

  Plotly.newPlot(
    "balance-chart",
    [
      {
        x: periods,
        y: saldoAcumulado,
        mode: "lines",
        fill: "tozeroy",
        name: "Saldo acumulado",
        line: { color: "#2563eb", width: 2.5 },
        fillcolor: "rgba(37,99,235,0.15)",
      },
    ],
    baseLayout({
      height: 250,
      margin: { l: 34, r: 10, t: 8, b: 34 },
      yaxis: { gridcolor: "rgba(148,163,184,0.16)", zeroline: false },
    })
  );

  Plotly.newPlot(
    "flow-chart",
    [
      {
        type: "sankey",
        arrangement: "snap",
        node: {
          pad: 18,
          thickness: 24,
          line: { color: "rgba(15,23,42,0.08)", width: 1 },
          label: state.dashboard.sankey.labels,
          color: state.dashboard.sankey.colors,
        },
        link: state.dashboard.sankey.links,
      },
    ],
    baseLayout({
      height: 250,
      margin: { l: 10, r: 10, t: 8, b: 8 },
    })
  );
}

function baseLayout(extra) {
  return {
    paper_bgcolor: "rgba(0,0,0,0)",
    plot_bgcolor: "rgba(0,0,0,0)",
    font: { family: "Source Sans 3, sans-serif", color: "#334155", size: 12 },
    legend: { orientation: "h", y: 1.08, x: 0 },
    xaxis: { showgrid: false, tickfont: { size: 11 } },
    yaxis: { tickfont: { size: 11 } },
    ...extra,
  };
}

function renderRanking() {
  const body = document.getElementById("ranking-body");
  body.innerHTML = "";

  state.dashboard.ranking.forEach((item) => {
    const row = document.createElement("tr");
    const saldoClass = item.saldo >= 0 ? "saldo-positive" : "saldo-negative";
    row.innerHTML = `
      <td>${item.orgao}</td>
      <td>${formatInt(item.nomeacoes)}</td>
      <td>${formatInt(item.exoneracoes)}</td>
      <td class="${saldoClass}">${item.saldo > 0 ? "+" : ""}${formatInt(item.saldo)}</td>
    `;
    body.appendChild(row);
  });
}

function renderTimeline() {
  const list = document.getElementById("timeline-list");
  list.innerHTML = "";

  state.dashboard.timeline.forEach((item) => {
    const article = document.createElement("article");
    article.className = `timeline-item ${item.tipo.toLowerCase()}`;
    article.innerHTML = `
      <div class="timeline-dot"></div>
      <div class="timeline-content">
        <strong>${item.tipo}</strong>
        <p>${item.cargo}</p>
        <p>${item.orgao}</p>
        <span class="timeline-date">${item.data}</span>
      </div>
    `;
    list.appendChild(article);
  });
}

function renderMeta() {
  const metaList = document.getElementById("meta-list");
  metaList.innerHTML = "";

  Object.entries(state.dashboard.meta).forEach(([key, value]) => {
    const item = document.createElement("div");
    item.className = "meta-item";
    item.innerHTML = `
      <div class="meta-item-icon">${sharedIconSvg[metaIconKey(key)] || ""}</div>
      <div>
        <strong>${metaLabel(key)}</strong>
        <p>${value}</p>
      </div>
    `;
    metaList.appendChild(item);
  });
}

function metaIconKey(key) {
  const labels = {
    fonte: "file",
    atualizacao: "calendar",
    cobertura: "users",
    granularidade: "building",
  };
  return labels[key] || "info";
}

function metaLabel(key) {
  const labels = {
    fonte: "Fontes",
    atualizacao: "Atualizacao",
    cobertura: "Cobertura",
    granularidade: "Granularidade",
  };
  return labels[key] || key;
}

function clearFilters() {
  const { bounds } = state.options;
  document.getElementById("start-date").value = "2025-01-01";
  document.getElementById("end-date").value = bounds.max_date;
  ["tipo-ato", "orgao", "cargo", "governo"].forEach((id) => {
    document.getElementById(id).value = "";
  });
  loadDashboard();
}

async function reloadConsolidated() {
  const response = await fetch("/api/reload", { method: "POST" });
  const payload = await response.json();
  document.getElementById("reload-status").textContent = payload.message;
  await loadOptions();
  await loadDashboard();
}

function exportSummary() {
  if (!state.dashboard) return;
  const blob = new Blob([JSON.stringify(state.dashboard, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = "dou-rj-resumo.json";
  link.click();
  URL.revokeObjectURL(url);
}

function formatInt(value) {
  return new Intl.NumberFormat("pt-BR").format(value);
}
