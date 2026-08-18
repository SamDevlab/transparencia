import fs from "node:fs";
import path from "node:path";

const root = process.cwd();
const cityRoot = path.join(root, "cities", "salvador");
const seedRoot = path.join(cityRoot, "data", "seed");
const snapshotsRoot = path.join(cityRoot, "data", "snapshots");
const finalRoot = path.join(cityRoot, "data", "final");
const outputRoot = path.join(root, "public", "data");

function readText(file) {
  return fs.readFileSync(file, "utf8");
}

function readJson(file) {
  return JSON.parse(readText(file));
}

function readJsonl(file) {
  if (!fs.existsSync(file)) return [];
  return readText(file)
    .split(/\r?\n/)
    .filter(Boolean)
    .map((line) => JSON.parse(line));
}

function parseCsv(text) {
  const rows = [];
  let row = [];
  let value = "";
  let quoted = false;

  for (let i = 0; i < text.length; i += 1) {
    const char = text[i];
    const next = text[i + 1];
    if (char === '"' && quoted && next === '"') {
      value += '"';
      i += 1;
    } else if (char === '"') {
      quoted = !quoted;
    } else if (char === "," && !quoted) {
      row.push(value);
      value = "";
    } else if ((char === "\n" || char === "\r") && !quoted) {
      if (char === "\r" && next === "\n") i += 1;
      row.push(value);
      if (row.some((cell) => cell !== "")) rows.push(row);
      row = [];
      value = "";
    } else {
      value += char;
    }
  }
  if (value || row.length) {
    row.push(value);
    rows.push(row);
  }
  if (!rows.length) return [];
  const headers = rows[0].map((header) => header.trim());
  return rows.slice(1).map((cells) =>
    Object.fromEntries(headers.map((header, index) => [header, cells[index] ?? ""])),
  );
}

function readCsv(file) {
  return parseCsv(readText(file));
}

function number(value) {
  if (value == null || value === "") return 0;
  return Number(value) || 0;
}

function normalizeKey(value) {
  return String(value ?? "")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, " ")
    .trim();
}

function normalizeReference(value) {
  return String(value ?? "")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toUpperCase()
    .replace(/\s+/g, "")
    .trim();
}

function slugify(value) {
  const slug = normalizeKey(value).replaceAll(" ", "-");
  return slug || "sem-identificador";
}

function write(name, payload) {
  const target = path.join(outputRoot, name);
  fs.writeFileSync(target, JSON.stringify(payload), "utf8");
  return target;
}

function latestValidatedSnapshot() {
  const candidates = fs.readdirSync(snapshotsRoot, { withFileTypes: true })
    .filter((entry) => entry.isDirectory() && /^\d{4}-\d{2}-\d{2}$/.test(entry.name))
    .map((entry) => entry.name)
    .filter((date) => {
      const snapshot = path.join(snapshotsRoot, date);
      return fs.existsSync(path.join(snapshot, "prefeitura_finance", "summary.json"))
        && fs.existsSync(path.join(snapshot, "prefeitura_acquisitions", "summary.json"))
        && fs.existsSync(path.join(finalRoot, date, "FINAL_STATUS.json"));
    })
    .sort();
  if (!candidates.length) throw new Error("Nenhum snapshot auditado compatível com o frontend foi encontrado.");
  return candidates.at(-1);
}

function firstJsonl(directory) {
  if (!fs.existsSync(directory)) return null;
  const file = fs.readdirSync(directory).filter((name) => name.endsWith(".jsonl")).sort().at(0);
  return file ? path.join(directory, file) : null;
}

fs.mkdirSync(outputRoot, { recursive: true });

const snapshotDate = latestValidatedSnapshot();
const snapshotRoot = path.join(snapshotsRoot, snapshotDate);
const financeRoot = path.join(snapshotRoot, "prefeitura_finance");
const acquisitionsRoot = path.join(snapshotRoot, "prefeitura_acquisitions");
const contractsRoot = path.join(snapshotRoot, "pncp_contracts");

