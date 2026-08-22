import fs from "node:fs";
import path from "node:path";

const root = process.cwd();
const snapshotsRoot = path.join(root, "cities", "salvador", "data", "snapshots");
const publicRoot = path.join(root, "public", "data");

function readJson(file, fallback = null) {
  if (!fs.existsSync(file)) return fallback;
  return JSON.parse(fs.readFileSync(file, "utf8"));
}

function writeJson(name, payload) {
  fs.writeFileSync(path.join(publicRoot, name), JSON.stringify(payload), "utf8");
}

function readJsonl(file) {
  if (!file || !fs.existsSync(file)) return [];
  return fs.readFileSync(file, "utf8").split(/\r?\n/).filter(Boolean).map((line) => JSON.parse(line));
}

function number(value) {
  return Number(value ?? 0) || 0;
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
    .replace(/[^A-Z0-9]+/g, "")
    .trim();
}

function slugify(value) {
  return normalizeKey(value).replaceAll(" ", "-") || "sem-identificador";
}

function snapshotDates() {
  if (!fs.existsSync(snapshotsRoot)) return [];
  return fs.readdirSync(snapshotsRoot, { withFileTypes: true })
    .filter((entry) => entry.isDirectory() && /^\d{4}-\d{2}-\d{2}$/.test(entry.name))
    .map((entry) => entry.name)
    .sort()
    .reverse();
}

function candidateDirectories(date, name) {
  const snapshot = path.join(snapshotsRoot, date);
  return [path.join(snapshot, name), path.join(snapshot, "production", name)];
}

function latestFinance() {
  for (const date of snapshotDates()) {
    for (const directory of candidateDirectories(date, "prefeitura_finance")) {
      const summary = readJson(path.join(directory, "summary.json"));
      if (!summary) continue;
      const counts = summary.record_counts ?? {};
      const required = ["contract_units", "expense_creditors", "expense_functions", "revenue_detail"];
      if (!required.every((key) => Number(counts[key] ?? 0) > 0)) continue;
      if (!summary.period_start || !summary.period_end) continue;
      const files = ["expense_by_function.jsonl", "expense_by_creditor.jsonl", "contract_execution_by_unit.jsonl", "revenue_events.jsonl"];
      if (!files.every((name) => fs.existsSync(path.join(directory, name)))) continue;
      return { date, directory, summary };
    }
  }
  return null;
}

function latestAcquisitions() {
  for (const date of snapshotDates()) {
    for (const directory of candidateDirectories(date, "prefeitura_acquisitions")) {
      const summary = readJson(path.join(directory, "summary.json"));
      const jsonl = path.join(directory, "acquisitions.jsonl");
      if (summary?.complete_for_filter !== true || !fs.existsSync(jsonl)) continue;
      const unique = Number(summary.unique_stable_records ?? 0);
      const reported = Number(summary.api_reported_total_records ?? 0);
      const pages = Number(summary.pages_collected ?? 0);
      const reportedPages = Number(summary.api_reported_pages ?? 0);
      if (!(unique > 0) || unique !== reported || !(pages > 0) || pages !== reportedPages) continue;
      return { date, directory, summary, jsonl };
    }
  }
  return null;
}

function mapAcquisition(row) {
  return {
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
  };
}

