import fs from "node:fs";
import path from "node:path";

const root = process.cwd();
const snapshotsRoot = path.join(root, "cities", "salvador", "data", "snapshots");
const publicFile = path.join(root, "public", "data", "contracts.json");

function readJson(file, fallback = null) {
  if (!fs.existsSync(file)) return fallback;
  return JSON.parse(fs.readFileSync(file, "utf8"));
}

function readJsonl(file) {
  if (!file || !fs.existsSync(file)) return [];
  return fs.readFileSync(file, "utf8")
    .split(/\r?\n/)
    .filter(Boolean)
    .map((line) => JSON.parse(line));
}

function parseBrl(value) {
  if (typeof value === "number") return value;
  const text = String(value ?? "").trim();
  if (!text) return null;
  const parsed = Number(text.replace(/\./g, "").replace(",", "."));
  return Number.isFinite(parsed) ? parsed : null;
}

function isoDate(value) {
  const text = String(value ?? "").trim();
  if (!text) return null;
  const match = /^(\d{2})\/(\d{2})\/(\d{4})$/.exec(text);
  return match ? `${match[3]}-${match[2]}-${match[1]}` : text;
}

function firstJsonl(directory) {
  if (!fs.existsSync(directory)) return null;
  const name = fs.readdirSync(directory)
    .filter((entry) => /^municipal_contract_grid_.*\.jsonl$/.test(entry))
    .sort()
    .at(-1);
  return name ? path.join(directory, name) : null;
}

function latestCompleteMunicipalContracts() {
  if (!fs.existsSync(snapshotsRoot)) return null;
  const dates = fs.readdirSync(snapshotsRoot, { withFileTypes: true })
    .filter((entry) => entry.isDirectory() && /^\d{4}-\d{2}-\d{2}$/.test(entry.name))
    .map((entry) => entry.name)
    .sort()
    .reverse();

  for (const date of dates) {
    const snapshot = path.join(snapshotsRoot, date);
    for (const relative of ["prefeitura_contracts", path.join("production", "prefeitura_contracts")]) {
      const directory = path.join(snapshot, relative);
      const coverage = readJson(path.join(directory, "coverage.json"));
      const jsonl = firstJsonl(directory);
      if (coverage?.complete_for_filter === true && jsonl) {
        return { date, directory, coverage, jsonl };
      }
    }
  }
  return null;
}

if (!fs.existsSync(publicFile)) process.exit(0);

const municipal = latestCompleteMunicipalContracts();
if (!municipal) {
  console.log("Contratos municipais: nenhuma grade detalhada completa; mantendo PNCP como camada principal.");
  process.exit(0);
}

const existing = readJson(publicFile, { rows: [] });
const rows = readJsonl(municipal.jsonl).map((entry, index) => {
  const row = entry.source_record ?? {};
  const sigef = row.nuContratoSigef ?? null;
  const original = row.nuContratoOriginal ?? null;
  return {
    id: `salvador:${sigef || entry.source_record_key || index}`,
    numero: original || sigef,
    numeroSigef: sigef,
    processo: row.nuProcesso ?? null,
    objeto: row.dsObjeto ?? null,
    valorInicial: parseBrl(row.vlOriginal),
    valorGlobal: parseBrl(row.vlAtualizado),
    fornecedor: row.nmCredor ?? null,
    documentoFornecedor: null,
    tipoFornecedor: null,
    orgao: row.sgOrgao ?? null,
    unidade: row.dsUnidadeGestora ?? row.sgUnidadeGestora ?? null,
    codigoUnidade: row.cdUnidadeGestora ?? null,
    assinadoEm: isoDate(row.dtAssinatura),
    publicadoEm: null,
    vigenciaInicio: isoDate(row.dtInicioVigencia),
    vigenciaFim: isoDate(row.dtTerminoVigenciaAtualizado),
    situacao: row.dsSituacao ?? null,
    percentualExecutado: row.percentualExecutado ?? null,
    fonte: "https://transparencia.salvador.ba.gov.br/",
    sourceSystem: "SALVADOR_TRANSPARENCIA_API_CONTRATOS",
  };
});

rows.sort((a, b) => Number(b.valorGlobal ?? 0) - Number(a.valorGlobal ?? 0));

const output = {
  asOf: municipal.coverage.period_end || municipal.date,
  source: "Prefeitura de Salvador",
  sourceSystem: "SALVADOR_TRANSPARENCIA_API_CONTRATOS",
  completeForFilter: true,
  periodStart: municipal.coverage.period_start,
  periodEnd: municipal.coverage.period_end,
  coverageNote: municipal.coverage.coverage_note,
  rows,
  complementary: {
    source: existing.source || "PNCP",
    asOf: existing.asOf ?? null,
    coverageNote: existing.coverageNote ?? null,
    rows: existing.rows ?? [],
  },
};

fs.writeFileSync(publicFile, JSON.stringify(output), "utf8");
console.log(`Contratos municipais publicados: ${rows.length} registros (${output.periodStart} → ${output.periodEnd}).`);
