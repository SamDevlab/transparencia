import fs from "node:fs";
import path from "node:path";

const root = process.cwd();
const publicRoot = path.join(root, "public", "data");

function readJson(name, fallback = {}) {
  const file = path.join(publicRoot, name);
  if (!fs.existsSync(file)) return fallback;
  return JSON.parse(fs.readFileSync(file, "utf8"));
}

function writeJson(name, payload) {
  fs.writeFileSync(path.join(publicRoot, name), JSON.stringify(payload), "utf8");
}

const processes = readJson("processes.json", { rows: [] });
const contracts = readJson("contracts.json", { rows: [] });
const money = readJson("money.json");
const meta = readJson("meta.json");

const uniqueContracts = new Map();
let exactPairs = 0;
const links = [];

for (const process of processes.rows ?? []) {
  const exactContracts = process.contratosExatos ?? [];
  if (!exactContracts.length) continue;
  const compactContracts = exactContracts.map((contract) => {
    exactPairs += 1;
    uniqueContracts.set(contract.id, contract);
    return {
      id: contract.id,
      numero: contract.numero ?? null,
      numeroSigef: contract.numeroSigef ?? null,
      processo: contract.processo ?? null,
      orgao: contract.orgao ?? null,
      unidade: contract.unidade ?? null,
      valorGlobal: contract.valorGlobal ?? null,
      assinadoEm: contract.assinadoEm ?? null,
      vigenciaInicio: contract.vigenciaInicio ?? null,
      vigenciaFim: contract.vigenciaFim ?? null,
      situacao: contract.situacao ?? null,
      sourceSystem: contract.sourceSystem ?? contracts.sourceSystem ?? null,
      fonte: contract.fonte ?? null,
    };
  });
  links.push({
    processId: process.id,
    processo: process.processo ?? null,
    aquisicao: process.numero ?? null,
    orgao: process.orgao ?? null,
    unidade: process.unidade ?? null,
    objeto: process.objeto ?? null,
    valorAquisicao: process.valor ?? null,
    publicadoEm: process.publicadoEm ?? null,
    contratos: compactContracts,
  });
}

links.sort((a, b) => Number(b.valorAquisicao ?? 0) - Number(a.valorAquisicao ?? 0));

const summary = {
  processesTotal: (processes.rows ?? []).length,
  processesWithExactContracts: links.length,
  exactPairs,
  contractsPrimaryRows: (contracts.rows ?? []).length,
  uniqueContractsLinked: uniqueContracts.size,
  processCoverageRatio: (processes.rows ?? []).length ? links.length / processes.rows.length : 0,
  contractCoverageRatio: (contracts.rows ?? []).length ? uniqueContracts.size / contracts.rows.length : 0,
  acquisitionsAsOf: meta.acquisitionsAsOf ?? processes.asOf ?? null,
  contractsAsOf: meta.municipalContractsPeriodEnd ?? contracts.asOf ?? null,
};

const payload = {
  summary,
  identityRule: "O vínculo exige igualdade do número oficial do processo após remover apenas formatação documental. Objeto, fornecedor, órgão e similaridade textual nunca criam relação.",
  accountingRule: "A relação aquisição → contrato é documental. Ela não liga automaticamente contrato a empenho, liquidação ou pagamento municipal; os totais financeiros agregados permanecem separados.",
  privacyRule: contracts.privacyRule ?? "Dados pessoais não estruturados não são usados para criar vínculos.",
  links,
};

writeJson("municipal-links.json", payload);

money.municipalDocumentaryLinks = summary;
money.municipalDocumentaryIdentityRule = payload.identityRule;
money.municipalDocumentaryAccountingRule = payload.accountingRule;
writeJson("money.json", money);

meta.municipalProcessesWithExactContracts = summary.processesWithExactContracts;
meta.municipalUniqueContractsLinked = summary.uniqueContractsLinked;
meta.municipalExactProcessContractPairs = summary.exactPairs;
writeJson("meta.json", meta);

console.log(`Vínculos municipais: ${summary.processesWithExactContracts} processos, ${summary.uniqueContractsLinked} contratos únicos, ${summary.exactPairs} pares exatos.`);
