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
  fs.mkdirSync(publicRoot, { recursive: true });
  fs.writeFileSync(path.join(publicRoot, name), JSON.stringify(payload), "utf8");
}
function comparableSnapshots() {
  if (!fs.existsSync(snapshotsRoot)) return [];
  const dates = fs.readdirSync(snapshotsRoot, { withFileTypes: true })
    .filter((entry) => entry.isDirectory() && /^\d{4}-\d{2}-\d{2}$/.test(entry.name))
    .map((entry) => entry.name)
    .sort();
  const out = [];
  for (const date of dates) {
    const dir = path.join(snapshotsRoot, date, "prefeitura_contracts");
    const coverage = readJson(path.join(dir, "coverage.json"));
    if (coverage?.complete_for_filter !== true) continue;
    const file = fs.existsSync(dir)
      ? fs.readdirSync(dir).filter((name) => /^municipal_contract_grid_.*\.jsonl$/.test(name)).sort().at(-1)
      : null;
    if (!file) continue;
    out.push({ date, coverage, file: path.join(dir, file) });
  }
  return out;
}
function exactKey(source) {
  const ug = String(source?.cdUnidadeGestora ?? "").trim();
  const sigef = String(source?.nuContratoSigef ?? "").trim();
  if (!ug || !sigef) return null;
  return `${ug}|${sigef}`;
}
function contractMap(snapshot) {
  const map = new Map();
  for (const wrapper of readJsonl(snapshot.file)) {
    const source = wrapper?.source_record;
    const key = exactKey(source);
    if (!key || map.has(key)) continue;
    map.set(key, source);
  }
  return map;
}

const fields = [
  ["vlAtualizado", "Valor atualizado", "currency"],
  ["dtTerminoVigenciaAtualizado", "Fim da vigência", "date"],
  ["dsSituacao", "Situação", "text"],
  ["percentualExecutado", "Percentual executado", "percent"],
];
const snapshots = comparableSnapshots();
const events = [];
let previous = null;

for (const snapshot of snapshots) {
  const current = contractMap(snapshot);
  if (previous) {
    for (const [key, row] of current) {
      const old = previous.map.get(key);
      const identity = {
        cdUnidadeGestora: row.cdUnidadeGestora ?? null,
        nuContratoSigef: row.nuContratoSigef ?? null,
        nuContratoOriginal: row.nuContratoOriginal ?? null,
        nuProcesso: row.nuProcesso ?? null,
      };
      if (!old) {
        events.push({
          type: "first_observed",
          observedAt: snapshot.date,
          previousObservedAt: previous.snapshot.date,
          contractKey: key,
          identity,
          note: "Contrato observado neste snapshot completo e não observado no snapshot completo comparável imediatamente anterior. Isso indica primeira observação na série preservada, não necessariamente a data jurídica de criação do contrato.",
        });
        continue;
      }
      for (const [field, label, valueType] of fields) {
        const before = old[field] ?? null;
        const after = row[field] ?? null;
        if (String(before ?? "") === String(after ?? "")) continue;
        events.push({
          type: "field_changed",
          observedAt: snapshot.date,
          previousObservedAt: previous.snapshot.date,
          contractKey: key,
          identity,
          field,
          label,
          valueType,
          before,
          after,
          note: "Mudança observada entre dois snapshots completos da mesma grade municipal; não é inferida por similaridade textual.",
        });
      }
    }
  }
  previous = { snapshot, map: current };
}

const latestProbeDates = fs.existsSync(snapshotsRoot)
  ? fs.readdirSync(snapshotsRoot, { withFileTypes: true })
      .filter((entry) => entry.isDirectory() && /^\d{4}-\d{2}-\d{2}$/.test(entry.name))
      .map((entry) => entry.name).sort().reverse()
  : [];
let financeProbe = null;
for (const date of latestProbeDates) {
  const summary = readJson(path.join(snapshotsRoot, date, "contract_finance_probe", "summary.json"));
  if (summary) { financeProbe = { date, summary }; break; }
}
const assessment = financeProbe?.summary?.assessment ?? {};
const sampleAttempts = financeProbe?.summary?.samples ?? [];
const statuses = [];
for (const sample of sampleAttempts) {
  if (sample?.detail?.status != null) statuses.push(sample.detail.status);
  for (const attempts of Object.values(sample?.related ?? {})) {
    for (const attempt of attempts ?? []) if (attempt?.status != null) statuses.push(attempt.status);
  }
}
const allBackend500 = statuses.length > 0 && statuses.every((status) => Number(status) === 500);
const financeStatus = {
  asOf: financeProbe?.date ?? null,
  status: assessment.can_build_exact_contract_finance_collector === true
    ? "available_for_exact_collection"
    : allBackend500 ? "blocked_upstream" : "unproven",
  officialEndpoints: financeProbe?.summary?.official_endpoints ?? [],
  commitmentsProven: assessment.commitment_relation_proven === true,
  liquidationsProven: assessment.liquidation_relation_proven === true,
  paymentsProven: assessment.payment_relation_proven === true,
  blocker: allBackend500 ? "official_contract_finance_endpoints_http_500" : null,
  detail: allBackend500
    ? "Os endpoints oficiais de contrato para detalhamento, empenho, liquidação e pagamento responderam HTTP 500 no backend da Prefeitura durante a ativação do contexto de dados. O projeto não substitui essa falha por vínculos inferidos."
    : "A ligação contrato → execução só será publicada quando os endpoints oficiais devolverem identificadores estruturados e cobertura auditável.",
  accountingRule: "Empenho, liquidação e pagamento permanecem etapas distintas e nunca são intercambiados.",
};

const payload = {
  asOf: snapshots.at(-1)?.date ?? null,
  source: "SALVADOR_TRANSPARENCIA_API_CONTRATOS",
  identityRule: "Histórico usa somente igualdade exata de cdUnidadeGestora + nuContratoSigef entre snapshots completos da mesma fonte.",
  comparisonRule: "Somente snapshots com complete_for_filter=true são comparados. Ausência em um snapshot não é publicada como cancelamento/exclusão; mudanças são registradas apenas quando o mesmo identificador oficial reaparece.",
  status: snapshots.length >= 2 ? "history_available" : "insufficient_comparable_history",
  snapshotsCompared: snapshots.map(({ date, coverage }) => ({
    date,
    periodStart: coverage.period_start ?? null,
    periodEnd: coverage.period_end ?? null,
    records: coverage.records_unique ?? null,
  })),
  events: events.sort((a, b) => String(b.observedAt).localeCompare(String(a.observedAt))),
  summary: {
    comparableSnapshots: snapshots.length,
    events: events.length,
    firstObserved: events.filter((event) => event.type === "first_observed").length,
    fieldChanges: events.filter((event) => event.type === "field_changed").length,
  },
  contractFinance: financeStatus,
};

writeJson("contract-changes.json", payload);
writeJson("contract-finance-status.json", financeStatus);
console.log(`Histórico contratual: snapshots comparáveis=${snapshots.length}; eventos=${events.length}; execução por contrato=${financeStatus.status}.`);
