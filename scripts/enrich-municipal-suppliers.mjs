import fs from "node:fs";
import path from "node:path";

const root = process.cwd();
const publicRoot = path.join(root, "public", "data");

function read(name, fallback = {}) {
  const file = path.join(publicRoot, name);
  if (!fs.existsSync(file)) return fallback;
  return JSON.parse(fs.readFileSync(file, "utf8"));
}
function write(name, payload) {
  fs.writeFileSync(path.join(publicRoot, name), JSON.stringify(payload), "utf8");
}
function digits(value) {
  return String(value ?? "").replace(/\D/g, "");
}
function businessCnpj(value) {
  const valueDigits = digits(value);
  return valueDigits.length === 14 ? valueDigits : null;
}
function ref(value) {
  return String(value ?? "")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toUpperCase()
    .replace(/[^A-Z0-9]+/g, "")
    .trim();
}
function contractNumbers(row) {
  return new Set([row.numero, row.numeroSigef, row.contract_number]
    .map(ref)
    .filter(Boolean));
}
function hasNumberIntersection(a, b) {
  const left = contractNumbers(a);
  const right = contractNumbers(b);
  for (const value of left) if (right.has(value)) return true;
  return false;
}

const contractsPayload = read("contracts.json", { rows: [], complementary: { rows: [] } });
const processesPayload = read("processes.json", { rows: [] });
const searchPayload = read("search.json", { rows: [] });
const moneyPayload = read("money.json", {});
const analysisPayload = read("analysis.json", {});
const dashboardPayload = read("dashboard.json", {});
const meta = read("meta.json", {});

const municipalRows = contractsPayload.sourceSystem === "SALVADOR_TRANSPARENCIA_API_CONTRATOS"
  ? (contractsPayload.rows ?? [])
  : [];
const pncpRows = (contractsPayload.complementary?.rows ?? [])
  .filter((row) => businessCnpj(row.documentoFornecedor));

const municipalByProcess = new Map();
for (const row of municipalRows) {
  const key = ref(row.processo);
  if (!key) continue;
  const list = municipalByProcess.get(key) ?? [];
  list.push(row);
  municipalByProcess.set(key, list);
}
const pncpByProcess = new Map();
for (const row of pncpRows) {
  const key = ref(row.processo);
  if (!key) continue;
  const list = pncpByProcess.get(key) ?? [];
  list.push(row);
  pncpByProcess.set(key, list);
}

let exactProcessAndContract = 0;
let exactUniqueProcess = 0;
const enrichedById = new Map();

for (const row of municipalRows) {
  const processKey = ref(row.processo);
  if (!processKey) continue;
  const candidates = pncpByProcess.get(processKey) ?? [];
  if (!candidates.length) continue;

  const numberMatches = candidates.filter((candidate) => hasNumberIntersection(row, candidate));
  let candidate = null;
  let method = null;
  if (numberMatches.length === 1) {
    candidate = numberMatches[0];
    method = "exact_process_and_contract_number";
    exactProcessAndContract += 1;
  } else if (numberMatches.length === 0 && candidates.length === 1 && (municipalByProcess.get(processKey) ?? []).length === 1) {
    candidate = candidates[0];
    method = "exact_process_unique_one_to_one";
    exactUniqueProcess += 1;
  }
  if (!candidate) continue;

  const cnpj = businessCnpj(candidate.documentoFornecedor);
  if (!cnpj || !candidate.fornecedor) continue;
  enrichedById.set(row.id, {
    fornecedor: candidate.fornecedor,
    documentoFornecedor: cnpj,
    tipoFornecedor: "CNPJ",
    supplierEvidence: {
      source: "PNCP",
      method,
      processNumber: row.processo ?? candidate.processo ?? null,
      municipalContractNumber: row.numero ?? row.numeroSigef ?? null,
      pncpContractNumber: candidate.numero ?? null,
      pncpControlNumber: candidate.controlePncp ?? null,
      sourceUrl: candidate.fonte ?? null,
      rule: "Fornecedor empresarial publicado somente quando o PNCP fornece CNPJ estruturado e o contrato municipal é reconciliado por identificadores documentais exatos. Similaridade textual nunca cria o vínculo.",
    },
  });
}

contractsPayload.rows = municipalRows.map((row) => enrichedById.has(row.id) ? { ...row, ...enrichedById.get(row.id), credorOmitidoPorPrivacidade: false } : row);
contractsPayload.structuredSupplierLinks = enrichedById.size;
contractsPayload.supplierEnrichmentRule = "CNPJ empresarial do PNCP só é anexado ao contrato municipal por processo oficial exato e, quando disponível, número de contrato exato; alternativa permitida apenas quando o mesmo processo possui exatamente um contrato em cada fonte.";
write("contracts.json", contractsPayload);

const contractById = new Map(contractsPayload.rows.map((row) => [row.id, row]));
processesPayload.rows = (processesPayload.rows ?? []).map((process) => ({
  ...process,
  contratosExatos: (process.contratosExatos ?? []).map((contract) => contractById.get(contract.id) ?? contract),
}));
write("processes.json", processesPayload);

