import fs from "node:fs";
import path from "node:path";

const file = path.join(process.cwd(), "public", "data", "bahia-transparency.json");
if (!fs.existsSync(file)) process.exit(0);

const data = JSON.parse(fs.readFileSync(file, "utf8"));
const sefaz = data.sefaz ?? {};

function defined(object) {
  return Object.fromEntries(Object.entries(object).filter(([, value]) => value !== undefined));
}

function compactSchema(table) {
  if (!table?.schema) return table;
  table.schema = { detected_fields: table.schema.detected_fields ?? {} };
  return table;
}

function compactProvenance(payload) {
  if (!payload || typeof payload !== "object") return payload;
  if (payload.evidence) {
    payload.evidence = defined({ sha256: payload.evidence.sha256 });
  }
  if (payload.resource) {
    payload.resource = defined({
      name: payload.resource.name,
      last_modified: payload.resource.last_modified,
      url: payload.resource.url,
    });
  }
  delete payload.transport;
  delete payload.privacy;
  return payload;
}

function compactStateCoverage(coverage) {
  if (!coverage?.sefaz_data) return coverage ? { sefaz_data: {} } : coverage;
  return {
    sefaz_data: Object.fromEntries(
      Object.entries(coverage.sefaz_data).map(([dataset, item]) => [
        dataset,
        defined({ status: item?.status, error: item?.error }),
      ]),
    ),
  };
}

for (const key of ["revenues", "procurements", "expenses", "payments", "contracts"]) {
  compactProvenance(sefaz[key]);
}

if (sefaz.revenues?.summary) {
  const summary = sefaz.revenues.summary;
  sefaz.revenues.summary = defined({
    dataset: summary.dataset,
    selected_year: summary.selected_year,
    rows: summary.rows,
    selected_year_totals: summary.selected_year_totals,
    selected_year_monthly: summary.selected_year_monthly,
    interpretation: summary.interpretation,
    schema: summary.schema ? { detected_fields: summary.schema.detected_fields ?? {} } : undefined,
  });
}

if (sefaz.procurements?.summary) {
  const summary = sefaz.procurements.summary;
  sefaz.procurements.summary = defined({
    dataset: summary.dataset,
    selected_year: summary.selected_year,
    primary_licitacoes: summary.primary_licitacoes,
    interpretation: summary.interpretation,
    table_classes: summary.table_classes,
  });
}

if (sefaz.expenses?.summary) {
  const summary = sefaz.expenses.summary;
  const primary = summary.primary_table
    ? compactSchema(defined({
        member: summary.primary_table.member,
        rows: summary.primary_table.rows,
        selected_rows: summary.primary_table.selected_rows,
        stage_totals: summary.primary_table.stage_totals,
        top_agencies: summary.primary_table.top_agencies,
        schema: summary.primary_table.schema,
      }))
    : undefined;
  sefaz.expenses.summary = defined({
    dataset: summary.dataset,
    selected_year: summary.selected_year,
    primary_table: primary,
    interpretation: summary.interpretation,
  });
}

if (sefaz.payments?.summary) {
  const summary = sefaz.payments.summary;
  const primary = summary.primary_table
    ? compactSchema(defined({
        member: summary.primary_table.member,
        rows: summary.primary_table.rows,
        selected_rows: summary.primary_table.selected_rows,
        schema: summary.primary_table.schema,
      }))
    : undefined;
  sefaz.payments.summary = defined({
    dataset: summary.dataset,
    selected_year: summary.selected_year,
    primary_table: primary,
    selected_year_payment: summary.selected_year_payment,
    interpretation: summary.interpretation,
  });
}

if (sefaz.contracts?.summary) {
  const summary = sefaz.contracts.summary;
  const sourcePrimary = summary.primary_table ?? {};
  const primary = compactSchema(defined({
    member: sourcePrimary.member,
    rows: sourcePrimary.rows,
    selected_rows: sourcePrimary.selected_rows,
    unique_instruments: sourcePrimary.unique_instruments,
    unique_process_keys: sourcePrimary.unique_process_keys,
    contract_value: sourcePrimary.contract_value,
    deduplication: sourcePrimary.deduplication,
    top_agencies: sourcePrimary.top_agencies,
    top_suppliers_cnpj_only: sourcePrimary.top_suppliers_cnpj_only,
    top_statuses: sourcePrimary.top_statuses,
    schema: sourcePrimary.schema,
  }));
  sefaz.contracts.summary = defined({
    dataset: summary.dataset,
    selected_year: summary.selected_year,
    primary_table: primary,
    interpretation: summary.interpretation,
    identity_rule: summary.identity_rule,
  });
}

if (sefaz.moneyFlow) {
  const flow = sefaz.moneyFlow;
  sefaz.moneyFlow = defined({
    selected_year: flow.selected_year,
    source: flow.source,
    summary: flow.summary,
    identity_rule: flow.identity_rule,
    contract_profile_identity_rule: flow.contract_profile_identity_rule,
    contract_profile_ambiguity_rule: flow.contract_profile_ambiguity_rule,
    interpretation: flow.interpretation,
    privacy_rule: flow.privacy_rule,
    top_end_to_end: Array.isArray(flow.top_end_to_end) ? flow.top_end_to_end : [],
  });
}

if (data.coverage) {
  data.coverage = compactStateCoverage(data.coverage);
}

const before = fs.statSync(file).size;
fs.writeFileSync(file, JSON.stringify(data), "utf8");
const after = fs.statSync(file).size;
console.log(`Bahia web compactada: ${before} → ${after} bytes`);
