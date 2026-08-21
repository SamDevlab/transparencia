import fs from "node:fs";
import path from "node:path";

const root = process.cwd();
const regionRoot = path.join(root, "regions", "bahia");
const dataRoot = path.join(regionRoot, "data");
const snapshotsRoot = path.join(dataRoot, "snapshots");
const outputRoot = path.join(root, "public", "data");

function readJson(file) {
  return JSON.parse(fs.readFileSync(file, "utf8"));
}

function writeJson(file, payload) {
  fs.mkdirSync(path.dirname(file), { recursive: true });
  fs.writeFileSync(file, JSON.stringify(payload), "utf8");
}

function slugSearch(value) {
  return String(value ?? "")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .replace(/\s+/g, " ")
    .trim();
}

function datedSnapshotDirs() {
  if (!fs.existsSync(snapshotsRoot)) return [];
  return fs.readdirSync(snapshotsRoot, { withFileTypes: true })
    .filter((entry) => entry.isDirectory() && /^\d{4}-\d{2}-\d{2}$/.test(entry.name))
    .map((entry) => path.join(snapshotsRoot, entry.name))
    .filter((dir) => fs.existsSync(path.join(dir, "coverage.json")))
    .sort();
}

function scopeHasRealRows(scope) {
  return scope?.status === "complete_for_api_query"
    && (Number(scope.current_export_rows ?? 0) + Number(scope.current_import_rows ?? 0)) > 0;
}

function validEconomicSnapshot(dir) {
  if (!dir || !fs.existsSync(path.join(dir, "coverage.json"))) return false;
  let coverage;
  try {
    coverage = readJson(path.join(dir, "coverage.json"));
  } catch {
    return false;
  }
  return scopeHasRealRows(coverage.bahia)
    && scopeHasRealRows(coverage.salvador)
    && fs.existsSync(path.join(dir, "bahia", "summary.json"))
    && fs.existsSync(path.join(dir, "salvador", "summary.json"));
}

function latestObservedSnapshot() {
  return datedSnapshotDirs().at(-1) ?? null;
}

function latestSnapshot() {
  const pointer = path.join(dataRoot, "latest.json");
  if (fs.existsSync(pointer)) {
    try {
      const latest = readJson(pointer);
      const candidate = path.join(root, latest.path ?? "");
      if (latest.path && validEconomicSnapshot(candidate)) return candidate;
    } catch {
      // Ponteiro inválido não substitui a busca por um snapshot anterior válido.
    }
  }
  return datedSnapshotDirs().filter(validEconomicSnapshot).at(-1) ?? null;
}

function sanitizedObservedCoverage(snapshot) {
  if (!snapshot) return null;
  const coverage = readJson(path.join(snapshot, "coverage.json"));
  const clean = structuredClone(coverage);
  for (const scope of ["bahia", "salvador"]) {
    const item = clean?.[scope];
    if (item?.status === "complete_for_api_query"
      && (Number(item.current_export_rows ?? 0) + Number(item.current_import_rows ?? 0)) === 0) {
      item.status = "invalid_empty_query";
      item.note = "A API respondeu com lista vazia para exportação e importação. O projeto rejeitou esse resultado como falso zero e não publicou valores econômicos.";
    }
  }
  return clean;
}

function readScope(snapshot, name) {
  const dir = path.join(snapshot, name);
  const summary = path.join(dir, "summary.json");
  if (!fs.existsSync(summary)) return null;
  const optional = (file, fallback) => fs.existsSync(path.join(dir, file)) ? readJson(path.join(dir, file)) : fallback;
  return {
    summary: readJson(summary),
    products: optional("products.json", []),
    countries: optional("countries.json", []),
    monthly: optional("monthly.json", []),
    opportunities: optional("opportunities.json", []),
  };
}

const config = readJson(path.join(regionRoot, "config.json"));
const snapshot = latestSnapshot();
const observedSnapshot = latestObservedSnapshot();
let economy;

