import fs from "node:fs";
import path from "node:path";

const root = process.cwd();
const publicRoot = path.join(root, "public", "data");
const snapshotsRoot = path.join(root, "cities", "salvador", "data", "snapshots");

function readJson(name, fallback = {}) {
  const file = path.join(publicRoot, name);
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

function normalizeReference(value) {
  return String(value ?? "")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toUpperCase()
    .replace(/[^A-Z0-9]+/g, "")
    .trim();
}

function latestPncpProcurementFile() {
  if (!fs.existsSync(snapshotsRoot)) return null;
  const dates = fs.readdirSync(snapshotsRoot, { withFileTypes: true })
    .filter((entry) => entry.isDirectory() && /^\d{4}-\d{2}-\d{2}$/.test(entry.name))
    .map((entry) => entry.name)
    .sort()
    .reverse();
  for (const date of dates) {
    const dir = path.join(snapshotsRoot, date, "pncp_complementary", "procurements");
    if (!fs.existsSync(dir)) continue;
    const files = fs.readdirSync(dir)
      .filter((name) => /^contratacoes_municipal_.*\.jsonl$/.test(name))
      .sort();
    const file = files.at(-1);
    if (file) return { date, file: path.join(dir, file) };
  }
  return null;
}

function sourceObservationKey(contract) {
  const source = contract.sourceSystem || contract._relationLayer || "fonte-desconhecida";
  const identifier = contract.id || contract.controlePncp || contract.numeroSigef || contract.numero;
  return `${source}:${String(identifier ?? "sem-identificador")}`;
}

function contractEvents(contract) {
  const label = contract.numero || contract.numeroSigef || (contract.sourceSystem === "PNCP" ? "PNCP" : "registrado");
  return [
    contract.assinadoEm ? { data: contract.assinadoEm, tipo: "Contrato", titulo: `Contrato ${label} assinado`, fonte: contract.fonte } : null,
    contract.publicadoEm ? { data: contract.publicadoEm, tipo: "Publicação", titulo: `Contrato ${label} publicado`, fonte: contract.fonte } : null,
    contract.vigenciaInicio ? { data: contract.vigenciaInicio, tipo: "Vigência", titulo: `Início da vigência · ${label}`, fonte: contract.fonte } : null,
    contract.vigenciaFim ? { data: contract.vigenciaFim, tipo: "Vigência", titulo: `Fim previsto da vigência · ${label}`, fonte: contract.fonte } : null,
  ].filter(Boolean);
}

function compactContract(contract, linkMethods = contract.linkMethods ?? []) {
  return {
    id: contract.id,
    numero: contract.numero ?? null,
    numeroSigef: contract.numeroSigef ?? null,
    processo: contract.processo ?? null,
    controlePncp: contract.controlePncp ?? null,
    controleContratacao: contract.controleContratacao ?? null,
    orgao: contract.orgao ?? null,
    unidade: contract.unidade ?? null,
    valorGlobal: contract.valorGlobal ?? null,
    fornecedor: contract.fornecedor ?? null,
    documentoFornecedor: contract.documentoFornecedor ?? null,
    assinadoEm: contract.assinadoEm ?? null,
    publicadoEm: contract.publicadoEm ?? null,
    vigenciaInicio: contract.vigenciaInicio ?? null,
    vigenciaFim: contract.vigenciaFim ?? null,
    situacao: contract.situacao ?? null,
    sourceSystem: contract.sourceSystem ?? null,
    sourceLayer: contract.sourceLayer ?? contract._relationLayer ?? null,
    linkMethods: [...new Set(linkMethods)].sort(),
    fonte: contract.fonte ?? null,
  };
}

function addRelation(target, contract, method) {
  const key = sourceObservationKey(contract);
  const existing = target.get(key) ?? { contract, methods: new Set() };
  existing.methods.add(method);
  target.set(key, existing);
}

const processes = readJson("processes.json", { rows: [] });
const contracts = readJson("contracts.json", { rows: [], complementary: { rows: [] } });
const money = readJson("money.json");
const meta = readJson("meta.json");

const primaryContracts = (contracts.rows ?? []).map((contract) => ({
  ...contract,
  sourceSystem: contract.sourceSystem ?? contracts.sourceSystem ?? "SALVADOR_TRANSPARENCIA_API_CONTRATOS",
  _relationLayer: "municipal_primary",
}));
const complementaryContracts = (contracts.complementary?.rows ?? []).map((contract) => ({
  ...contract,
  sourceSystem: contract.sourceSystem ?? contracts.complementary?.source ?? "PNCP",
  _relationLayer: "pncp_complementary",
}));

const contractsByProcess = new Map();
for (const contract of [...primaryContracts, ...complementaryContracts]) {
  const processKey = normalizeReference(contract.processo);
  if (!processKey) continue;
  const current = contractsByProcess.get(processKey) ?? new Map();
  current.set(sourceObservationKey(contract), contract);
  contractsByProcess.set(processKey, current);
}

// Exact two-hop PNCP documentary path:
// municipal process number == PNCP procurement process_number
// PNCP procurement numeroControlePNCP == PNCP contract numeroControlePncpCompra.
// No object, supplier, value, date or textual similarity participates in this relation.
const pncpProcurementSource = latestPncpProcurementFile();
const pncpProcurements = readJsonl(pncpProcurementSource?.file);
const procurementControlsByProcess = new Map();
for (const procurement of pncpProcurements) {
  const processKey = normalizeReference(procurement.process_number);
  const controlKey = normalizeReference(procurement.pncp_control_number);
  if (!processKey || !controlKey) continue;
  const controls = procurementControlsByProcess.get(processKey) ?? new Set();
  controls.add(controlKey);
  procurementControlsByProcess.set(processKey, controls);
}

const pncpContractsByProcurementControl = new Map();
for (const contract of complementaryContracts) {
  const controlKey = normalizeReference(contract.controleContratacao);
  if (!controlKey) continue;
  const current = pncpContractsByProcurementControl.get(controlKey) ?? new Map();
  current.set(sourceObservationKey(contract), contract);
  pncpContractsByProcurementControl.set(controlKey, current);
}

let processesWithDirectExactContracts = 0;
let directExactPairs = 0;
let processesWithPncpProcurementControlLinks = 0;
let pncpProcurementControlExactPairs = 0;
let processesNewlyLinkedByPncpProcurementControl = 0;
let pncpProcurementControlIncrementalPairs = 0;
const pncpProcurementControlIncrementalContracts = new Set();

const updatedProcesses = (processes.rows ?? []).map((process) => {
  const processKey = normalizeReference(process.processo);
  const relations = new Map();
  const direct = processKey ? [...(contractsByProcess.get(processKey)?.values() ?? [])] : [];
  if (direct.length) processesWithDirectExactContracts += 1;
  directExactPairs += direct.length;
  for (const contract of direct) addRelation(relations, contract, "exact_process_number");

  let twoHopPairsForProcess = 0;
  const controls = processKey ? procurementControlsByProcess.get(processKey) ?? new Set() : new Set();
  for (const controlKey of controls) {
    const matches = pncpContractsByProcurementControl.get(controlKey);
    if (!matches) continue;
    for (const contract of matches.values()) {
      const key = sourceObservationKey(contract);
      const existed = relations.has(key);
      addRelation(relations, contract, "pncp_procurement_control_chain");
      twoHopPairsForProcess += 1;
      pncpProcurementControlExactPairs += 1;
      if (!existed) {
        pncpProcurementControlIncrementalPairs += 1;
        pncpProcurementControlIncrementalContracts.add(key);
      }
    }
  }
  if (twoHopPairsForProcess > 0) processesWithPncpProcurementControlLinks += 1;
  if (!direct.length && relations.size > 0) processesNewlyLinkedByPncpProcurementControl += 1;

  const exactRelations = [...relations.values()];
  const exactContracts = exactRelations.map(({ contract, methods }) => ({ ...contract, linkMethods: [...methods] }));
  const primaryExact = exactContracts.filter((contract) => contract._relationLayer === "municipal_primary");
  const pncpExact = exactContracts.filter((contract) => contract._relationLayer === "pncp_complementary");
  const timeline = [
    process.realizadoEm ? { data: process.realizadoEm, tipo: "Aquisição", titulo: "Data da aquisição", fonte: process.fonte } : null,
    process.publicadoEm ? { data: process.publicadoEm, tipo: "Publicação", titulo: "Publicação municipal", fonte: process.fonte } : null,
    ...exactContracts.flatMap(contractEvents),
  ].filter(Boolean).sort((a, b) => String(a.data).localeCompare(String(b.data)));
  return {
    ...process,
    contratosExatos: exactContracts.map((contract) => compactContract(contract, contract.linkMethods)),
    contratosExatosMunicipais: primaryExact.map((contract) => compactContract(contract, contract.linkMethods)),
    contratosPncpComplementaresExatos: pncpExact.map((contract) => compactContract(contract, contract.linkMethods)),
    linhaDoTempo: timeline,
  };
});

processes.rows = updatedProcesses;
writeJson("processes.json", processes);

const uniqueObservations = new Map();
const uniquePrimary = new Map();
const uniquePncp = new Map();
let exactPairs = 0;
let primaryExactPairs = 0;
let pncpExactPairs = 0;
let processesWithPrimaryExactContracts = 0;
let processesWithPncpComplementaryExactContracts = 0;
const links = [];

for (const process of updatedProcesses) {
  const exactContracts = process.contratosExatos ?? [];
  if (!exactContracts.length) continue;
  const primaryCount = exactContracts.filter((contract) => contract.sourceLayer === "municipal_primary").length;
  const pncpCount = exactContracts.filter((contract) => contract.sourceLayer === "pncp_complementary").length;
  if (primaryCount > 0) processesWithPrimaryExactContracts += 1;
  if (pncpCount > 0) processesWithPncpComplementaryExactContracts += 1;

  const compactContracts = exactContracts.map((contract) => {
    const key = sourceObservationKey(contract);
    exactPairs += 1;
    uniqueObservations.set(key, contract);
    if (contract.sourceLayer === "pncp_complementary") {
      pncpExactPairs += 1;
      uniquePncp.set(key, contract);
    } else {
      primaryExactPairs += 1;
      uniquePrimary.set(key, contract);
    }
    return compactContract(contract, contract.linkMethods);
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
    contratosMunicipais: compactContracts.filter((contract) => contract.sourceLayer === "municipal_primary"),
    contratosPncpComplementares: compactContracts.filter((contract) => contract.sourceLayer === "pncp_complementary"),
  });
}

links.sort((a, b) => Number(b.valorAquisicao ?? 0) - Number(a.valorAquisicao ?? 0));

const totalContractObservations = primaryContracts.length + complementaryContracts.length;
const summary = {
  processesTotal: updatedProcesses.length,
  processesWithExactContracts: links.length,
  processesWithDirectExactContracts,
  processesWithPrimaryExactContracts,
  processesWithPncpComplementaryExactContracts,
  processesWithPncpProcurementControlLinks,
  processesNewlyLinkedByPncpProcurementControl,
  exactPairs,
  directExactPairs,
  primaryExactPairs,
  pncpComplementaryExactPairs: pncpExactPairs,
  pncpProcurementControlExactPairs,
  pncpProcurementControlIncrementalPairs,
  pncpProcurementControlIncrementalContracts: pncpProcurementControlIncrementalContracts.size,
  pncpProcurementRows: pncpProcurements.length,
  pncpProcurementAsOf: pncpProcurementSource?.date ?? null,
  contractsPrimaryRows: primaryContracts.length,
  contractsComplementaryRows: complementaryContracts.length,
  uniqueContractsLinked: uniqueObservations.size,
  uniquePrimaryContractsLinked: uniquePrimary.size,
  uniquePncpComplementaryContractsLinked: uniquePncp.size,
  processCoverageRatio: updatedProcesses.length ? links.length / updatedProcesses.length : 0,
  contractCoverageRatio: totalContractObservations ? uniqueObservations.size / totalContractObservations : 0,
  primaryContractCoverageRatio: primaryContracts.length ? uniquePrimary.size / primaryContracts.length : 0,
  pncpComplementaryContractCoverageRatio: complementaryContracts.length ? uniquePncp.size / complementaryContracts.length : 0,
  acquisitionsAsOf: meta.acquisitionsAsOf ?? processes.asOf ?? null,
  contractsAsOf: meta.municipalContractsPeriodEnd ?? contracts.asOf ?? null,
  pncpComplementaryAsOf: contracts.complementary?.publishedRowsAsOf ?? contracts.complementary?.asOf ?? null,
};

const payload = {
  summary,
  identityRule: "O vínculo exige igualdade de identificadores oficiais após remover apenas formatação documental. O caminho direto compara o número oficial do processo; o caminho PNCP de dois saltos exige processo municipal = process_number da contratação PNCP e numeroControlePNCP da contratação = numeroControlePncpCompra do contrato. Objeto, fornecedor, órgão, valor, data e similaridade textual nunca criam relação.",
  sourceObservationRule: "Prefeitura e PNCP permanecem observações documentais separadas. Registros das duas fontes não são fundidos por semelhança e seus valores não são somados entre si; cada observação mantém sua fonte, identificador e método de vínculo.",
  accountingRule: "A relação aquisição → contrato é documental. Ela não liga automaticamente contrato a empenho, liquidação ou pagamento municipal; os totais financeiros agregados permanecem separados.",
  privacyRule: contracts.privacyRule ?? "Dados pessoais não estruturados não são usados para criar vínculos.",
  links,
};

writeJson("municipal-links.json", payload);

money.municipalDocumentaryLinks = summary;
money.municipalDocumentaryIdentityRule = payload.identityRule;
money.municipalDocumentarySourceObservationRule = payload.sourceObservationRule;
money.municipalDocumentaryAccountingRule = payload.accountingRule;
writeJson("money.json", money);

meta.municipalProcessesWithExactContracts = summary.processesWithExactContracts;
meta.municipalProcessesWithDirectExactContracts = summary.processesWithDirectExactContracts;
meta.municipalProcessesWithPrimaryExactContracts = summary.processesWithPrimaryExactContracts;
meta.municipalProcessesWithExactPncpComplementaryContracts = summary.processesWithPncpComplementaryExactContracts;
meta.municipalProcessesWithPncpProcurementControlLinks = summary.processesWithPncpProcurementControlLinks;
meta.municipalProcessesNewlyLinkedByPncpProcurementControl = summary.processesNewlyLinkedByPncpProcurementControl;
meta.municipalUniqueContractsLinked = summary.uniqueContractsLinked;
meta.municipalUniquePrimaryContractsLinked = summary.uniquePrimaryContractsLinked;
meta.pncpComplementaryUniqueContractsLinked = summary.uniquePncpComplementaryContractsLinked;
meta.municipalExactProcessContractPairs = summary.exactPairs;
meta.municipalPrimaryExactProcessContractPairs = summary.primaryExactPairs;
meta.pncpComplementaryExactProcessContractPairs = summary.pncpComplementaryExactPairs;
meta.pncpProcurementControlIncrementalPairs = summary.pncpProcurementControlIncrementalPairs;
writeJson("meta.json", meta);

console.log(`Vínculos exatos: ${summary.processesWithExactContracts} processos; ${summary.primaryExactPairs} observações municipais e ${summary.pncpComplementaryExactPairs} observações PNCP. Cadeia PNCP adicionou ${summary.processesNewlyLinkedByPncpProcurementControl} processos e ${summary.pncpProcurementControlIncrementalPairs} pares líquidos. Nenhum valor foi somado entre fontes.`);
