import fs from "node:fs";
import path from "node:path";

const root = process.cwd();
const regionRoot = path.join(root, "regions", "bahia");
const referenceRoot = path.join(regionRoot, "data", "reference");
const stateRoot = path.join(regionRoot, "data", "state_transparency");
const outputRoot = path.join(root, "public", "data");

function readJson(file, fallback = null) {
  if (!fs.existsSync(file)) return fallback;
  return JSON.parse(fs.readFileSync(file, "utf8"));
}

function writeJson(file, payload) {
  fs.mkdirSync(path.dirname(file), { recursive: true });
  fs.writeFileSync(file, JSON.stringify(payload), "utf8");
}

function stateStatusLabel(status) {
  return {
    complete_for_defined_collection: "Rotina estadual processada",
    complete_for_metadata_collection: "Catálogo estadual atualizado",
    partial_with_verified_sources: "Dados estaduais parciais verificados",
    partial: "Coleta estadual parcial",
  }[status] ?? "Fontes oficiais mapeadas";
}

const interstate = readJson(path.join(referenceRoot, "interstate_dependency_2017.json"));
const mip = readJson(path.join(referenceRoot, "mip_bahia_2012_key_sectors.json"));
const stateCatalog = readJson(path.join(referenceRoot, "state_transparency_catalog.json"), { sources: [] });

const economyPath = path.join(outputRoot, "economy.json");
const economy = readJson(economyPath, { available: false, coverage: {} });
economy.interstate = {
  available: Boolean(interstate),
  status: interstate ? "historical_baseline_normalized" : "source_mapped_not_normalized",
  baseline: interstate,
  keySectors: mip,
  warning: "Os indicadores interestaduais são estruturais e históricos. Eles não representam uma medição corrente de 2026.",
};
economy.coverage = economy.coverage ?? {};
economy.coverage.interstate_dependency = interstate
  ? {
      status: "historical_baseline_normalized",
      source: "SEI - cadeia regional de valor e Matriz de Insumo-Produto da Bahia",
      reference_years: [2017, 2012],
      note: "Linha de base histórica normalizada; não é um indicador corrente de 2026.",
    }
  : economy.coverage.interstate_dependency;
writeJson(economyPath, economy);

const stateLatest = readJson(path.join(stateRoot, "latest.json"));
let stateSnapshot = null;
if (stateLatest?.path) {
  const candidate = path.join(root, stateLatest.path);
  if (fs.existsSync(path.join(candidate, "coverage.json"))) stateSnapshot = candidate;
}

const stateCoverage = stateSnapshot ? readJson(path.join(stateSnapshot, "coverage.json"), {}) : {};
const stateCollectedCatalog = stateSnapshot ? readJson(path.join(stateSnapshot, "catalog.json"), { rows: [] }) : { rows: [] };
const tceExpenses = stateSnapshot ? readJson(path.join(stateSnapshot, "tce_expenses.json")) : null;
const tceContracts = stateSnapshot ? readJson(path.join(stateSnapshot, "tce_contracts.json")) : null;
const tceProcurements = stateSnapshot ? readJson(path.join(stateSnapshot, "tce_procurements.json")) : null;

const ckanSummary = stateCoverage.summary ?? {
  ckan_datasets_collected: 0,
  ckan_datasets_expected: 6,
  tce_datasets_processed: 0,
  tce_datasets_expected: 3,
};

const bahiaTransparency = {
  available: Boolean(stateSnapshot),
  snapshot: stateSnapshot ? path.basename(stateSnapshot) : null,
  status: stateCoverage.status ?? "sources_mapped",
  statusLabel: stateStatusLabel(stateCoverage.status),
  collectionMode: stateCoverage.collection_mode ?? null,
  coverage: stateCoverage,
  summary: ckanSummary,
  sources: stateCollectedCatalog.rows?.length ? stateCollectedCatalog.rows : stateCatalog.sources,
  tce: {
    expenses: tceExpenses,
    contracts: tceContracts,
    procurements: tceProcurements,
  },
  mappedSources: stateCatalog.sources?.length ?? 0,
  privacyNote: "Arquivos brutos grandes do TCE são processados temporariamente e não são republicados pelo projeto. Resumos não mantêm amostras de CPF/CNPJ.",
};
writeJson(path.join(outputRoot, "bahia-transparency.json"), bahiaTransparency);

const transparencyPath = path.join(outputRoot, "transparency.json");
const transparency = readJson(transparencyPath, { datasets: [] });
transparency.datasets = (transparency.datasets ?? []).filter((item) => !["bahia_state_transparency", "bahia_interestadual"].includes(item.id));
transparency.datasets.push({
  id: "bahia_state_transparency",
  title: "Transparência estadual da Bahia",
  status: stateSnapshot ? stateCoverage.status : "sources_mapped",
  statusLabel: stateSnapshot ? stateStatusLabel(stateCoverage.status) : "Fontes oficiais mapeadas",
  detail: stateSnapshot
    ? `${ckanSummary.ckan_datasets_collected ?? 0}/${ckanSummary.ckan_datasets_expected ?? 6} catálogos SEFAZ/CKAN coletados; arquivos TCE permanecem com cobertura separada.`
    : "Receitas, despesas, pagamentos, contratos, licitações, diárias e bases TCE já têm fontes oficiais catalogadas; o primeiro snapshot processado ainda não está versionado.",
  source: "SEFAZ/AGE Bahia + TCE/BA",
  href: "/bahia/transparencia",
});
transparency.datasets.push({
  id: "bahia_interestadual",
  title: "Dependência interestadual da Bahia",
  status: interstate ? "historical_baseline_normalized" : "source_mapped_not_normalized",
  statusLabel: interstate ? "Linha de base histórica normalizada" : "Fonte mapeada",
  detail: interstate
    ? "Estrutura interestadual baseada na matriz de 2017 e setores-chave da MIP Bahia 2012; anos de referência ficam visíveis na interface."
    : "A fonte SEI está mapeada, mas ainda não foi normalizada.",
  source: "SEI Bahia",
  href: "/economia/oportunidades",
});
writeJson(transparencyPath, transparency);

const metaPath = path.join(outputRoot, "meta.json");
const meta = readJson(metaPath, {});
meta.interstateBaselineAvailable = Boolean(interstate);
meta.interstateReferenceYear = interstate?.reference_year ?? null;
meta.mipReferenceYear = mip?.reference_year ?? null;
meta.stateTransparencyAvailable = Boolean(stateSnapshot);
meta.stateTransparencySnapshot = stateSnapshot ? path.basename(stateSnapshot) : null;
meta.stateTransparencyStatus = stateCoverage.status ?? null;
meta.stateCkanCollected = ckanSummary.ckan_datasets_collected ?? 0;
meta.stateCkanExpected = ckanSummary.ckan_datasets_expected ?? 6;
meta.stateTceProcessed = ckanSummary.tce_datasets_processed ?? 0;
meta.stateTransparencyMappedSources = stateCatalog.sources?.length ?? 0;
writeJson(metaPath, meta);

console.log(`Bahia regional: interestadual=${interstate ? "linha de base normalizada" : "pendente"}; transparência estadual=${stateSnapshot ? stateCoverage.status : "fontes mapeadas"}`);
