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

function classifyStateTable(table) {
  const name = String(table?.member ?? "").toUpperCase();
  if (name.includes("AQUISICAO_FORNEC")) return "participantes";
  if (name.includes("AQUISICAO_ITEM_INSTRUMENTO")) return "tabela_relacionada";
  if (name.includes("AQUISICAO_ITEM")) return "itens";
  if (name.includes("AQUISICAO_LIC_REQ")) return "licitacoes";
  return table?.classification ?? "tabela_relacionada";
}

function semanticValue(table, token) {
  const entries = Object.entries(table?.value_field_sums ?? {});
  const found = entries.find(([field]) => String(field).toUpperCase().includes(token));
  return found ? { field: found[0], ...found[1] } : null;
}

function normalizeStateProcurements(payload) {
  if (!payload?.summary?.tables) return payload;
  const copy = structuredClone(payload);
  const tables = copy.summary.tables.map((table) => {
    const hasTemporalField = Boolean(table?.schema?.detected_fields?.year || table?.schema?.detected_fields?.date);
    return {
      ...table,
      classification: classifyStateTable(table),
      selected_rows: hasTemporalField ? table.selected_rows : null,
      scope_status: hasTemporalField ? "year_filtered" : "year_not_filterable",
    };
  });
  copy.summary.tables = tables;
  copy.summary.table_classes = tables.reduce((acc, table) => {
    acc[table.classification] = (acc[table.classification] ?? 0) + 1;
    return acc;
  }, {});
  const primary = tables.find((table) => table.classification === "licitacoes" && table?.schema?.detected_fields?.year);
  if (primary) {
    copy.summary.primary_licitacoes = {
      member: primary.member,
      rows_all_years: primary.rows,
      rows_selected_year: primary.selected_rows,
      years: primary.years ?? {},
      top_modalities: primary.top_modalities ?? [],
      top_statuses: primary.top_statuses ?? [],
      top_agencies: primary.top_agencies ?? [],
      estimated_value: semanticValue(primary, "ESTIMADO"),
      homologated_value: semanticValue(primary, "HOMOLOGADO"),
    };
  }
  const filterable = tables.filter((table) => table.selected_rows != null);
  const unfilterable = tables.filter((table) => table.selected_rows == null);
  copy.summary.selected_rows_across_filterable_tables = filterable.reduce((sum, table) => sum + Number(table.selected_rows || 0), 0);
  copy.summary.year_filterable_tables = filterable.length;
  copy.summary.year_unfilterable_tables = unfilterable.length;
  copy.summary.unfilterable_related_rows = unfilterable.reduce((sum, table) => sum + Number(table.rows || 0), 0);
  copy.summary.interpretation = "A quantidade anual vem somente da tabela principal com campo temporal. Tabelas auxiliares não são contadas como novas licitações.";
  return copy;
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
  ? { status: "historical_baseline_normalized", source: "SEI Bahia", reference_years: [2017, 2012], note: "Linha de base histórica; não é um indicador corrente de 2026." }
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
const stateRevenues = stateSnapshot ? readJson(path.join(stateSnapshot, "sefaz_receitas.json")) : null;
const rawStateProcurements = stateSnapshot ? readJson(path.join(stateSnapshot, "sefaz_licitacoes.json")) : null;
const stateProcurements = normalizeStateProcurements(rawStateProcurements);
const stateExpenses = stateSnapshot ? readJson(path.join(stateSnapshot, "sefaz_despesas.json")) : null;
const statePayments = stateSnapshot ? readJson(path.join(stateSnapshot, "sefaz_pagamentos.json")) : null;
const stateContracts = stateSnapshot ? readJson(path.join(stateSnapshot, "sefaz_contratos.json")) : null;
const stateMoneyFlow = stateSnapshot ? readJson(path.join(stateSnapshot, "sefaz_money_flow.json")) : null;
const tceExpenses = stateSnapshot ? readJson(path.join(stateSnapshot, "tce_expenses.json")) : null;
const tceContracts = stateSnapshot ? readJson(path.join(stateSnapshot, "tce_contracts.json")) : null;
const tceProcurements = stateSnapshot ? readJson(path.join(stateSnapshot, "tce_procurements.json")) : null;

const ckanSummary = stateCoverage.summary ?? { ckan_datasets_collected: 0, ckan_datasets_expected: 6, tce_datasets_processed: 0, tce_datasets_expected: 3 };
const sefazSummary = stateCoverage.sefaz_data_summary ?? { processed: 0, expected: 5, datasets: ["receitas", "licitacoes", "despesas", "pagamentos", "contratos"], reference_year: 2026 };
const contractPrimary = stateContracts?.summary?.primary_table;
const contractDedup = contractPrimary?.deduplication;
const contractValue = contractPrimary?.contract_value;

const bahiaTransparency = {
  available: Boolean(stateSnapshot),
  snapshot: stateSnapshot ? path.basename(stateSnapshot) : null,
  status: stateCoverage.status ?? "sources_mapped",
  statusLabel: stateStatusLabel(stateCoverage.status),
  collectionMode: stateCoverage.collection_mode ?? null,
  coverage: stateCoverage,
  summary: ckanSummary,
  sources: stateCollectedCatalog.rows?.length ? stateCollectedCatalog.rows : stateCatalog.sources,
  sefaz: {
    summary: sefazSummary,
    revenues: stateRevenues,
    procurements: stateProcurements,
    expenses: stateExpenses,
    payments: statePayments,
    contracts: stateContracts,
    moneyFlow: stateMoneyFlow,
  },
  tce: { expenses: tceExpenses, contracts: tceContracts, procurements: tceProcurements },
  mappedSources: stateCatalog.sources?.length ?? 0,
  privacyNote: "Arquivos brutos grandes são processados temporariamente. CPF não é republicado; CNPJ empresarial pode aparecer apenas em agregações de contratos.",
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
    ? `${sefazSummary.processed ?? 0}/${sefazSummary.expected ?? 5} bases prioritárias SEFAZ processadas. TCE permanece como fonte complementar com cobertura própria.`
    : "Receitas, despesas, pagamentos, contratos e licitações têm fontes estaduais catalogadas.",
  source: "SEFAZ/AGE Bahia + TCE/BA",
  href: "/bahia/transparencia",
});
transparency.datasets.push({
  id: "bahia_interestadual",
  title: "Dependência interestadual da Bahia",
  status: interstate ? "historical_baseline_normalized" : "source_mapped_not_normalized",
  statusLabel: interstate ? "Linha de base histórica normalizada" : "Fonte mapeada",
  detail: interstate ? "Matriz interestadual de 2017 e setores-chave da MIP Bahia 2012, com anos de referência visíveis." : "A fonte SEI está mapeada, mas ainda não foi normalizada.",
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
meta.stateSefazDataProcessed = sefazSummary.processed ?? 0;
meta.stateSefazDataExpected = sefazSummary.expected ?? 5;
meta.stateRevenueRows = stateRevenues?.summary?.rows ?? 0;
meta.stateRevenueRealized2026 = stateRevenues?.summary?.selected_year_totals?.realized ?? null;
meta.stateProcurements2026 = stateProcurements?.summary?.primary_licitacoes?.rows_selected_year ?? 0;
meta.stateProcurementEstimated2026 = stateProcurements?.summary?.primary_licitacoes?.estimated_value?.sum ?? null;
meta.stateProcurementHomologated2026 = stateProcurements?.summary?.primary_licitacoes?.homologated_value?.sum ?? null;
meta.stateExpenseRows2026 = stateExpenses?.summary?.primary_table?.selected_rows ?? 0;
meta.stateExpenseCommitted2026 = stateExpenses?.summary?.primary_table?.stage_totals?.committed?.sum ?? null;
meta.stateExpenseLiquidated2026 = stateExpenses?.summary?.primary_table?.stage_totals?.liquidated?.sum ?? null;
meta.stateExpensePaid2026 = stateExpenses?.summary?.primary_table?.stage_totals?.paid?.sum ?? null;
meta.statePaymentRows2026 = statePayments?.summary?.primary_table?.selected_rows ?? 0;
meta.statePayments2026 = statePayments?.summary?.selected_year_payment?.sum ?? null;
meta.statePaymentSourceField = statePayments?.summary?.selected_year_payment?.source_field ?? null;
meta.stateContractRelationRows2026 = contractPrimary?.selected_rows ?? 0;
meta.stateContractUniqueInstruments2026 = contractPrimary?.unique_instruments ?? contractDedup?.unique_instruments ?? 0;
meta.stateContractValue2026 = contractValue?.deduplicated_sum ?? null;
meta.stateContractValueField = contractValue?.field ?? null;
meta.stateContractProcessKeys2026 = contractPrimary?.unique_process_keys ?? 0;
meta.stateContractCnpjSuppliersPublished = contractPrimary?.top_suppliers_cnpj_only?.length ?? 0;
meta.stateMoneyFlowAvailable = Boolean(stateMoneyFlow?.summary);
meta.stateProcurementContractExactLinks = stateMoneyFlow?.summary?.instruments_procurement_to_contract ?? 0;
meta.stateContractPaymentExactLinks = stateMoneyFlow?.summary?.instruments_contract_to_payment ?? 0;
meta.stateEndToEndInstruments = stateMoneyFlow?.summary?.instruments_end_to_end ?? 0;
meta.stateEndToEndPaymentValue = stateMoneyFlow?.summary?.payment_value_end_to_end ?? null;
meta.stateTceProcessed = ckanSummary.tce_datasets_processed ?? 0;
meta.stateTransparencyMappedSources = stateCatalog.sources?.length ?? 0;
writeJson(metaPath, meta);

console.log(`Bahia regional: SEFAZ=${sefazSummary.processed ?? 0}/${sefazSummary.expected ?? 5}; licitações=${meta.stateProcurements2026}; instrumentos=${meta.stateContractUniqueInstruments2026}; fio=${meta.stateEndToEndInstruments}`);
