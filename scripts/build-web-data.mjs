import fs from "node:fs";
import path from "node:path";

const root = process.cwd();
const cityRoot = path.join(root, "cities", "salvador");
const seedRoot = path.join(cityRoot, "data", "seed");
const snapshotRoot = path.join(cityRoot, "data", "snapshots", "2026-08-17");
const outputRoot = path.join(root, "public", "data");

function readText(file) {
  return fs.readFileSync(file, "utf8");
}

function readJson(file) {
  return JSON.parse(readText(file));
}

function readJsonl(file) {
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

function write(name, payload) {
  const target = path.join(outputRoot, name);
  fs.writeFileSync(target, JSON.stringify(payload), "utf8");
  return target;
}

fs.mkdirSync(outputRoot, { recursive: true });

const financeRoot = path.join(snapshotRoot, "prefeitura_finance");
const acquisitionsRoot = path.join(snapshotRoot, "prefeitura_acquisitions");

const finalStatus = readJson(path.join(cityRoot, "data", "final", "2026-08-17", "FINAL_STATUS.json"));
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

const leadershipByName = new Map();
for (const row of legislativeLeadership) {
  const key = normalizeKey(row.name);
  const current = leadershipByName.get(key) ?? [];
  current.push(row);
  leadershipByName.set(key, current);
}

const executive = executiveAgents.map((person, index) => ({
  id: `executivo-${index}-${normalizeKey(person.name).replaceAll(" ", "-")}`,
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

const vereadores = officials.map((person, index) => {
  const leadership = leadershipByName.get(normalizeKey(person.name)) ?? [];
  return {
    id: `legislativo-${index}-${normalizeKey(person.name).replaceAll(" ", "-")}`,
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

const searchItems = [
  ...publicAgents.map((person) => ({
    tipo: "Agente público",
    titulo: person.nome,
    detalhe: [person.cargo, person.orgao, person.partido].filter(Boolean).join(" · "),
    referencia: person.funcoes?.[0] || person.periodo || "",
    href: `/agentes?busca=${encodeURIComponent(person.nome)}`,
    termos: normalizeKey([person.nome, person.cargo, person.orgao, person.partido, ...(person.funcoes ?? [])].join(" ")),
  })),
  ...acquisitions.map((row) => {
    const reference = row.processo || row.numero || row.aviso || "";
    return {
      tipo: "Licitação ou aquisição",
      titulo: reference ? `Referência ${reference}` : (row.objeto || "Aquisição"),
      detalhe: [row.orgao, row.tipo || row.modalidade].filter(Boolean).join(" · "),
      referencia: row.objeto || "",
      href: `/licitacoes?busca=${encodeURIComponent(reference || row.objeto || "")}`,
      termos: normalizeKey([row.processo, row.numero, row.aviso, row.objeto, row.orgao, row.unidade, row.modalidade, row.tipo].join(" ")),
    };
  }),
  ...expenseCreditors.map((row) => ({
    tipo: "Credor agregado",
    titulo: row.dimension_name || "Credor",
    detalhe: row.dimension_code ? `Código ${row.dimension_code}` : "Despesa agregada no período",
    referencia: "Consultar valores empenhados, liquidados e pagos",
    href: `/financas?tipo=credor&busca=${encodeURIComponent(row.dimension_name || row.dimension_code || "")}`,
    termos: normalizeKey([row.dimension_name, row.dimension_code].join(" ")),
  })),
  ...revenue.map((row) => ({
    tipo: "Receita",
    titulo: row.nature_name || "Natureza de receita",
    detalhe: row.nature_code ? `Código ${row.nature_code}` : "Natureza de receita",
    referencia: "Consultar previsão e arrecadação",
    href: `/financas?tipo=receita&busca=${encodeURIComponent(row.nature_code || row.nature_name || "")}`,
    termos: normalizeKey([row.nature_name, row.nature_code].join(" ")),
  })),
];

const dashboard = {
  asOf: finalStatus.as_of,
  finance: financeSummary,
  acquisitions: {
    summary: acquisitionsSummary,
    byType: acquisitionsAnalysis.by_acquisition_type ?? [],
    byAgency: (acquisitionsAnalysis.by_agency ?? []).slice(0, 12),
    top: acquisitions.slice(0, 10),
  },
  agents: {
    total: publicAgents.length,
    executivo: executive.length,
    vereadores: vereadores.length,
    mesaDiretora: legislativeLeadership.length,
  },
  officialsCount: officials.length,
  legislative,
  fiscal,
  finalStatus,
};

write("dashboard.json", dashboard);
write("acquisitions.json", {
  asOf: finalStatus.as_of,
  summary: acquisitionsSummary,
  rows: acquisitions,
});
write("finance.json", {
  asOf: finalStatus.as_of,
  summary: financeSummary,
  expenseFunctions,
  expenseCreditors,
  contractUnits,
  revenue,
});
write("camara.json", {
  asOf: finalStatus.as_of,
  officials,
  legislative,
  fiscal,
  procurementsSeed,
  coverage: finalStatus.datasets?.cms_commitments ?? null,
});
write("agents.json", {
  asOf: finalStatus.as_of,
  summary: {
    total: publicAgents.length,
    executive: executive.length,
    councilors: vereadores.length,
    leadershipContacts: legislativeLeadership.length,
  },
  rows: publicAgents,
});
write("search.json", {
  asOf: finalStatus.as_of,
  rows: searchItems,
});
write("meta.json", {
  generatedFromRepository: true,
  city: "Salvador",
  uf: "BA",
  asOf: finalStatus.as_of,
  sourceStatus: finalStatus.project_status,
  acquisitions: acquisitions.length,
  creditorsPublished: expenseCreditors.length,
  officials: officials.length,
  executiveAgents: executive.length,
  publicAgents: publicAgents.length,
  searchItems: searchItems.length,
});

console.log(`dados do site gerados em ${path.relative(root, outputRoot)}: ${acquisitions.length} aquisições, ${publicAgents.length} agentes públicos, ${searchItems.length} itens na busca geral`);