const finalStatus = readJson(path.join(finalRoot, snapshotDate, "FINAL_STATUS.json"));
const financeSummary = readJson(path.join(financeRoot, "summary.json"));
const acquisitionsSummary = readJson(path.join(acquisitionsRoot, "summary.json"));
const acquisitionsAnalysis = readJson(path.join(acquisitionsRoot, "analysis.json"));
const fiscal = readCsv(path.join(seedRoot, "fiscal_observations.csv"));
const legislative = readCsv(path.join(seedRoot, "legislative_observations.csv"));
const officials = readCsv(path.join(seedRoot, "officials.csv"));
const executiveAgents = readCsv(path.join(seedRoot, "executive_agents.csv"));
const legislativeLeadership = readCsv(path.join(seedRoot, "legislative_leadership.csv"));
const procurementsSeed = readCsv(path.join(seedRoot, "procurements.csv"));

const acquisitions = readJsonl(path.join(acquisitionsRoot, "acquisitions.jsonl"))
  .map((row) => ({
    id: row.source_record_key,
    processo: row.process_number,
    aviso: row.notice_number,
    numero: row.acquisition_number,
    modalidade: row.modality_name,
    tipo: row.acquisition_type,
    fundamento: row.direct_purchase_basis,
    objeto: row.object,
    orgao: row.agency_name,
    siglaOrgao: row.agency_abbreviation,
    unidade: row.unit_name,
    publicadoEm: row.published_at,
    realizadoEm: row.acquisition_at,
    valor: row.acquisition_value,
    fonte: row.source_url,
  }))
  .sort((a, b) => number(b.valor) - number(a.valor));

const expenseFunctions = readJsonl(path.join(financeRoot, "expense_by_function.jsonl"))
  .sort((a, b) => number(b.paid_value) - number(a.paid_value));
const expenseCreditors = readJsonl(path.join(financeRoot, "expense_by_creditor.jsonl"))
  .sort((a, b) => number(b.paid_value) - number(a.paid_value))
  .slice(0, 750);
const contractUnits = readJsonl(path.join(financeRoot, "contract_execution_by_unit.jsonl"))
  .sort((a, b) => number(b.contracted_value) - number(a.contracted_value));
const revenue = readJsonl(path.join(financeRoot, "revenue_events.jsonl"))
  .sort((a, b) => number(b.collected_value) - number(a.collected_value))
  .slice(0, 350);

const contractJsonl = firstJsonl(contractsRoot);
const contracts = (contractJsonl ? readJsonl(contractJsonl) : []).map((row, index) => ({
  id: row.pncp_control_number || `${row.contract_number || "contrato"}-${index}`,
  numero: row.contract_number,
  processo: row.process_number,
  controlePncp: row.pncp_control_number,
  controleContratacao: row.procurement_control_number,
  objeto: row.object,
  valorInicial: row.initial_value,
  valorGlobal: row.global_value,
  valorAcumulado: row.accumulated_value,
  parcelas: row.installments,
  valorParcela: row.installment_value,
  fornecedor: row.supplier_name,
  documentoFornecedor: row.supplier_document,
  tipoFornecedor: row.supplier_type,
  unidade: row.unit_name,
  codigoUnidade: row.unit_code,
  assinadoEm: row.signed_at,
  publicadoEm: row.published_at,
  vigenciaInicio: row.valid_from,
  vigenciaFim: row.valid_to,
  atualizadoEm: row.updated_at,
  fonte: row.source_url,
}));

const leadershipByName = new Map();
for (const row of legislativeLeadership) {
  const key = normalizeKey(row.name);
  const current = leadershipByName.get(key) ?? [];
  current.push(row);
  leadershipByName.set(key, current);
}

const executive = executiveAgents.map((person) => ({
  id: slugify(person.name),
  nome: person.name,
  poder: "Executivo",
  cargo: person.role,
  orgao: person.agency,
  partido: person.party || "",
  periodo: person.mandate_or_period || "",
  funcoes: [],
  telefone: person.phone || "",
  email: person.email || "",
  fonte: person.source_url,
  fonteComplementar: person.source_url_secondary || "",
  observadoEm: person.observed_at,
  observacao: person.notes || "",
}));