function sanitizeLinkContracts(links) {
  return (links ?? []).map((link) => ({
    ...link,
    contratos: (link.contratos ?? []).map((contract) => contractById.get(contract.id) ?? contract),
  }));
}
moneyPayload.exactCrossSourceLinks = sanitizeLinkContracts(moneyPayload.exactCrossSourceLinks);
moneyPayload.structuredMunicipalSupplierLinks = enrichedById.size;
moneyPayload.supplierEnrichmentRule = contractsPayload.supplierEnrichmentRule;
write("money.json", moneyPayload);
analysisPayload.exactCrossSourceLinks = sanitizeLinkContracts(analysisPayload.exactCrossSourceLinks);
analysisPayload.structuredMunicipalSupplierLinks = enrichedById.size;
write("analysis.json", analysisPayload);

const supplierMap = new Map();
for (const contract of contractsPayload.rows) {
  const cnpj = businessCnpj(contract.documentoFornecedor);
  if (!cnpj || !contract.fornecedor) continue;
  const supplier = supplierMap.get(cnpj) ?? {
    id: cnpj,
    documento: cnpj,
    nome: contract.fornecedor,
    tipo: "CNPJ",
    quantidadeContratos: 0,
    valorGlobal: 0,
    unidades: {},
    contratos: [],
    evidenceModel: "exact_municipal_contract_to_pncp_business_cnpj",
  };
  supplier.quantidadeContratos += 1;
  supplier.valorGlobal += Number(contract.valorGlobal ?? 0);
  const unit = contract.unidade || contract.orgao || "Unidade não informada";
  supplier.unidades[unit] = (supplier.unidades[unit] ?? 0) + Number(contract.valorGlobal ?? 0);
  supplier.contratos.push(contract);
  supplierMap.set(cnpj, supplier);
}

// Keep complementary PNCP-only business suppliers that have not been connected to a municipal contract.
for (const contract of pncpRows) {
  const cnpj = businessCnpj(contract.documentoFornecedor);
  if (!cnpj || !contract.fornecedor || supplierMap.has(cnpj)) continue;
  supplierMap.set(cnpj, {
    id: cnpj,
    documento: cnpj,
    nome: contract.fornecedor,
    tipo: "CNPJ",
    quantidadeContratos: 1,
    valorGlobal: Number(contract.valorGlobal ?? 0),
    unidades: contract.unidade ? { [contract.unidade]: Number(contract.valorGlobal ?? 0) } : {},
    contratos: [contract],
    evidenceModel: "pncp_complementary_only",
  });
}

const suppliers = [...supplierMap.values()].map((supplier) => ({
  ...supplier,
  unidades: Object.entries(supplier.unidades).map(([nome, valor]) => ({ nome, valor })).sort((a, b) => b.valor - a.valor),
  contratos: supplier.contratos.slice().sort((a, b) => String(b.assinadoEm ?? b.publicadoEm ?? "").localeCompare(String(a.assinadoEm ?? a.publicadoEm ?? ""))),
})).sort((a, b) => b.valorGlobal - a.valorGlobal);
write("suppliers.json", {
  asOf: contractsPayload.periodEnd ?? contractsPayload.asOf ?? null,
  totalContractValue: suppliers.reduce((sum, supplier) => sum + Number(supplier.valorGlobal ?? 0), 0),
  coverageNote: "Diretório público restrito a fornecedores empresariais com CNPJ estruturado. Relações com contratos municipais exigem evidência documental exata; fornecedores PNCP não ligados permanecem marcados como complementares.",
  rows: suppliers,
});

const retainedSearch = (searchPayload.rows ?? []).filter((item) => !["Fornecedores", "Contratos"].includes(item.grupo));
const supplierSearch = suppliers.map((supplier) => ({
  tipo: "Fornecedor empresarial",
  grupo: "Fornecedores",
  titulo: supplier.nome,
  detalhe: `CNPJ ${supplier.documento}`,
  referencia: `${supplier.quantidadeContratos} contrato(s) no recorte publicado`,
  href: `/fornecedores/${encodeURIComponent(supplier.documento)}`,
  termos: [supplier.nome, supplier.documento].filter(Boolean).join(" ").toLowerCase(),
}));
const contractSearch = contractsPayload.rows.map((contract) => ({
  tipo: "Contrato",
  grupo: "Contratos",
  titulo: contract.numero ? `Contrato ${contract.numero}` : "Contrato",
  detalhe: [contract.fornecedor, contract.unidade || contract.orgao].filter(Boolean).join(" · "),
  referencia: contract.processo ? `Processo ${contract.processo}` : (contract.objeto || ""),
  href: `/contratos/${encodeURIComponent(contract.id)}`,
  termos: [contract.numero, contract.numeroSigef, contract.processo, contract.fornecedor, contract.documentoFornecedor, contract.unidade, contract.orgao, contract.objeto].filter(Boolean).join(" ").toLowerCase(),
}));
searchPayload.rows = [...retainedSearch, ...supplierSearch, ...contractSearch];
write("search.json", searchPayload);

dashboardPayload.suppliers ??= {};
dashboardPayload.suppliers.total = suppliers.length;
dashboardPayload.suppliers.structuredMunicipalLinks = enrichedById.size;
write("dashboard.json", dashboardPayload);

meta.suppliers = suppliers.length;
meta.searchItems = searchPayload.rows.length;
meta.structuredMunicipalSupplierLinks = enrichedById.size;
meta.structuredSupplierExactProcessAndContract = exactProcessAndContract;
meta.structuredSupplierExactUniqueProcess = exactUniqueProcess;
write("meta.json", meta);

console.log(`Fornecedores estruturados: ${suppliers.length}; contratos municipais enriquecidos=${enrichedById.size} (processo+contrato=${exactProcessAndContract}, processo 1:1=${exactUniqueProcess}).`);