if (!snapshot) {
  const observedCoverage = sanitizedObservedCoverage(observedSnapshot);
  economy = {
    available: false,
    reason: observedCoverage
      ? "A coleta econômica mais recente não passou pelos critérios de publicação. O site não converte consulta vazia ou falha externa em US$ 0."
      : "Nenhum snapshot econômico validado foi encontrado ainda.",
    observedSnapshot: observedSnapshot ? path.basename(observedSnapshot) : null,
    bahia: null,
    salvador: null,
    coverage: observedCoverage ?? {
      bahia: { status: "not_collected" },
      salvador: { status: "not_collected" },
      interstate_dependency: {
        status: "source_mapped_not_normalized",
        source: "SEI - Matriz de Insumo-Produto da Bahia",
      },
    },
    methodology: config.methodology,
  };
} else {
  const coverage = readJson(path.join(snapshot, "coverage.json"));
  economy = {
    available: true,
    snapshot: path.basename(snapshot),
    bahia: readScope(snapshot, "bahia"),
    salvador: readScope(snapshot, "salvador"),
    coverage,
    methodology: config.methodology,
  };
}

writeJson(path.join(outputRoot, "economy.json"), economy);

const dashboardPath = path.join(outputRoot, "dashboard.json");
const dashboard = fs.existsSync(dashboardPath) ? readJson(dashboardPath) : {};
const finalStatus = dashboard.finalStatus ?? {};
const acquisitionSummary = dashboard.acquisitions?.summary ?? {};

const statusPt = (status) => ({
  complete_for_filter: "Completo para o filtro",
  complete_for_api_query: "Completo para a consulta",
  partial: "Parcial",
  unavailable: "Indisponível",
  not_collected: "Ainda não coletado",
  invalid_empty_query: "Consulta vazia rejeitada",
  source_mapped_not_normalized: "Fonte mapeada; normalização pendente",
  historical_baseline_normalized: "Linha de base histórica normalizada",
}[status] ?? status ?? "Não informado");

const transparency = {
  asOf: dashboard.asOf ?? null,
  datasets: [
    {
      id: "salvador_aquisicoes",
      title: "Aquisições da Prefeitura",
      status: acquisitionSummary.complete_for_filter ? "complete_for_filter" : (acquisitionSummary.completeness_status ?? "complete_for_filter"),
      statusLabel: "Completo para o filtro publicado",
      detail: `${acquisitionSummary.records_received ?? 0} registros e ${acquisitionSummary.pages_collected ?? 0} páginas no recorte municipal.`,
      source: "Portal da Transparência de Salvador",
      href: "/licitacoes",
    },
    {
      id: "salvador_financas",
      title: "Receitas e despesas de Salvador",
      status: "collected",
      statusLabel: "Dados oficiais preservados",
      detail: "Receita, empenho, liquidação e pagamento permanecem separados.",
      source: "Portal da Transparência de Salvador",
      href: "/financas",
    },
    {
      id: "salvador_contratos",
      title: "Contratos individualizados",
      status: finalStatus.datasets?.prefeitura_detailed_contract_grid?.status ?? "partial",
      statusLabel: "Cobertura municipal detalhada parcial",
      detail: "A grade municipal detalhada pode apresentar tempo de resposta esgotado; PNCP é mantido como fonte complementar.",
      source: "Prefeitura de Salvador + PNCP",
      href: "/contratos",
    },
    {
      id: "cms",
      title: "Câmara Municipal",
      status: finalStatus.datasets?.cms_commitments?.status ?? "partial",
      statusLabel: "Cobertura condicionada à validação do parser",
      detail: "Gasto institucional não é atribuído a vereador sem documento nominal.",
      source: "Câmara Municipal de Salvador",
      href: "/camara",
    },
    {
      id: "bahia_comex",
      title: "Comércio exterior da Bahia",
      status: economy.coverage?.bahia?.status ?? "not_collected",
      statusLabel: statusPt(economy.coverage?.bahia?.status),
      detail: economy.coverage?.bahia?.note ?? economy.coverage?.bahia?.methodology ?? config.methodology.state_trade,
      source: "MDIC / Comex Stat",
      href: "/economia/bahia",
    },
    {
      id: "salvador_comex",
      title: "Comércio exterior de empresas de Salvador",
      status: economy.coverage?.salvador?.status ?? "not_collected",
      statusLabel: statusPt(economy.coverage?.salvador?.status),
      detail: economy.coverage?.salvador?.note ?? economy.coverage?.salvador?.methodology ?? config.methodology.capital_trade,
      source: "MDIC / Comex Stat",
      href: "/economia/salvador",
    },
    {
      id: "bahia_interestadual",
      title: "Dependência interestadual da Bahia",
      status: economy.coverage?.interstate_dependency?.status ?? "source_mapped_not_normalized",
      statusLabel: statusPt(economy.coverage?.interstate_dependency?.status),
      detail: economy.coverage?.interstate_dependency?.note ?? "A dependência entre estados é tratada separadamente do comércio exterior.",
      source: "SEI - Matriz de Insumo-Produto da Bahia",
      href: "/economia/oportunidades",
    },
  ],
};
writeJson(path.join(outputRoot, "transparency.json"), transparency);