const vereadores = officials.map((person) => {
  const leadership = leadershipByName.get(normalizeKey(person.name)) ?? [];
  return {
    id: slugify(person.name),
    nome: person.name,
    poder: "Legislativo",
    cargo: person.office || "Vereador(a)",
    orgao: "Câmara Municipal de Salvador",
    partido: person.party || "",
    periodo: person.legislature || "",
    funcoes: leadership.map((row) => row.leadership_role).filter(Boolean),
    telefone: leadership.find((row) => row.phone)?.phone || "",
    email: leadership.find((row) => row.email)?.email || "",
    fonte: leadership[0]?.source_url || person.source_url,
    fonteCadastro: person.source_url,
    observadoEm: person.observed_at,
    observacao: leadership.length ? `Mesa Diretora ${leadership[0].period}.` : "Cadastro oficial de vereadores observado pela CMS.",
  };
});

const publicAgents = [...executive, ...vereadores];

const contractsByProcess = new Map();
for (const contract of contracts) {
  const key = normalizeReference(contract.processo);
  if (!key) continue;
  const list = contractsByProcess.get(key) ?? [];
  list.push(contract);
  contractsByProcess.set(key, list);
}

const processes = acquisitions.map((row) => {
  const exactContracts = contractsByProcess.get(normalizeReference(row.processo)) ?? [];
  const timeline = [
    row.realizadoEm ? { data: row.realizadoEm, tipo: "Aquisição", titulo: "Data da aquisição", fonte: row.fonte } : null,
    row.publicadoEm ? { data: row.publicadoEm, tipo: "Publicação", titulo: "Publicação municipal", fonte: row.fonte } : null,
    ...exactContracts.flatMap((contract) => [
      contract.assinadoEm ? { data: contract.assinadoEm, tipo: "Contrato", titulo: `Contrato ${contract.numero || "PNCP"} assinado`, fonte: contract.fonte } : null,
      contract.publicadoEm ? { data: contract.publicadoEm, tipo: "Publicação", titulo: `Contrato ${contract.numero || "PNCP"} publicado no PNCP`, fonte: contract.fonte } : null,
      contract.vigenciaInicio ? { data: contract.vigenciaInicio, tipo: "Vigência", titulo: "Início da vigência contratual", fonte: contract.fonte } : null,
      contract.vigenciaFim ? { data: contract.vigenciaFim, tipo: "Vigência", titulo: "Fim previsto da vigência contratual", fonte: contract.fonte } : null,
    ]),
  ].filter(Boolean).sort((a, b) => String(a.data).localeCompare(String(b.data)));
  return {
    ...row,
    contratosExatos: exactContracts,
    linhaDoTempo: timeline,
  };
});

const agencyMap = new Map();
for (const row of acquisitions) {
  const name = row.orgao || "Órgão não informado";
  const key = slugify(name);
  const entry = agencyMap.get(key) ?? {
    id: key,
    nome: name,
    sigla: row.siglaOrgao || "",
    quantidade: 0,
    valorDeclarado: 0,
    contratacaoDiretaQuantidade: 0,
    contratacaoDiretaValor: 0,
    tipos: {},
    maiores: [],
  };
  entry.quantidade += 1;
  entry.valorDeclarado += number(row.valor);
  const type = row.tipo || row.modalidade || "Não informado";
  if (!entry.tipos[type]) entry.tipos[type] = { quantidade: 0, valor: 0 };
  entry.tipos[type].quantidade += 1;
  entry.tipos[type].valor += number(row.valor);
  const direct = normalizeKey(row.tipo).includes("dispensa") || normalizeKey(row.tipo).includes("inexigibilidade");
  if (direct) {
    entry.contratacaoDiretaQuantidade += 1;
    entry.contratacaoDiretaValor += number(row.valor);
  }
  entry.maiores.push({ id: row.id, processo: row.processo, numero: row.numero, objeto: row.objeto, tipo: row.tipo, valor: row.valor, publicadoEm: row.publicadoEm });
  agencyMap.set(key, entry);
}

