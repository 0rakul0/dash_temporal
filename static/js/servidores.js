const personInput = document.getElementById("person-search-input");
const clearButton = document.getElementById("person-search-clear");
const resultsHost = document.getElementById("person-search-results");
const trajectoryHost = document.getElementById("person-trajectory-panel");
const statsHost = document.getElementById("person-search-stats");

if (personInput && clearButton && resultsHost && trajectoryHost && statsHost) {
  let activeRequest = 0;
  let selectedName = "";

  const escapeHtml = (value) =>
    String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#39;");

  const setEmptyState = () => {
    trajectoryHost.innerHTML = `
      <div class="empty-state">
        <strong>Selecione uma pessoa para ver a trajetoria.</strong>
        <p>A busca reaproveita o filtro de limpeza para evitar patentes, cargos e outros textos ruidosos.</p>
      </div>
    `;
    statsHost.textContent = "";
  };

  const renderResults = (results) => {
    if (!results.length) {
      resultsHost.hidden = true;
      resultsHost.innerHTML = "";
      return;
    }

    resultsHost.innerHTML = results
      .map(
        (item) => `
          <button class="search-result-item" type="button" data-name="${escapeHtml(item.nome)}">
            <span>${escapeHtml(item.nome)}</span>
            <small>${Math.round(Math.min(item.score, 1) * 100)}%</small>
          </button>
        `,
      )
      .join("");
    resultsHost.hidden = false;
  };

  const renderTrajectory = (payload) => {
    if (!payload?.rows?.length) {
      trajectoryHost.innerHTML = `
        <div class="empty-state">
          <strong>Nenhum ato encontrado para ${escapeHtml(payload?.nome || "a pessoa selecionada")}.</strong>
          <p>Se esse nome estiver no consolidado do projeto fonte, vale recarregar a base para atualizar o indice.</p>
        </div>
      `;
      statsHost.textContent = "";
      return;
    }

    statsHost.textContent = payload.resumo || "";
    trajectoryHost.innerHTML = `
      <div class="trajectory-header">
        <div>
          <h3>Trajetoria de ${escapeHtml(payload.nome)}</h3>
          <p class="trajectory-summary">Historico consolidado por data, tipo de ato, orgao, cargo e governo.</p>
        </div>
      </div>
      <div class="table-wrapper">
        <table class="trajectory-table">
          <thead>
            <tr>
              <th>Data</th>
              <th>Tipo</th>
              <th>Orgao</th>
              <th>Cargo</th>
              <th>Governo</th>
            </tr>
          </thead>
          <tbody>
            ${payload.rows
              .map(
                (row) => `
                  <tr class="${row.tipo === "nomeacao" ? "is-nomeacao" : "is-exoneracao"}">
                    <td>${escapeHtml(row.data)}</td>
                    <td>${escapeHtml(row.tipo)}</td>
                    <td>${escapeHtml(row.orgao)}</td>
                    <td>${escapeHtml(row.cargo)}</td>
                    <td>${escapeHtml(row.governo)}</td>
                  </tr>
                `,
              )
              .join("")}
          </tbody>
        </table>
      </div>
    `;
  };

  const loadTrajectory = async (name) => {
    const cleaned = String(name || "").trim();
    if (!cleaned) {
      selectedName = "";
      setEmptyState();
      return;
    }

    selectedName = cleaned;
    personInput.value = cleaned;
    resultsHost.hidden = true;

    const response = await fetch(`/api/pessoas/trajetoria?nome=${encodeURIComponent(cleaned)}`);
    const payload = await response.json();
    renderTrajectory(payload);
  };

  const searchPeople = async (query) => {
    const cleaned = String(query || "").trim();
    if (cleaned.length < 3) {
      resultsHost.hidden = true;
      resultsHost.innerHTML = "";
      return;
    }

    const requestId = ++activeRequest;
    const response = await fetch(`/api/pessoas/search?q=${encodeURIComponent(cleaned)}`);
    const payload = await response.json();
    if (requestId !== activeRequest) {
      return;
    }
    renderResults(payload.results || []);
  };

  personInput.addEventListener("input", (event) => {
    const value = event.target.value;
    if (!value.trim()) {
      selectedName = "";
      setEmptyState();
    }
    window.clearTimeout(personInput._searchTimer);
    personInput._searchTimer = window.setTimeout(() => {
      searchPeople(value);
    }, 160);
  });

  personInput.addEventListener("keydown", (event) => {
    if (event.key === "Enter") {
      event.preventDefault();
      const firstButton = resultsHost.querySelector(".search-result-item");
      if (firstButton) {
        firstButton.click();
      } else if (personInput.value.trim() && personInput.value.trim() !== selectedName) {
        loadTrajectory(personInput.value.trim());
      }
    }
  });

  clearButton.addEventListener("click", () => {
    personInput.value = "";
    selectedName = "";
    resultsHost.hidden = true;
    resultsHost.innerHTML = "";
    setEmptyState();
  });

  resultsHost.addEventListener("click", (event) => {
    const button = event.target.closest(".search-result-item");
    if (!button) {
      return;
    }
    loadTrajectory(button.dataset.name || "");
  });

  document.addEventListener("click", (event) => {
    const shortcut = event.target.closest(".person-shortcut");
    if (!shortcut) {
      return;
    }
    loadTrajectory(shortcut.dataset.person || "");
    shortcut.scrollIntoView({ behavior: "smooth", block: "center" });
  });

  const params = new URLSearchParams(window.location.search);
  const presetName = params.get("nome");
  if (presetName) {
    loadTrajectory(presetName);
  } else {
    setEmptyState();
  }
}
