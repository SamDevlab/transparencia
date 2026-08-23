import fs from "node:fs";
import path from "node:path";

const root = process.cwd();
const snapshotsRoot = path.join(root, "cities", "salvador", "data", "snapshots");
const publicRoot = path.join(root, "public", "data");

function readJson(file, fallback = null) {
  if (!fs.existsSync(file)) return fallback;
  return JSON.parse(fs.readFileSync(file, "utf8"));
}
function readJsonl(file) {
  if (!file || !fs.existsSync(file)) return [];
  return fs.readFileSync(file, "utf8").split(/\r?\n/).filter(Boolean).map((line) => JSON.parse(line));
}
function writeJson(name, payload) {
  fs.writeFileSync(path.join(publicRoot, name), JSON.stringify(payload), "utf8");
}
function latestPncp() {
  if (!fs.existsSync(snapshotsRoot)) return null;
  const dates = fs.readdirSync(snapshotsRoot, { withFileTypes: true })
    .filter((entry) => entry.isDirectory() && /^\d{4}-\d{2}-\d{2}$/.test(entry.name))
    .map((entry) => entry.name).sort().reverse();
  for (const date of dates) {
    const dir = path.join(snapshotsRoot, date, "pncp_complementary");
    const summary = readJson(path.join(dir, "summary.json"));
    if (!summary) continue;
    const contractDir = path.join(dir, "contracts");
    const jsonl = fs.existsSync(contractDir)
      ? fs.readdirSync(contractDir).filter((name) => /^contratos_.*\.jsonl$/.test(name)).sort().at(-1)
      : null;
    return { date, dir, summary, contractJsonl: jsonl ? path.join(contractDir, jsonl) : null };
  }
  return null;
}

const current = latestPncp();
if (!current) {
  console.log("PNCP complementar: nenhum snapshot escopado atual; mantendo complemento existente.");
  process.exit(0);
}

const contracts = readJson(path.join(publicRoot, "contracts.json"), { rows: [], complementary: { rows: [] } });
const sourceRows = current.contractJsonl ? readJsonl(current.contractJsonl) : [];
const mapped = sourceRows.map((row, index) => ({
  id: row.pncp_control_number || `pncp:${row.contract_number || index}`,
  numero: row.contract_number ?? null,
  processo: row.process_number ?? null,
  controlePncp: row.pncp_control_number ?? null,
  controleContratacao: row.procurement_control_number ?? null,
  objeto: row.object ?? null,
  valorInicial: row.initial_value ?? null,
  valorGlobal: row.global_value ?? null,
  valorAcumulado: row.accumulated_value ?? null,
  parcelas: row.installments ?? null,
  valorParcela: row.installment_value ?? null,
  fornecedor: row.supplier_name ?? null,
  documentoFornecedor: row.supplier_document ?? null,
  tipoFornecedor: row.supplier_type ?? null,
  unidade: row.unit_name ?? null,
  codigoUnidade: row.unit_code ?? null,
  assinadoEm: row.signed_at ?? null,
  publicadoEm: row.published_at ?? null,
  vigenciaInicio: row.valid_from ?? null,
  vigenciaFim: row.valid_to ?? null,
  atualizadoEm: row.updated_at ?? null,
  fonte: row.source_url ?? null,
  sourceSystem: "PNCP",
}));

const suppliedCnpjs = Array.isArray(current.summary.agency_cnpjs_supplied)
  ? current.summary.agency_cnpjs_supplied
  : [];
const legacyDiscovered = Number(current.summary.agency_cnpjs_discovered ?? 0);
const agencyCnpjCount = suppliedCnpjs.length || legacyDiscovered;
const discoveryComplete = current.summary.agency_cnpj_discovery_complete === true;
const currentComplete = current.summary.contracts?.complete_for_supplied_agencies_and_filter === true;
const discoveredScopeComplete = discoveryComplete
  && current.summary.contracts?.complete_for_discovered_municipal_agencies_and_filter === true
  && current.summary.reconciliation?.procurement_and_contract_scope_match === true;