const agencies = [...agencyMap.values()].map((entry) => ({
  ...entry,
  valorMedio: entry.quantidade ? entry.valorDeclarado / entry.quantidade : 0,
  percentualContratacaoDireta: entry.quantidade ? entry.contratacaoDiretaQuantidade / entry.quantidade : 0,
  tipos: Object.entries(entry.tipos).map(([tipo, values]) => ({ tipo, ...values })).sort((a, b) => b.valor - a.valor),
  maiores: entry.maiores.sort((a, b) => number(b.valor) - number(a.valor)).slice(0, 15),
})).sort((a, b) => b.valorDeclarado - a.valorDeclarado);

const contractTotalByUnit = new Map();
for (const contract of contracts) {
  const unit = contract.unidade || "Unidade não informada";
  contractTotalByUnit.set(unit, (contractTotalByUnit.get(unit) ?? 0) + number(contract.valorGlobal));
}

const supplierMap = new Map();
for (const contract of contracts) {
  const key = contract.documentoFornecedor || slugify(contract.fornecedor);
  const supplier = supplierMap.get(key) ?? {
    id: key,
    documento: contract.documentoFornecedor || "",
    nome: contract.fornecedor || "Fornecedor não informado",
    tipo: contract.tipoFornecedor || "",
    quantidadeContratos: 0,
    valorGlobal: 0,
    valorAcumulado: 0,
    unidades: {},
    contratos: [],
  };
  supplier.quantidadeContratos += 1;
  supplier.valorGlobal += number(contract.valorGlobal);
  supplier.valorAcumulado += number(contract.valorAcumulado);
  const unit = contract.unidade || "Unidade não informada";
  supplier.unidades[unit] = (supplier.unidades[unit] ?? 0) + number(contract.valorGlobal);
  supplier.contratos.push(contract);
  supplierMap.set(key, supplier);
}

const pncpContractsTotal = contracts.reduce((sum, contract) => sum + number(contract.valorGlobal), 0);
const suppliers = [...supplierMap.values()].map((supplier) => {
  const units = Object.entries(supplier.unidades)
    .map(([nome, valor]) => ({ nome, valor, participacaoNaUnidade: contractTotalByUnit.get(nome) ? valor / contractTotalByUnit.get(nome) : 0 }))
    .sort((a, b) => b.valor - a.valor);
  return {
    ...supplier,
    unidades: units,
    participacaoNoRecortePncp: pncpContractsTotal ? supplier.valorGlobal / pncpContractsTotal : 0,
    maiorParticipacaoEmUnidade: units[0]?.participacaoNaUnidade ?? 0,
    contratos: supplier.contratos.sort((a, b) => String(b.publicadoEm ?? "").localeCompare(String(a.publicadoEm ?? ""))),
  };
}).sort((a, b) => b.valorGlobal - a.valorGlobal);

const exactCrossSourceLinks = processes
  .filter((process) => process.contratosExatos.length > 0)
  .map((process) => ({
    processoId: process.id,
    processo: process.processo,
    objeto: process.objeto,
    orgao: process.orgao,
    valorAquisicao: process.valor,
    contratos: process.contratosExatos.map((contract) => ({
      numero: contract.numero,
      fornecedor: contract.fornecedor,
      documentoFornecedor: contract.documentoFornecedor,
      valorGlobal: contract.valorGlobal,
      fonte: contract.fonte,
    })),
    metodo: "Número de processo normalizado com correspondência exata entre as duas fontes.",
  }));

const highValueAcquisitions = acquisitions.filter((row) => number(row.valor) >= 1_000_000).slice(0, 60);
const directAcquisitions = acquisitions
  .filter((row) => normalizeKey(row.tipo).includes("dispensa") || normalizeKey(row.tipo).includes("inexigibilidade"))
  .slice(0, 60);
const repeatSuppliers = suppliers.filter((row) => row.quantidadeContratos >= 2).slice(0, 40);
const concentratedSuppliers = suppliers.filter((row) => row.maiorParticipacaoEmUnidade >= 0.5 && row.valorGlobal > 0).slice(0, 40);

