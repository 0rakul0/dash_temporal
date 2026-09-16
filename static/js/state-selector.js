const IBGE_MESH_URL = "https://servicodados.ibge.gov.br/api/v3/malhas/estados";
const RIO_DE_JANEIRO_CODE = "33";
const STATE_NAMES = {
  11: "Rondônia", 12: "Acre", 13: "Amazonas", 14: "Roraima", 15: "Pará", 16: "Amapá", 17: "Tocantins",
  21: "Maranhão", 22: "Piauí", 23: "Ceará", 24: "Rio Grande do Norte", 25: "Paraíba", 26: "Pernambuco", 27: "Alagoas", 28: "Sergipe", 29: "Bahia",
  31: "Minas Gerais", 32: "Espírito Santo", 33: "Rio de Janeiro", 35: "São Paulo",
  41: "Paraná", 42: "Santa Catarina", 43: "Rio Grande do Sul",
  50: "Mato Grosso do Sul", 51: "Mato Grosso", 52: "Goiás", 53: "Distrito Federal",
};

const svg = document.getElementById("brazil-map");
const status = document.getElementById("state-map-status");
const ns = "http://www.w3.org/2000/svg";

function coordinatesFromGeometry(geometry) {
  return geometry.type === "Polygon" ? geometry.coordinates : geometry.coordinates.flat();
}

function createPath(rings, project) {
  return rings.map((ring) => ring.map(([longitude, latitude], index) => {
    const [x, y] = project(longitude, latitude);
    return `${index === 0 ? "M" : "L"}${x.toFixed(2)} ${y.toFixed(2)}`;
  }).join(" ") + "Z").join(" ");
}

async function loadOfficialMap() {
  const codes = Object.keys(STATE_NAMES);
  const results = await Promise.allSettled(codes.map(async (code) => {
    const response = await fetch(`${IBGE_MESH_URL}/${code}?formato=application/vnd.geo+json&qualidade=minima`);
    if (!response.ok) throw new Error(`IBGE respondeu ${response.status}`);
    const collection = await response.json();
    return { code, geometry: collection.features[0].geometry };
  }));
  const states = results.filter((result) => result.status === "fulfilled").map((result) => result.value);
  if (states.length !== codes.length) throw new Error("Malhas incompletas");

  const points = states.flatMap((state) => coordinatesFromGeometry(state.geometry).flat());
  const longitudes = points.map(([longitude]) => longitude);
  const latitudes = points.map(([, latitude]) => latitude);
  const padding = 24;
  const longitudeSpan = Math.max(...longitudes) - Math.min(...longitudes);
  const latitudeSpan = Math.max(...latitudes) - Math.min(...latitudes);
  const scale = Math.min((620 - padding * 2) / longitudeSpan, (680 - padding * 2) / latitudeSpan);
  const offsetX = (620 - longitudeSpan * scale) / 2 - Math.min(...longitudes) * scale;
  const offsetY = (680 - latitudeSpan * scale) / 2 + Math.max(...latitudes) * scale;
  const project = (longitude, latitude) => [offsetX + longitude * scale, offsetY - latitude * scale];

  svg.replaceChildren();
  states.forEach(({ code, geometry }) => {
    const available = code === RIO_DE_JANEIRO_CODE;
    const path = document.createElementNS(ns, "path");
    path.setAttribute("d", createPath(coordinatesFromGeometry(geometry), project));
    path.setAttribute("class", `map-state ${available ? "available" : "unavailable"}`);
    path.setAttribute("aria-label", STATE_NAMES[code]);
    path.setAttribute("tabindex", available ? "0" : "-1");
    path.addEventListener("mouseenter", () => {
      status.textContent = available ? "Rio de Janeiro: dados disponíveis. Clique para abrir." : `${STATE_NAMES[code]}: ainda sem dados disponíveis.`;
    });
    if (available) {
      path.setAttribute("role", "link");
      path.addEventListener("click", () => { window.location.assign("/rj"); });
      path.addEventListener("keydown", (event) => {
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          window.location.assign("/rj");
        }
      });
    }
    svg.appendChild(path);
  });
  svg.classList.add("is-ready");
  status.textContent = "Selecione o Rio de Janeiro para continuar.";
}

loadOfficialMap().catch(() => {
  status.textContent = "Não foi possível carregar o mapa oficial agora. Tente novamente em instantes.";
  svg.replaceChildren();
  const message = document.createElementNS(ns, "text");
  message.setAttribute("class", "map-loading");
  message.setAttribute("x", "310");
  message.setAttribute("y", "340");
  message.setAttribute("text-anchor", "middle");
  message.textContent = "Mapa indisponível";
  svg.appendChild(message);
});
