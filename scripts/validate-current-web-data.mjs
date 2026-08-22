import fs from "node:fs";
import path from "node:path";

const root = process.cwd();
const publicRoot = path.join(root, "public", "data");

function read(name) {
  const file = path.join(publicRoot, name);
  if (!fs.existsSync(file) || fs.statSync(file).size === 0) throw new Error(`arquivo público ausente: ${name}`);
  return JSON.parse(fs.readFileSync(file, "utf8"));
}
function digits(value) {
  return String(value ?? "").replace(/\D/g, "");
}

const meta = read("meta.json");
const contracts = read("contracts.json");
const acquisitions = read("acquisitions.json");
const municipalLinks = read("municipal-links.json");
const camara = read("camara.json");
const suppliers = read("suppliers.json");
const transparency = read("transparency.json");

if (contracts.sourceSystem !== "SALVADOR_TRANSPARENCIA_API_CONTRATOS" || contracts.completeForFilter !== true) {
  throw new Error("grade municipal de contratos completa não foi promovida");
}
if (!(Number(contracts.sourceRows) >= Number(contracts.rows?.length || 0)) || !(contracts.rows?.length > 0)) {
  throw new Error("contagens da grade municipal de contratos inválidas");
}
for (const row of contracts.rows ?? []) {
  const hasSupplier = Boolean(row.fornecedor || row.documentoFornecedor);
  if (!hasSupplier) continue;
  if (digits(row.documentoFornecedor).length !== 14 || !row.fornecedor || !row.supplierEvidence?.method) {
    throw new Error(`contrato municipal ${row.id} publicou fornecedor sem CNPJ empresarial e evidência documental`);
  }
  if (!String(row.supplierEvidence?.method).startsWith("exact_")) {
    throw new Error(`contrato municipal ${row.id} usa método de fornecedor não exato`);
  }
}
if ((suppliers.rows ?? []).some((supplier) => digits(supplier.documento).length !== 14)) {
  throw new Error("diretório público contém fornecedor sem CNPJ empresarial estruturado");
}
if (meta.supplierPrivacyModel !== "business_cnpj_only") {
  throw new Error("modelo de privacidade de fornecedores ausente");
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

const auxiliary = camara.auxiliary;
if (!auxiliary) throw new Error("fontes auxiliares atuais da Câmara ausentes");
if (auxiliary.travel?.complete !== true || !(auxiliary.travel?.records > 0) || !(auxiliary.travel?.pages > 0)) {
  throw new Error("cobertura de viagens da Câmara inconsistente");
}
if (auxiliary.documents?.complete !== true || !(auxiliary.documents?.records > 0)) {
  throw new Error("catálogo documental da Câmara inconsistente");
}
if (auxiliary.certames?.complete !== false || auxiliary.certames?.status !== "partial") {
  throw new Error("certames da Câmara não permanecem explicitamente parciais");
}
if (!String(auxiliary.travel?.publicDetailRule || "").includes("não são republicados")) {
  throw new Error("regra pública de privacidade das viagens ausente");
}

const byId = new Map((transparency.datasets ?? []).map((row) => [row.id, row]));
for (const id of ["salvador_aquisicoes", "salvador_financas", "salvador_contratos", "salvador_relacoes", "cms", "cms_viagens", "cms_documentos", "cms_certames"]) {
  if (!byId.has(id)) throw new Error(`cobertura pública sem dataset ${id}`);
}
if (byId.get("salvador_contratos")?.status !== "complete_for_filter") throw new Error("cobertura pública ainda chama contratos municipais de parciais");
if (byId.get("cms")?.status !== "complete_for_filter") throw new Error("cobertura pública ainda chama o ledger atual da Câmara de parcial");
if (byId.get("cms_viagens")?.status !== "complete_for_filter") throw new Error("cobertura pública de viagens diverge da coleta completa");
if (byId.get("cms_documentos")?.status !== "complete_for_filter") throw new Error("cobertura pública de documentos diverge da coleta completa");
if (byId.get("cms_certames")?.status !== "partial") throw new Error("cobertura pública de certames não está parcial");

console.log(JSON.stringify({
  ok: true,
  contracts: { sourceRows: contracts.sourceRows, publishedRows: contracts.rows.length, structuredSupplierLinks: contracts.structuredSupplierLinks ?? 0, asOf: contracts.periodEnd },
  acquisitions: { records: acquisitions.rows.length, asOf: acquisitions.summary?.period_end },
  suppliers: { businessCnpjOnly: true, records: suppliers.rows?.length ?? 0 },
  links: linkSummary,
  cms: { records: ledger.records, pages: ledger.pagesWithRecords, asOf: ledger.asOf },
  cmsAuxiliary: {
    asOf: auxiliary.asOf,
    travelRecords: auxiliary.travel?.records,
    documents: auxiliary.documents?.records,
    visibleCertames: auxiliary.certames?.recordsVisible,
  },
  latestSourceAsOf: transparency.latestSourceAsOf ?? meta.latestSourceAsOf ?? null,
}, null, 2));