const currentStatus = discoveredScopeComplete
  ? "complete_for_discovered_municipal_agencies_and_filter"
  : currentComplete
    ? "complete_for_supplied_agencies_and_filter"
    : "partial";
const previousComplementary = contracts.complementary ?? {};
const previousRows = previousComplementary.rows ?? [];
const previousPublishedAsOf = previousComplementary.publishedRowsAsOf ?? previousComplementary.asOf ?? null;

// A partial observation is valuable evidence, but it must not silently replace a
// previously published contract set. Promote new rows only when every supplied
// CNPJ/date query reached a normal source end. A stronger status is exposed only
// when discovery itself is complete and the procurement/contract CNPJ scopes were
// reconciled exactly, with no fuzzy identity matching.
const promoteCurrentRows = currentComplete && mapped.length > 0;
const publishedRows = promoteCurrentRows ? mapped : previousRows;
const publishedRowsAsOf = promoteCurrentRows ? current.date : previousPublishedAsOf;

contracts.complementary = {
  source: "PNCP",
  asOf: current.date,
  status: currentStatus,
  collectionMode: current.summary.collection_mode ?? "legacy_discovery",
  agencyCnpjs: suppliedCnpjs,
  agencyCnpjCount,
  agencyCnpjDiscoveryComplete: discoveryComplete,
  procurementAndContractScopeMatch: current.summary.reconciliation?.procurement_and_contract_scope_match === true,
  coverageNote: current.summary.coverage_rule ?? null,
  errors: current.summary.errors ?? [],
  rows: publishedRows,
  publishedRowsAsOf,
  currentSnapshotRows: mapped.length,
  currentSnapshotPromoted: promoteCurrentRows,
  retainedPreviousRows: promoteCurrentRows ? 0 : previousRows.length,
};
writeJson("contracts.json", contracts);

const meta = readJson(path.join(publicRoot, "meta.json"), {});
meta.pncpComplementaryAsOf = current.date;
meta.pncpComplementaryStatus = contracts.complementary.status;
meta.pncpComplementaryCollectionMode = contracts.complementary.collectionMode;
meta.pncpComplementaryCurrentRows = mapped.length;
meta.pncpComplementaryPublishedRows = publishedRows.length;
meta.pncpComplementaryPublishedRowsAsOf = publishedRowsAsOf;
meta.pncpComplementaryCurrentSnapshotPromoted = promoteCurrentRows;
meta.pncpComplementaryAgencyCnpjs = agencyCnpjCount;
meta.pncpComplementaryAgencyDiscoveryComplete = discoveryComplete;
meta.pncpComplementaryProcurementAndContractScopeMatch = contracts.complementary.procurementAndContractScopeMatch;
meta.dataFreshness ??= {};
meta.dataFreshness.pncpComplementary = {
  asOf: current.date,
  status: contracts.complementary.status,
  collectionMode: contracts.complementary.collectionMode,
  agencyCnpjCount,
  agencyCnpjDiscoveryComplete: discoveryComplete,
  procurementAndContractScopeMatch: contracts.complementary.procurementAndContractScopeMatch,
  currentSnapshotRows: mapped.length,
  currentSnapshotPromoted: promoteCurrentRows,
  publishedRows: publishedRows.length,
  publishedRowsAsOf,
};
const candidateDates = [meta.latestSourceAsOf, current.date].filter((value) => /^\d{4}-\d{2}-\d{2}$/.test(String(value || ""))).sort();
meta.latestSourceAsOf = candidateDates.at(-1) ?? meta.latestSourceAsOf ?? null;
writeJson("meta.json", meta);

console.log(`PNCP complementar ${current.date}: observados=${mapped.length}; publicados=${publishedRows.length}; promovido=${promoteCurrentRows}; status=${contracts.complementary.status}; CNPJs fornecidos=${agencyCnpjCount}; descoberta completa=${discoveryComplete}; escopo reconciliado=${contracts.complementary.procurementAndContractScopeMatch}; fonte mais recente=${meta.latestSourceAsOf}.`);
