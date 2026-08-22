import fs from "node:fs";
import path from "node:path";

const root = process.cwd();
const snapshotsRoot = path.join(root, "cities", "salvador", "data", "snapshots");
const publicRoot = path.join(root, "public", "data");

function readJson(file, fallback = null) {
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

function latestLedger() {
  if (!fs.existsSync(snapshotsRoot)) return null;
  const dates = fs.readdirSync(snapshotsRoot, { withFileTypes: true })
    .filter((entry) => entry.isDirectory() && /^\d{4}-\d{2}-\d{2}$/.test(entry.name))
    .map((entry) => entry.name)
    .sort()
    .reverse();
  for (const date of dates) {
    const snapshot = path.join(snapshotsRoot, date);
    for (const relative of ["cms_commitments", path.join("production", "cms_commitments")]) {
      const directory = path.join(snapshot, relative);
      const coverage = readJson(path.join(directory, "coverage.json"));
      if (!coverage || coverage.superseded === true || coverage.parser_complete_for_visible_records === false) continue;
      const commitments = path.join(directory, "commitments.jsonl");
      const fallback = path.join(directory, "commitments_visible.jsonl");
      const jsonl = fs.existsSync(commitments) ? commitments : (fs.existsSync(fallback) ? fallback : null);
      if (jsonl) return { date, directory, coverage, jsonl };
    }
  }
  return null;
}

const ledger = latestLedger();
if (!ledger) {
  console.log("Câmara: nenhum ledger atual publicável; mantendo resumo institucional existente.");
  process.exit(0);
}

const rows = readJsonl(ledger.jsonl);
const totalCommitted = rows.reduce((sum, row) => sum + Number(row.committed_value ?? 0), 0);
const parliamentaryRows = rows.filter((row) => row.is_parliamentary_compensatory_allowance === true);
const travelRows = rows.filter((row) => row.is_travel_related === true);
const verifiedOfficialMatches = rows.filter((row) => row.matched_official_name).length;
const summary = {
  asOf: ledger.date,
  source: "Câmara Municipal de Salvador",
  sourceUrl: ledger.coverage.source_url ?? "https://cmsalvador.sys.inf.br/ca/gridRegistroEmpenho/",
  status: ledger.coverage.complete === true ? "complete_for_filter" : "partial",
  completeForDefaultPublicView: ledger.coverage.complete === true,
  records: rows.length,
  pagesWithRecords: Number(ledger.coverage.pages_with_records ?? 0),
  sourceExhausted: ledger.coverage.source_exhausted === true,
  parserCompleteForVisibleRecords: ledger.coverage.parser_complete_for_visible_records !== false,
  totalCommitted,
  parliamentaryCompensatoryAllowance: {
    records: parliamentaryRows.length,
    committedValue: parliamentaryRows.reduce((sum, row) => sum + Number(row.committed_value ?? 0), 0),
  },
  travelRelated: {
    records: travelRows.length,
    committedValue: travelRows.reduce((sum, row) => sum + Number(row.committed_value ?? 0), 0),
  },
  verifiedOfficialMatches,
  coverageNote: ledger.coverage.coverage_note ?? null,
  privacyRule: "A camada pública resume o ledger institucional e não republica nomes de credores nem CPF. O coletor mascara CPF na normalização; CNPJ permanece apenas na evidência normalizada quando aplicável.",
  accountingRule: "Todos os registros deste ledger são empenhos/commitments. Nenhum valor é reclassificado como liquidação ou pagamento.",
};

const camara = readJson(path.join(publicRoot, "camara.json"), {});
camara.commitmentLedger = summary;
camara.dataFreshness ??= {};
camara.dataFreshness.commitments = { asOf: ledger.date, source: "CMS_EMPENHOS" };
camara.freshnessModel = "per_source";
camara.coverage = {
  status: summary.status,
  complete: summary.completeForDefaultPublicView,
  records: summary.records,
  pages: summary.pagesWithRecords,
  note: summary.coverageNote,
};
writeJson("camara.json", camara);

const meta = readJson(path.join(publicRoot, "meta.json"), {});
meta.cmsCommitmentsAsOf = ledger.date;
meta.cmsCommitmentsStatus = summary.status;
meta.cmsCommitmentsRecords = summary.records;
meta.cmsCommitmentsPages = summary.pagesWithRecords;
meta.cmsCommitmentsCompleteForDefaultView = summary.completeForDefaultPublicView;
writeJson("meta.json", meta);

console.log(`Câmara: ${summary.records} empenhos resumidos (${summary.pagesWithRecords} páginas), status=${summary.status}, observado em ${ledger.date}.`);
