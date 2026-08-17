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

const dashboard = {
  asOf: finalStatus.as_of,
  finance: financeSummary,
  acquisitions: {
    summary: acquisitionsSummary,
    byType: acquisitionsAnalysis.by_acquisition_type ?? [],
    byAgency: (acquisitionsAnalysis.by_agency ?? []).slice(0, 12),
    top: acquisitions.slice(0, 10),
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
write("meta.json", {
  generatedFromRepository: true,
  city: "Salvador",
  uf: "BA",
  asOf: finalStatus.as_of,
  sourceStatus: finalStatus.project_status,
  acquisitions: acquisitions.length,
  creditorsPublished: expenseCreditors.length,
  officials: officials.length,
});

console.log(`web data built in ${path.relative(root, outputRoot)}: ${acquisitions.length} aquisições, ${officials.length} nomes da Câmara`);
