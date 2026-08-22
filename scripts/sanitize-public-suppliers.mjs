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

function isBusinessCnpj(value) {
  return digits(value).length === 14;
}

function sanitizeContract(contract) {
  if (!contract || typeof contract !== "object") return contract;
  if (isBusinessCnpj(contract.documentoFornecedor)) {
    return { ...contract, documentoFornecedor: digits(contract.documentoFornecedor) };
  }
  return {
    ...contract,
    fornecedor: null,
    documentoFornecedor: null,
    tipoFornecedor: null,
    supplierPrivacy: "non_business_or_unstructured_supplier_omitted",
  };
}

function sanitizeLink(link) {
  return {
    ...link,
    contratos: (link.contratos ?? []).map(sanitizeContract),
  };
}

const contracts = read("contracts.json", { rows: [] });
contracts.rows = (contracts.rows ?? []).map(sanitizeContract);
if (contracts.complementary?.rows) {
  contracts.complementary.rows = contracts.complementary.rows.map(sanitizeContract);
}
contracts.supplierPrivacyRule = "A camada pública de fornecedores publica somente fornecedor empresarial com CNPJ estruturado de 14 dígitos. CPF, nomes de pessoa física e fornecedor sem CNPJ empresarial verificável permanecem omitidos da camada pública.";
write("contracts.json", contracts);

const suppliers = read("suppliers.json", { rows: [] });
suppliers.rows = (suppliers.rows ?? [])
  .filter((supplier) => isBusinessCnpj(supplier.documento))
  .map((supplier) => ({
    ...supplier,
    id: digits(supplier.documento),
    documento: digits(supplier.documento),
    contratos: (supplier.contratos ?? []).map(sanitizeContract),
  }));
suppliers.totalContractValue = suppliers.rows.reduce((sum, supplier) => sum + Number(supplier.valorGlobal ?? 0), 0);
suppliers.coverageNote = "Diretório público restrito a fornecedores empresariais com CNPJ estruturado. Pessoas físicas e fornecedores sem CNPJ empresarial verificável não são republicados aqui.";
write("suppliers.json", suppliers);

const processes = read("processes.json", { rows: [] });
processes.rows = (processes.rows ?? []).map((process) => ({
  ...process,
  contratosExatos: (process.contratosExatos ?? []).map(sanitizeContract),
}));
write("processes.json", processes);

const analysis = read("analysis.json");
analysis.repeatSuppliers = (analysis.repeatSuppliers ?? []).filter((supplier) => isBusinessCnpj(supplier.documento)).map((supplier) => ({ ...supplier, documento: digits(supplier.documento), contratos: (supplier.contratos ?? []).map(sanitizeContract) }));
analysis.concentratedSuppliers = (analysis.concentratedSuppliers ?? []).filter((supplier) => isBusinessCnpj(supplier.documento)).map((supplier) => ({ ...supplier, documento: digits(supplier.documento), contratos: (supplier.contratos ?? []).map(sanitizeContract) }));
analysis.exactCrossSourceLinks = (analysis.exactCrossSourceLinks ?? []).map(sanitizeLink);
write("analysis.json", analysis);

const money = read("money.json");
money.suppliers = (money.suppliers ?? []).filter((supplier) => isBusinessCnpj(supplier.documento)).map((supplier) => ({ ...supplier, documento: digits(supplier.documento), contratos: (supplier.contratos ?? []).map(sanitizeContract) }));
money.exactCrossSourceLinks = (money.exactCrossSourceLinks ?? []).map(sanitizeLink);
money.supplierPrivacyRule = contracts.supplierPrivacyRule;
write("money.json", money);

const search = read("search.json", { rows: [] });
const retained = (search.rows ?? []).filter((item) => !["Fornecedores", "Contratos"].includes(item.grupo));
const supplierSearch = suppliers.rows.map((supplier) => ({
  tipo: "Fornecedor empresarial",
  grupo: "Fornecedores",
  titulo: supplier.nome || "Fornecedor empresarial",
  detalhe: `CNPJ ${supplier.documento}`,
  referencia: `${supplier.quantidadeContratos ?? 0} contrato(s) no recorte complementar`,
  href: `/fornecedores/${encodeURIComponent(supplier.documento)}`,
  termos: [supplier.nome, supplier.documento].filter(Boolean).join(" ").toLowerCase(),
}));
const contractSearch = (contracts.rows ?? []).map((contract) => ({
  tipo: "Contrato",
  grupo: "Contratos",
  titulo: contract.numero ? `Contrato ${contract.numero}` : "Contrato",
  detalhe: [contract.fornecedor, contract.unidade || contract.orgao].filter(Boolean).join(" · "),
  referencia: contract.processo ? `Processo ${contract.processo}` : (contract.objeto || ""),
  href: `/contratos/${encodeURIComponent(contract.id)}`,
  termos: [contract.numero, contract.numeroSigef, contract.processo, contract.fornecedor, contract.documentoFornecedor, contract.unidade, contract.orgao, contract.objeto].filter(Boolean).join(" ").toLowerCase(),
}));
search.rows = [...retained, ...supplierSearch, ...contractSearch];
write("search.json", search);

const dashboard = read("dashboard.json");
dashboard.suppliers ??= {};
dashboard.suppliers.total = suppliers.rows.length;
dashboard.supplierPrivacyRule = contracts.supplierPrivacyRule;
write("dashboard.json", dashboard);

const meta = read("meta.json");
meta.suppliers = suppliers.rows.length;
meta.searchItems = search.rows.length;
meta.supplierPrivacyModel = "business_cnpj_only";
write("meta.json", meta);

console.log(`Fornecedores públicos sanitizados: ${suppliers.rows.length} empresas com CNPJ; pessoas físicas/sem CNPJ omitidas.`);
