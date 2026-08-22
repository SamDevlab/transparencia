import fs from "node:fs";
import path from "node:path";

const root = process.cwd();
const publicRoot = path.join(root, "public", "data");

function read(name) {
  const file = path.join(publicRoot, name);
  if (!fs.existsSync(file) || fs.statSync(file).size === 0) throw new Error(`arquivo público ausente: ${name}`);
  return JSON.parse(fs.readFileSync(file, "utf8"));
}

const meta = read("meta.json");
const contracts = read("contracts.json");
const acquisitions = read("acquisitions.json");
const municipalLinks = read("municipal-links.json");
const camara = read("camara.json");
const transparency = read("transparency.json");

if (contracts.sourceSystem !== "SALVADOR_TRANSPARENCIA_API_CONTRATOS" || contracts.completeForFilter !== true) {
  throw new Error("grade municipal de contratos completa não foi promovida");
}
if (!(Number(contracts.sourceRows) >= Number(contracts.rows?.length || 0)) || !(contracts.rows?.length > 0)) {
  throw new Error("contagens da grade municipal de contratos inválidas");
}
if (contracts.rows.some((row) => row.fornecedor || row.documentoFornecedor)) {
  throw new Error("grade municipal republicou credor/fornecedor não estruturado");
}
if (acquisitions.summary?.complete_for_filter !== true || !(acquisitions.rows?.length > 0)) {
  throw new Error("aquisições municipais atuais não estão completas para o filtro");
}
const linkSummary = municipalLinks.summary ?? {};
if (!(linkSummary.processesWithExactContracts > 0) || !(linkSummary.uniqueContractsLinked > 0) || !(linkSummary.exactPairs > 0)) {
  throw new Error("índice municipal de relações exatas vazio");
}
if (linkSummary.processesWithExactContracts !== (municipalLinks.links?.length ?? 0)) {
  throw new Error("contagem de processos vinculados diverge do índice");
}
if (!String(municipalLinks.identityRule || "").includes("número oficial do processo")) {
  throw new Error("regra de identidade municipal ausente");
}
if (!String(municipalLinks.accountingRule || "").includes("não liga automaticamente")) {
  throw new Error("limite contábil municipal ausente");
}

const ledger = camara.commitmentLedger;
if (!ledger || ledger.completeForDefaultPublicView !== true) throw new Error("ledger atual da Câmara não foi promovido como completo para a visão pública padrão");
if (!(ledger.records > 0) || !(ledger.pagesWithRecords > 0) || ledger.parserCompleteForVisibleRecords !== true || ledger.sourceExhausted !== true) {
  throw new Error("cobertura do ledger da Câmara inconsistente");
}
if (!String(ledger.accountingRule || "").includes("empenhos")) throw new Error("regra contábil do ledger da Câmara ausente");
if (!String(ledger.privacyRule || "").includes("não republica nomes de credores")) throw new Error("regra de privacidade da Câmara ausente");

const byId = new Map((transparency.datasets ?? []).map((row) => [row.id, row]));
for (const id of ["salvador_aquisicoes", "salvador_financas", "salvador_contratos", "salvador_relacoes", "cms"]) {
  if (!byId.has(id)) throw new Error(`cobertura pública sem dataset ${id}`);
}
if (byId.get("salvador_contratos")?.status !== "complete_for_filter") throw new Error("cobertura pública ainda chama contratos municipais de parciais");
if (byId.get("cms")?.status !== "complete_for_filter") throw new Error("cobertura pública ainda chama o ledger atual da Câmara de parcial");

console.log(JSON.stringify({
  ok: true,
  contracts: { sourceRows: contracts.sourceRows, publishedRows: contracts.rows.length, asOf: contracts.periodEnd },
  acquisitions: { records: acquisitions.rows.length, asOf: acquisitions.summary?.period_end },
  links: linkSummary,
  cms: { records: ledger.records, pages: ledger.pagesWithRecords, asOf: ledger.asOf },
  latestSourceAsOf: transparency.latestSourceAsOf ?? meta.latestSourceAsOf ?? null,
}, null, 2));