const searchItems = [
  ...publicAgents.map((person) => ({
    tipo: "Agente público",
    grupo: "Pessoas",
    titulo: person.nome,
    detalhe: [person.cargo, person.orgao, person.partido].filter(Boolean).join(" · "),
    referencia: person.funcoes?.[0] || person.periodo || "",
    href: `/agentes/${person.id}`,
    termos: normalizeKey([person.nome, person.cargo, person.orgao, person.partido, ...(person.funcoes ?? [])].join(" ")),
  })),
  ...agencies.map((agency) => ({
    tipo: "Órgão",
    grupo: "Órgãos",
    titulo: agency.nome,
    detalhe: `${agency.quantidade} aquisições no recorte`,
    referencia: agency.sigla || "",
    href: `/orgaos/${agency.id}`,
    termos: normalizeKey([agency.nome, agency.sigla].join(" ")),
  })),
  ...suppliers.map((supplier) => ({
    tipo: "Fornecedor",
    grupo: "Fornecedores",
    titulo: supplier.nome,
    detalhe: supplier.documento ? `CNPJ/CPF ${supplier.documento}` : `${supplier.quantidadeContratos} contratos PNCP`,
    referencia: `${supplier.quantidadeContratos} contrato(s) no recorte complementar`,
    href: `/fornecedores/${encodeURIComponent(supplier.id)}`,
    termos: normalizeKey([supplier.nome, supplier.documento, ...supplier.unidades.map((unit) => unit.nome)].join(" ")),
  })),
  ...processes.map((row) => {
    const reference = row.processo || row.numero || row.aviso || "";
    return {
      tipo: "Processo ou aquisição",
      grupo: "Processos",
      titulo: reference ? `Referência ${reference}` : (row.objeto || "Aquisição"),
      detalhe: [row.orgao, row.tipo || row.modalidade].filter(Boolean).join(" · "),
      referencia: row.objeto || "",
      href: `/processos/${encodeURIComponent(row.id)}`,
      termos: normalizeKey([row.processo, row.numero, row.aviso, row.objeto, row.orgao, row.unidade, row.modalidade, row.tipo].join(" ")),
    };
  }),
  ...contracts.map((contract) => ({
    tipo: "Contrato",
    grupo: "Contratos",
    titulo: contract.numero ? `Contrato ${contract.numero}` : "Contrato PNCP",
    detalhe: [contract.fornecedor, contract.unidade].filter(Boolean).join(" · "),
    referencia: contract.processo ? `Processo ${contract.processo}` : contract.objeto,
    href: contract.documentoFornecedor ? `/fornecedores/${encodeURIComponent(contract.documentoFornecedor)}#contratos` : "/contratos",
    termos: normalizeKey([contract.numero, contract.processo, contract.controlePncp, contract.fornecedor, contract.documentoFornecedor, contract.unidade, contract.objeto].join(" ")),
  })),
  ...expenseCreditors.map((row) => ({
    tipo: "Credor agregado",
    grupo: "Credores",
    titulo: row.dimension_name || "Credor",
    detalhe: row.dimension_code ? `Código ${row.dimension_code}` : "Despesa agregada no período",
    referencia: "Consultar valores empenhados, liquidados e pagos",
    href: `/financas?tipo=credor&busca=${encodeURIComponent(row.dimension_name || row.dimension_code || "")}`,
    termos: normalizeKey([row.dimension_name, row.dimension_code].join(" ")),
  })),
  ...revenue.map((row) => ({
    tipo: "Receita",
    grupo: "Receitas",
    titulo: row.nature_name || "Natureza de receita",
    detalhe: row.nature_code ? `Código ${row.nature_code}` : "Natureza de receita",
    referencia: "Consultar previsão e arrecadação",
    href: `/financas?tipo=receita&busca=${encodeURIComponent(row.nature_code || row.nature_name || "")}`,
    termos: normalizeKey([row.nature_name, row.nature_code].join(" ")),
  })),
];

