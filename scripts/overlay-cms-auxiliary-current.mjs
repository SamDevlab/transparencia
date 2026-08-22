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
const certameRows = readJsonl(path.join(current.dir, "cms_certames_visible.jsonl"));
const totalTravel = travelRows.reduce((sum, row) => sum + Number(row.value_brl ?? 0), 0);
const travelWithProcess = travelRows.filter((row) => row.process_number).length;

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
    status: "partial",
    complete: false,
    recordsVisible: Number(current.summary.certames?.records ?? certameRows.length),
    coverage: "server_visible_page_only",
    rows: certameRows.slice(0, 20).map((row) => ({
      modality: row.modality_name ?? null,
      noticeNumber: row.notice_number ?? null,
      scheduledAtText: row.scheduled_at_text ?? null,
      updatedAtText: row.updated_at_text ?? null,
      object: row.object ?? null,
      latestStatusText: row.latest_status_text ?? null,
      sourceUrl: row.source_url ?? null,
    })),
    coverageRule: "Somente a página atualmente visível no servidor foi normalizada. A ausência de um certame nesta lista não significa inexistência no catálogo da Câmara.",
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
meta.cmsVisibleCertames = auxiliary.certames.recordsVisible;
writeJson("meta.json", meta);

console.log(`Câmara auxiliar ${current.date}: viagens=${auxiliary.travel.records}, documentos=${auxiliary.documents.records}, certames visíveis=${auxiliary.certames.recordsVisible}.`);