function buildAgencies(acquisitions) {
  const map = new Map();
  for (const row of acquisitions) {
    const name = row.orgao || "Órgão não informado";
    const key = slugify(name);
    const entry = map.get(key) ?? {
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
    entry.tipos[type] ??= { quantidade: 0, valor: 0 };
    entry.tipos[type].quantidade += 1;
    entry.tipos[type].valor += number(row.valor);
    const direct = normalizeKey(row.tipo).includes("dispensa") || normalizeKey(row.tipo).includes("inexigibilidade");
    if (direct) {
      entry.contratacaoDiretaQuantidade += 1;
      entry.contratacaoDiretaValor += number(row.valor);
    }
    entry.maiores.push({ id: row.id, processo: row.processo, numero: row.numero, objeto: row.objeto, tipo: row.tipo, valor: row.valor, publicadoEm: row.publicadoEm });
    map.set(key, entry);
  }
  return [...map.values()].map((entry) => ({
    ...entry,
    valorMedio: entry.quantidade ? entry.valorDeclarado / entry.quantidade : 0,
    percentualContratacaoDireta: entry.quantidade ? entry.contratacaoDiretaQuantidade / entry.quantidade : 0,
    tipos: Object.entries(entry.tipos).map(([tipo, values]) => ({ tipo, ...values })).sort((a, b) => b.valor - a.valor),
    maiores: entry.maiores.sort((a, b) => number(b.valor) - number(a.valor)).slice(0, 15),
  })).sort((a, b) => b.valorDeclarado - a.valorDeclarado);
}

function aggregateAcquisitions(acquisitions, keyFn, labelFn) {
  const map = new Map();
  for (const row of acquisitions) {
    const key = keyFn(row) || "Não informado";
    const current = map.get(key) ?? { name: labelFn(row) || key, count: 0, value: 0 };
    current.count += 1;
    current.value += number(row.valor);
    map.set(key, current);
  }
  return [...map.values()].sort((a, b) => b.value - a.value);
}

function buildProcesses(acquisitions, contracts) {
  const byProcess = new Map();
  for (const contract of contracts) {
    const key = normalizeReference(contract.processo);
    if (!key) continue;
    const list = byProcess.get(key) ?? [];
    list.push(contract);
    byProcess.set(key, list);
  }
  return acquisitions.map((row) => {
    const exactContracts = byProcess.get(normalizeReference(row.processo)) ?? [];
    const timeline = [
      row.realizadoEm ? { data: row.realizadoEm, tipo: "Aquisição", titulo: "Data da aquisição", fonte: row.fonte } : null,
      row.publicadoEm ? { data: row.publicadoEm, tipo: "Publicação", titulo: "Publicação municipal", fonte: row.fonte } : null,
      ...exactContracts.flatMap((contract) => [
        contract.assinadoEm ? { data: contract.assinadoEm, tipo: "Contrato", titulo: `Contrato ${contract.numero || contract.numeroSigef || "registrado"} assinado`, fonte: contract.fonte } : null,
        contract.publicadoEm ? { data: contract.publicadoEm, tipo: "Publicação", titulo: `Contrato ${contract.numero || "registrado"} publicado`, fonte: contract.fonte } : null,
        contract.vigenciaInicio ? { data: contract.vigenciaInicio, tipo: "Vigência", titulo: "Início da vigência contratual", fonte: contract.fonte } : null,
        contract.vigenciaFim ? { data: contract.vigenciaFim, tipo: "Vigência", titulo: "Fim previsto da vigência contratual", fonte: contract.fonte } : null,
      ]),
    ].filter(Boolean).sort((a, b) => String(a.data).localeCompare(String(b.data)));
    return { ...row, contratosExatos: exactContracts, linhaDoTempo: timeline };
  });
}

function exactLinks(processes) {
  return processes.filter((process) => process.contratosExatos?.length > 0).map((process) => ({
    processoId: process.id,
    processo: process.processo,
    objeto: process.objeto,
    orgao: process.orgao,
    valorAquisicao: process.valor,
    contratos: process.contratosExatos.map((contract) => ({
      numero: contract.numero || contract.numeroSigef,
      fornecedor: contract.fornecedor,
      documentoFornecedor: contract.documentoFornecedor ?? null,
      valorGlobal: contract.valorGlobal,
      fonte: contract.fonte,
    })),
    metodo: "Número de processo normalizado com correspondência exata entre as duas fontes; nenhuma similaridade textual cria vínculo.",
  }));
}

function acquisitionSearchRows(agencies, processes) {
  return [
    ...agencies.map((agency) => ({
      tipo: "Órgão",
      grupo: "Órgãos",
      titulo: agency.nome,
      detalhe: `${agency.quantidade} aquisições no recorte`,
      referencia: agency.sigla || "",
      href: `/orgaos/${agency.id}`,
      termos: normalizeKey([agency.nome, agency.sigla].join(" ")),
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
  ];
}

const meta = readJson(path.join(publicRoot, "meta.json"), {});
const dashboard = readJson(path.join(publicRoot, "dashboard.json"), {});
const money = readJson(path.join(publicRoot, "money.json"), {});
const search = readJson(path.join(publicRoot, "search.json"), { rows: [] });
const analysis = readJson(path.join(publicRoot, "analysis.json"), {});
const comparisons = readJson(path.join(publicRoot, "comparisons.json"), {});
const contractsPublic = readJson(path.join(publicRoot, "contracts.json"), { rows: [] });

const finance = latestFinance();
if (finance) {
  const summary = finance.summary;
  const expenseFunctions = readJsonl(path.join(finance.directory, "expense_by_function.jsonl")).sort((a, b) => number(b.paid_value) - number(a.paid_value));
  const expenseCreditors = readJsonl(path.join(finance.directory, "expense_by_creditor.jsonl")).sort((a, b) => number(b.paid_value) - number(a.paid_value)).slice(0, 750);
  const contractUnits = readJsonl(path.join(finance.directory, "contract_execution_by_unit.jsonl")).sort((a, b) => number(b.contracted_value) - number(a.contracted_value));
  const revenue = readJsonl(path.join(finance.directory, "revenue_events.jsonl")).sort((a, b) => number(b.collected_value) - number(a.collected_value)).slice(0, 350);

  writeJson("finance.json", { asOf: summary.period_end, summary, expenseFunctions, expenseCreditors, contractUnits, revenue });
  dashboard.finance = summary;
  dashboard.dataFreshness ??= {};
  dashboard.dataFreshness.finance = { asOf: summary.period_end, periodStart: summary.period_start, source: summary.source_system };
  money.asOf = summary.period_end;
  money.financeSummary = summary;
  money.expenseFunctions = expenseFunctions.slice(0, 15);
  money.contractUnits = contractUnits;
  meta.financeAsOf = summary.period_end;
  meta.financePeriodStart = summary.period_start;
  meta.financeSource = summary.source_system;
  meta.creditorsPublished = expenseCreditors.length;
  console.log(`Finanças municipais promovidas: ${summary.period_start} → ${summary.period_end}.`);
}

const acquisitionSource = latestAcquisitions();
if (acquisitionSource) {
  const acquisitions = readJsonl(acquisitionSource.jsonl).map(mapAcquisition).sort((a, b) => number(b.valor) - number(a.valor));
  const agencies = buildAgencies(acquisitions);
  const processes = buildProcesses(acquisitions, contractsPublic.rows ?? []);
  const links = exactLinks(processes);
  const byType = aggregateAcquisitions(acquisitions, (row) => row.tipo || row.modalidade, (row) => row.tipo || row.modalidade || "Não informado");
  const byAgency = aggregateAcquisitions(acquisitions, (row) => row.orgao, (row) => row.orgao || "Órgão não informado");
  const highValueAcquisitions = acquisitions.filter((row) => number(row.valor) >= 1_000_000).slice(0, 60);
  const directAcquisitions = acquisitions.filter((row) => normalizeKey(row.tipo).includes("dispensa") || normalizeKey(row.tipo).includes("inexigibilidade")).slice(0, 60);

  writeJson("acquisitions.json", { asOf: acquisitionSource.summary.period_end, summary: acquisitionSource.summary, rows: acquisitions });
  writeJson("processes.json", { asOf: acquisitionSource.summary.period_end, rows: processes });
  writeJson("agencies.json", { asOf: acquisitionSource.summary.period_end, rows: agencies });
  comparisons.asOf = acquisitionSource.summary.period_end;
  comparisons.agencies = agencies;
  analysis.asOf = acquisitionSource.summary.period_end;
  analysis.highValueAcquisitions = highValueAcquisitions;
  analysis.directAcquisitions = directAcquisitions;
  analysis.exactCrossSourceLinks = links;

  dashboard.acquisitions = { summary: acquisitionSource.summary, byType, byAgency: byAgency.slice(0, 12), top: acquisitions.slice(0, 6) };
  dashboard.dataFreshness ??= {};
  dashboard.dataFreshness.acquisitions = { asOf: acquisitionSource.summary.period_end, periodStart: acquisitionSource.summary.period_start, source: acquisitionSource.summary.source_system };
  dashboard.suppliers ??= {};
  dashboard.suppliers.exactLinks = links.length;

  money.agencies = agencies;
  money.exactCrossSourceLinks = links;

  const preservedSearch = (search.rows ?? []).filter((item) => !["Órgãos", "Processos"].includes(item.grupo));
  search.asOf = acquisitionSource.summary.period_end;
  search.rows = [...preservedSearch, ...acquisitionSearchRows(agencies, processes)];

  meta.acquisitions = acquisitions.length;
  meta.processes = processes.length;
  meta.agencies = agencies.length;
  meta.exactCrossSourceLinks = links.length;
  meta.acquisitionsAsOf = acquisitionSource.summary.period_end;
  meta.acquisitionsPeriodStart = acquisitionSource.summary.period_start;
  meta.acquisitionsSource = acquisitionSource.summary.source_system;
  meta.searchItems = search.rows.length;
  console.log(`Aquisições municipais promovidas: ${acquisitions.length} registros até ${acquisitionSource.summary.period_end}; vínculos exatos com contratos=${links.length}.`);
}

const sourceDates = [meta.snapshotDate, meta.financeAsOf, meta.acquisitionsAsOf, meta.municipalContractsPeriodEnd].filter(Boolean).sort();
meta.latestSourceAsOf = sourceDates.at(-1) ?? meta.asOf;
meta.freshnessModel = "per_source";
dashboard.latestSourceAsOf = meta.latestSourceAsOf;
dashboard.freshnessModel = "per_source";

writeJson("dashboard.json", dashboard);
writeJson("money.json", money);
writeJson("search.json", search);
writeJson("analysis.json", analysis);
writeJson("comparisons.json", comparisons);
writeJson("meta.json", meta);