const searchPath = path.join(outputRoot, "search.json");
if (fs.existsSync(searchPath) && economy.available) {
  const search = readJson(searchPath);
  const extras = [];
  for (const [scope, label] of [["bahia", "Bahia"], ["salvador", "Salvador"]]) {
    const data = economy[scope];
    if (!data) continue;
    for (const row of data.products.slice(0, 250)) {
      const ref = row.sh4 || row.product || "";
      extras.push({
        tipo: "Produto do comércio exterior",
        grupo: `Economia ${label}`,
        titulo: row.sh4 ? `SH4 ${row.sh4} · ${row.product}` : row.product,
        detalhe: `${label} · exportações e importações`,
        referencia: row.balance_fob < 0 ? "Saldo comercial negativo no recorte" : "Saldo comercial não negativo no recorte",
        href: `/economia/${scope === "bahia" ? "bahia" : "salvador"}?busca=${encodeURIComponent(ref)}`,
        termos: slugSearch([row.sh4, row.product, row.top_import_country?.country, row.top_export_country?.country].filter(Boolean).join(" ")),
      });
    }
    for (const row of data.countries.slice(0, 80)) {
      extras.push({
        tipo: "País parceiro comercial",
        grupo: `Economia ${label}`,
        titulo: row.country,
        detalhe: `${label} · comércio exterior`,
        referencia: row.country_code ? `Código ${row.country_code}` : "",
        href: `/economia/${scope === "bahia" ? "bahia" : "salvador"}?busca=${encodeURIComponent(row.country)}`,
        termos: slugSearch([row.country, row.country_code, label].filter(Boolean).join(" ")),
      });
    }
  }
  search.rows = [...search.rows, ...extras];
  writeJson(searchPath, search);
}

const metaPath = path.join(outputRoot, "meta.json");
if (fs.existsSync(metaPath)) {
  const meta = readJson(metaPath);
  meta.economyAvailable = economy.available;
  meta.economySnapshot = economy.snapshot ?? null;
  meta.economyObservedSnapshot = economy.observedSnapshot ?? null;
  meta.bahiaEconomicProducts = economy.bahia?.products?.length ?? 0;
  meta.salvadorEconomicProducts = economy.salvador?.products?.length ?? 0;
  meta.searchItems = fs.existsSync(searchPath) ? (readJson(searchPath).rows?.length ?? meta.searchItems) : meta.searchItems;
  writeJson(metaPath, meta);
}

console.log(`economia: ${economy.available ? `snapshot validado ${economy.snapshot}` : "sem snapshot publicável; falso zero bloqueado"}; cobertura integrada gerada`);
