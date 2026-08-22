import fs from "node:fs";
import path from "node:path";

const publicRoot = path.join(process.cwd(), "public", "data");

function read(name, fallback = {}) {
  const file = path.join(publicRoot, name);
  return fs.existsSync(file) ? JSON.parse(fs.readFileSync(file, "utf8")) : fallback;
}
function write(name, payload) {
  fs.writeFileSync(path.join(publicRoot, name), JSON.stringify(payload), "utf8");
}
function cnpj(value) {
  const digits = String(value ?? "").replace(/\D/g, "");
  return digits.length === 14 ? digits : null;
}

const contracts = read("contracts.json", { rows: [], complementary: { rows: [] } });
const suppliersPayload = read("suppliers.json", { rows: [] });
const search = read("search.json", { rows: [] });
const dashboard = read("dashboard.json", {});
const meta = read("meta.json", {});

const municipalBusinessCnpjs = new Set(
  (contracts.rows ?? [])
    .filter((row) => row.supplierEvidence && cnpj(row.documentoFornecedor))
    .map((row) => cnpj(row.documentoFornecedor)),
);

const municipalSuppliers = (suppliersPayload.rows ?? []).filter((supplier) => municipalBusinessCnpjs.has(cnpj(supplier.documento)));
const pncpGroups = new Map();

for (const contract of contracts.complementary?.rows ?? []) {
  const id = cnpj(contract.documentoFornecedor);
  if (!id || !contract.fornecedor || municipalBusinessCnpjs.has(id)) continue;
  const group = pncpGroups.get(id) ?? { nome: contract.fornecedor, contracts: new Map() };
  const contractKey = contract.id || contract.controlePncp || `${contract.numero || ""}:${contract.processo || ""}`;
  group.contracts.set(contractKey, contract);
  pncpGroups.set(id, group);
}

const complementarySuppliers = [...pncpGroups.entries()].map(([id, group]) => {
  const rows = [...group.contracts.values()];
  const unitMap = new Map();
  let total = 0;
  for (const contract of rows) {
    const value = Number(contract.valorGlobal ?? 0);
    total += value;
    const unit = contract.unidade || "Unidade não informada";
    unitMap.set(unit, (unitMap.get(unit) ?? 0) + value);
  }
  return {
    id,
    documento: id,
    nome: group.nome,
    tipo: "CNPJ",
    quantidadeContratos: rows.length,
    valorGlobal: total,
    unidades: [...unitMap.entries()].map(([nome, valor]) => ({ nome, valor })).sort((a, b) => b.valor - a.valor),
    contratos: rows.slice().sort((a, b) => String(b.assinadoEm ?? b.publicadoEm ?? "").localeCompare(String(a.assinadoEm ?? a.publicadoEm ?? ""))),
    evidenceModel: "pncp_complementary_only",
  };
});

const suppliers = [...municipalSuppliers, ...complementarySuppliers].sort((a, b) => Number(b.valorGlobal ?? 0) - Number(a.valorGlobal ?? 0));
suppliersPayload.rows = suppliers;
suppliersPayload.totalContractValue = suppliers.reduce((sum, supplier) => sum + Number(supplier.valorGlobal ?? 0), 0);
suppliersPayload.dataFreshness = {
  municipalContracts: contracts.periodEnd ?? contracts.asOf ?? null,
  pncpComplementary: contracts.complementary?.asOf ?? null,
};
suppliersPayload.coverageNote = "Diretório público restrito a empresas com CNPJ estruturado. Fornecedores ligados a contrato municipal exigem evidência documental exata; empresas somente do PNCP complementar são agregadas por CNPJ sem inferência textual.";
write("suppliers.json", suppliersPayload);

const retainedSearch = (search.rows ?? []).filter((item) => item.grupo !== "Fornecedores");
const supplierSearch = suppliers.map((supplier) => ({
  tipo: "Fornecedor empresarial",
  grupo: "Fornecedores",
  titulo: supplier.nome,
  detalhe: `CNPJ ${supplier.documento}`,
  referencia: `${supplier.quantidadeContratos} contrato(s) no recorte publicado`,
  href: `/fornecedores/${encodeURIComponent(supplier.documento)}`,
  termos: [supplier.nome, supplier.documento].filter(Boolean).join(" ").toLowerCase(),
}));
search.rows = [...retainedSearch, ...supplierSearch];
write("search.json", search);

dashboard.suppliers ??= {};
dashboard.suppliers.total = suppliers.length;
write("dashboard.json", dashboard);
meta.suppliers = suppliers.length;
meta.searchItems = search.rows.length;
meta.pncpComplementaryBusinessSuppliers = complementarySuppliers.length;
write("meta.json", meta);

console.log(`Agregação PNCP complementar: ${complementarySuppliers.length} empresas; ${complementarySuppliers.reduce((sum, supplier) => sum + supplier.quantidadeContratos, 0)} contratos.`);
