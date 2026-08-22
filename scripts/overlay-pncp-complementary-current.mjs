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
  console.log("PNCP complementar: nenhum snapshot source-scoped atual; mantendo complemento existente.");
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

contracts.complementary = {
  source: "PNCP",
  asOf: current.date,
  status: current.summary.contracts?.complete_for_supplied_agencies_and_filter ? "complete_for_supplied_agencies_and_filter" : "partial",
  upstreamProcurementsComplete: current.summary.procurements?.complete === true,
  agencyCnpjsDiscovered: current.summary.agency_cnpjs_discovered ?? 0,
  coverageNote: current.summary.coverage_rule ?? null,
  errors: current.summary.errors ?? [],
  rows: mapped.length ? mapped : (contracts.complementary?.rows ?? []),
  currentSnapshotRows: mapped.length,
};
writeJson("contracts.json", contracts);

const meta = readJson(path.join(publicRoot, "meta.json"), {});
meta.pncpComplementaryAsOf = current.date;
meta.pncpComplementaryStatus = contracts.complementary.status;
meta.pncpComplementaryCurrentRows = mapped.length;
meta.pncpComplementaryAgencyCnpjs = contracts.complementary.agencyCnpjsDiscovered;
writeJson("meta.json", meta);

console.log(`PNCP complementar ${current.date}: ${mapped.length} contratos no snapshot atual; status=${contracts.complementary.status}; CNPJs consultados/descobertos=${contracts.complementary.agencyCnpjsDiscovered}.`);
