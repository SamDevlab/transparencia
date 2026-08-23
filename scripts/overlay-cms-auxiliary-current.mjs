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
  if (!fs.existsSync(file)) return [];
  return fs.readFileSync(file, "utf8").split(/\r?\n/).filter(Boolean).map((line) => JSON.parse(line));
}
function writeJson(name, value) {
  fs.writeFileSync(path.join(publicRoot, name), JSON.stringify(value), "utf8");
}
function latestAux() {
  if (!fs.existsSync(snapshotsRoot)) return null;
  const dates = fs.readdirSync(snapshotsRoot, { withFileTypes: true })
    .filter((entry) => entry.isDirectory() && /^\d{4}-\d{2}-\d{2}$/.test(entry.name))
    .map((entry) => entry.name).sort().reverse();
  for (const date of dates) {
    const dir = path.join(snapshotsRoot, date, "cms_auxiliary");
    const summary = readJson(path.join(dir, "summary.json"));
    if (summary) return { date, dir, summary };
  }
  return null;
}

const current = latestAux();
if (!current) {
  console.log("Câmara auxiliar: nenhum snapshot atual encontrado.");
  process.exit(0);
}

const travelRows = readJsonl(path.join(current.dir, "cms_travel_expenses.jsonl"));
const certameFile = fs.existsSync(path.join(current.dir, "cms_certames.jsonl"))
  ? path.join(current.dir, "cms_certames.jsonl")
  : path.join(current.dir, "cms_certames_visible.jsonl");
const certameRows = readJsonl(certameFile);
const totalTravel = travelRows.reduce((sum, row) => sum + Number(row.value_brl ?? 0), 0);
const travelWithProcess = travelRows.filter((row) => row.process_number).length;
const certameSummary = current.summary.certames ?? {};
const certamesComplete = certameSummary.complete === true
  && Number(certameSummary.records ?? certameRows.length) === Number(certameSummary.server_reported_total ?? -1)
  && certameSummary.reached_server_end === true;
const certameCount = Number(certameSummary.records ?? certameRows.length);
const certameExpected = Number.isFinite(Number(certameSummary.server_reported_total))
  ? Number(certameSummary.server_reported_total)
  : null;

const auxiliary = {
  asOf: current.date,
  travel: {
    status: current.summary.travel?.complete ? "complete_for_filter" : "partial",
    complete: current.summary.travel?.complete === true,
    records: Number(current.summary.travel?.records ?? travelRows.length),
    pages: Number(current.summary.travel?.pages_collected ?? 0),
    totalValue: totalTravel,
    recordsWithProcessNumber: travelWithProcess,
    publicDetailRule: "A camada pública exibe apenas contagem e valor agregado dos registros de viagem. Nomes de usuários, justificativas e demais campos pessoais/textuais permanecem na evidência preservada e não são republicados neste resumo.",
  },
  documents: {
    status: current.summary.documents?.complete ? "complete_for_filter" : "partial",
    complete: current.summary.documents?.complete === true,
    records: Number(current.summary.documents?.records ?? 0),
    sections: current.summary.documents?.sections ?? {},
    publicDetailRule: "O portal publica a cobertura e as contagens do catálogo; os documentos continuam acessíveis nas páginas oficiais da Câmara.",
  },
  certames: {
    status: certamesComplete ? "complete_for_filter" : "partial",
    complete: certamesComplete,
    records: certameCount,
    serverReportedTotal: certameExpected,
    pages: Number(certameSummary.pages_collected ?? 0),
    reachedServerEnd: certameSummary.reached_server_end === true,
    coverage: certameSummary.coverage ?? (certamesComplete ? "scriptcase_full_catalogue" : "server_visible_page_only"),
    rows: certameRows.slice(0, 20).map((row) => ({
      modality: row.modality_name ?? null,
      noticeNumber: row.notice_number ?? null,
      scheduledAtText: row.scheduled_at_text ?? null,
      updatedAtText: row.updated_at_text ?? null,
      object: row.object ?? null,
      latestStatusText: row.latest_status_text ?? null,
      sourceUrl: row.source_url ?? null,
    })),
    coverageRule: certamesComplete
      ? "O catálogo foi paginado pela própria sessão ScriptCase até o fim declarado pelo servidor; completude exige que a quantidade de linhas normalizadas seja exatamente igual ao total informado pela fonte."
      : "A cobertura permanece parcial porque a sessão, paginação, transporte ou parser não comprovou simultaneamente o fim do catálogo e igualdade com o total informado pelo servidor. Ausência não significa inexistência.",
  },
};

const camara = readJson(path.join(publicRoot, "camara.json"), {});
camara.auxiliary = auxiliary;
camara.dataFreshness ??= {};
camara.dataFreshness.auxiliary = { asOf: current.date, source: "CMS" };
camara.freshnessModel = "per_source";
writeJson("camara.json", camara);

const meta = readJson(path.join(publicRoot, "meta.json"), {});
meta.cmsAuxiliaryAsOf = current.date;
meta.cmsTravelRecords = auxiliary.travel.records;
meta.cmsDocumentsRecords = auxiliary.documents.records;
meta.cmsCertamesRecords = auxiliary.certames.records;
meta.cmsCertamesStatus = auxiliary.certames.status;
meta.cmsCertamesServerReportedTotal = auxiliary.certames.serverReportedTotal;
// Backward-compatible field retained until downstream consumers migrate.
meta.cmsVisibleCertames = auxiliary.certames.records;
writeJson("meta.json", meta);

console.log(`Câmara auxiliar ${current.date}: viagens=${auxiliary.travel.records}, documentos=${auxiliary.documents.records}, certames=${auxiliary.certames.records}/${auxiliary.certames.serverReportedTotal ?? "?"}, status=${auxiliary.certames.status}.`);