const dashboard = {
  asOf: finalStatus.as_of,
  snapshotDate,
  finance: financeSummary,
  acquisitions: {
    summary: acquisitionsSummary,
    byType: acquisitionsAnalysis.by_acquisition_type ?? [],
    byAgency: (acquisitionsAnalysis.by_agency ?? []).slice(0, 12),
    top: acquisitions.slice(0, 6),
  },
  agents: {
    total: publicAgents.length,
    executivo: executive.length,
    vereadores: vereadores.length,
    mesaDiretora: legislativeLeadership.length,
  },
  suppliers: {
    total: suppliers.length,
    contracts: contracts.length,
    exactLinks: exactCrossSourceLinks.length,
  },
  officialsCount: officials.length,
  legislative,
  fiscal,
  finalStatus,
};

write("dashboard.json", dashboard);
write("acquisitions.json", { asOf: finalStatus.as_of, summary: acquisitionsSummary, rows: acquisitions });
write("processes.json", { asOf: finalStatus.as_of, rows: processes });
write("contracts.json", { asOf: finalStatus.as_of, source: "PNCP", coverageNote: "Fonte complementar; não substitui a grade municipal detalhada quando ela estiver disponível.", rows: contracts });
write("suppliers.json", { asOf: finalStatus.as_of, totalContractValue: pncpContractsTotal, coverageNote: "Perfis construídos a partir dos contratos PNCP preservados no repositório. Não representam necessariamente todos os fornecedores do Município.", rows: suppliers });
write("agencies.json", { asOf: finalStatus.as_of, rows: agencies });
write("finance.json", { asOf: finalStatus.as_of, summary: financeSummary, expenseFunctions, expenseCreditors, contractUnits, revenue });
write("camara.json", { asOf: finalStatus.as_of, officials, legislative, fiscal, procurementsSeed, coverage: finalStatus.datasets?.cms_commitments ?? null });
write("agents.json", {
  asOf: finalStatus.as_of,
  summary: { total: publicAgents.length, executive: executive.length, councilors: vereadores.length, leadershipContacts: legislativeLeadership.length },
  rows: publicAgents,
});
write("analysis.json", {
  asOf: finalStatus.as_of,
  notes: "Os pontos abaixo são descritivos e servem para orientar consulta documental. Não constituem acusação ou conclusão de irregularidade.",
  highValueAcquisitions,
  directAcquisitions,
  repeatSuppliers,
  concentratedSuppliers,
  exactCrossSourceLinks,
});
write("money.json", {
  asOf: finalStatus.as_of,
  financeSummary,
  expenseFunctions: expenseFunctions.slice(0, 15),
  agencies,
  suppliers: suppliers.slice(0, 30),
  exactCrossSourceLinks,
  contractUnits,
  coverageNote: "Valores por função e unidade são agregados oficiais. Relações com contratos/fornecedores são exibidas apenas quando há identificador exato ou quando a fonte PNCP já contém explicitamente a relação.",
});
write("comparisons.json", { asOf: finalStatus.as_of, agencies });
write("search.json", { asOf: finalStatus.as_of, rows: searchItems });
write("meta.json", {
  generatedFromRepository: true,
  city: "Salvador",
  uf: "BA",
  asOf: finalStatus.as_of,
  snapshotDate,
  sourceStatus: finalStatus.project_status,
  acquisitions: acquisitions.length,
  processes: processes.length,
  contracts: contracts.length,
  suppliers: suppliers.length,
  agencies: agencies.length,
  creditorsPublished: expenseCreditors.length,
  officials: officials.length,
  executiveAgents: executive.length,
  publicAgents: publicAgents.length,
  searchItems: searchItems.length,
  exactCrossSourceLinks: exactCrossSourceLinks.length,
});

console.log(`dados do site gerados do snapshot auditado ${snapshotDate}: ${acquisitions.length} aquisições, ${contracts.length} contratos PNCP, ${suppliers.length} fornecedores, ${publicAgents.length} agentes e ${searchItems.length} itens na busca`);
