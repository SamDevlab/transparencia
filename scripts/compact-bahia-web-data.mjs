import fs from "node:fs";
import path from "node:path";

const file = path.join(process.cwd(), "public", "data", "bahia-transparency.json");
if (!fs.existsSync(file)) process.exit(0);

const data = JSON.parse(fs.readFileSync(file, "utf8"));
const sefaz = data.sefaz ?? {};

function compactSchema(table) {
  if (!table?.schema) return table;
  table.schema = { detected_fields: table.schema.detected_fields ?? {} };
  return table;
}

if (sefaz.procurements?.summary) {
  const summary = sefaz.procurements.summary;
  sefaz.procurements.summary = {
    dataset: summary.dataset,
    selected_year: summary.selected_year,
    primary_licitacoes: summary.primary_licitacoes,
    interpretation: summary.interpretation,
    table_classes: summary.table_classes,
  };
}

if (sefaz.expenses?.summary) {
  const summary = sefaz.expenses.summary;
  sefaz.expenses.summary = {
    dataset: summary.dataset,
    selected_year: summary.selected_year,
    primary_table: compactSchema(summary.primary_table),
    interpretation: summary.interpretation,
  };
}

if (sefaz.payments?.summary) {
  const summary = sefaz.payments.summary;
  sefaz.payments.summary = {
    dataset: summary.dataset,
    selected_year: summary.selected_year,
    primary_table: compactSchema(summary.primary_table),
    selected_year_payment: summary.selected_year_payment,
    interpretation: summary.interpretation,
  };
}

if (sefaz.contracts?.summary) {
  const summary = sefaz.contracts.summary;
  const primary = structuredClone(summary.primary_table ?? {});
  delete primary.instrument_keys;
  compactSchema(primary);
  sefaz.contracts.summary = {
    dataset: summary.dataset,
    selected_year: summary.selected_year,
    primary_table: primary,
    interpretation: summary.interpretation,
    identity_rule: summary.identity_rule,
  };
}

if (sefaz.moneyFlow?.top_end_to_end?.length > 50) {
  sefaz.moneyFlow.top_end_to_end = sefaz.moneyFlow.top_end_to_end.slice(0, 50);
  sefaz.moneyFlow.public_limit = 50;
}

const before = fs.statSync(file).size;
fs.writeFileSync(file, JSON.stringify(data), "utf8");
const after = fs.statSync(file).size;
console.log(`Bahia web compactada: ${before} → ${after} bytes`);
