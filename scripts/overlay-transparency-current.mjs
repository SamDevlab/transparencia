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

function replaceDataset(datasets, item) {
  const index = datasets.findIndex((row) => row.id === item.id);
  if (index >= 0) datasets[index] = item;
  else datasets.push(item);
}

const transparency = readJson("transparency.json", { datasets: [] });
const meta = readJson("meta.json");
const acquisitions = readJson("acquisitions.json");
const finance = readJson("finance.json");
const contracts = readJson("contracts.json");
const links = readJson("municipal-links.json");
const camara = readJson("camara.json");
const datasets = Array.isArray(transparency.datasets) ? transparency.datasets : [];

const acqSummary = acquisitions.summary ?? {};
replaceDataset(datasets, {
  id: "salvador_aquisicoes",
  title: "Aquisições da Prefeitura",
  status: acqSummary.complete_for_filter === true ? "complete_for_filter" : "partial",
  statusLabel: acqSummary.complete_for_filter === true ? "Completo para o filtro" : "Parcial",
  detail: `${acqSummary.unique_stable_records ?? acqSummary.records_received ?? 0} registros em ${acqSummary.pages_collected ?? 0} páginas, de ${acqSummary.period_start ?? "—"} a ${acqSummary.period_end ?? "—"}. A contagem é aceita como completa apenas quando páginas e total reconciliam com a própria API.`,
  source: "Portal da Transparência de Salvador",
  href: "/licitacoes",
  asOf: acqSummary.period_end ?? null,
});

const financeSummary = finance.summary ?? {};
const financeCounts = financeSummary.record_counts ?? {};
const financeComplete = ["contract_units", "expense_creditors", "expense_functions", "revenue_detail"].every((key) => Number(financeCounts[key] ?? 0) > 0);
replaceDataset(datasets, {
  id: "salvador_financas",
  title: "Receitas e despesas de Salvador",
  status: financeComplete ? "collected" : "partial",
  statusLabel: financeComplete ? "Dados oficiais preservados" : "Cobertura parcial",
  detail: `Recorte ${financeSummary.period_start ?? "—"} a ${financeSummary.period_end ?? "—"}. Receita, empenho, liquidação e pagamento permanecem separados; credores são agregados e não pagamentos individuais.`,
  source: "Portal da Transparência de Salvador",
  href: "/financas",
  asOf: financeSummary.period_end ?? null,
});

const contractComplete = contracts.completeForFilter === true && contracts.sourceSystem === "SALVADOR_TRANSPARENCIA_API_CONTRATOS";
replaceDataset(datasets, {
  id: "salvador_contratos",
  title: "Contratos individualizados",
  status: contractComplete ? "complete_for_filter" : "partial",
  statusLabel: contractComplete ? "Grade municipal completa para o filtro" : "Cobertura municipal detalhada parcial",
  detail: contractComplete
    ? `${contracts.sourceRows ?? contracts.rows?.length ?? 0} linhas reconciliadas com a paginação oficial; ${contracts.publishedRows ?? contracts.rows?.length ?? 0} registros substantivamente distintos são exibidos. UUID técnico não é tratado como identificador oficial e credor em texto livre não é republicado.`
    : "A grade municipal detalhada ainda não satisfez os controles de completude; PNCP permanece como fonte complementar.",
  source: contractComplete ? "Portal da Transparência de Salvador + PNCP complementar" : "Prefeitura de Salvador + PNCP",
  href: "/contratos",
  asOf: contracts.periodEnd ?? contracts.asOf ?? null,
});

const linkSummary = links.summary ?? {};
replaceDataset(datasets, {
  id: "salvador_relacoes",
  title: "Relações aquisição → contrato",
  status: contractComplete && acqSummary.complete_for_filter === true ? "complete_for_filter" : "partial",
  statusLabel: `${linkSummary.processesWithExactContracts ?? 0} processos com contrato exato`,
  detail: `${linkSummary.exactPairs ?? 0} pares documentais ligam ${linkSummary.processesWithExactContracts ?? 0} processos a ${linkSummary.uniqueContractsLinked ?? 0} contratos únicos. A igualdade do número oficial do processo é a única regra de vínculo; não há fuzzy matching e isso não cria ligação automática com pagamento.`,
  source: "Portal da Transparência de Salvador",
  href: "/relacoes",
  asOf: [linkSummary.acquisitionsAsOf, linkSummary.contractsAsOf].filter(Boolean).sort().at(-1) ?? null,
});

const cms = camara.commitmentLedger;
if (cms) {
  replaceDataset(datasets, {
    id: "cms",
    title: "Empenhos da Câmara Municipal",
    status: cms.completeForDefaultPublicView === true ? "complete_for_filter" : "partial",
    statusLabel: cms.completeForDefaultPublicView === true ? "Completo para a visão pública padrão" : "Parcial",
    detail: `${cms.records ?? 0} empenhos em ${cms.pagesWithRecords ?? 0} páginas. Parser completo=${cms.parserCompleteForVisibleRecords === true ? "sim" : "não"}; fonte esgotada=${cms.sourceExhausted === true ? "sim" : "não"}. São empenhos, não liquidações nem pagamentos, e o resumo público não republica nomes de credores nem CPF.`,
    source: "Câmara Municipal de Salvador",
    href: "/camara",
    asOf: cms.asOf ?? null,
  });
}

transparency.asOf = meta.asOf ?? transparency.asOf ?? null;
transparency.latestSourceAsOf = [meta.latestSourceAsOf, meta.cmsCommitmentsAsOf].filter(Boolean).sort().at(-1) ?? null;
transparency.freshnessModel = "per_source";
transparency.dataFreshness = {
  ...(meta.dataFreshness ?? {}),
  ...(cms ? { cmsCommitments: { asOf: cms.asOf ?? null, source: "CMS_EMPENHOS" } } : {}),
};
transparency.datasets = datasets;

writeJson("transparency.json", transparency);
console.log(`Cobertura pública reconciliada: ${datasets.length} conjuntos; fonte mais recente=${transparency.latestSourceAsOf ?? "n/a"}.`);
