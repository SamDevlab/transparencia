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

const meta = readJson("meta.json");
const dashboard = readJson("dashboard.json");
const money = readJson("money.json");
const search = readJson("search.json", { rows: [] });
const analysis = readJson("analysis.json");
const comparisons = readJson("comparisons.json");
const contracts = readJson("contracts.json", { rows: [] });

const baseAsOf = meta.asOf || meta.snapshotDate || null;
const financeFreshness = meta.financeAsOf
  ? { asOf: meta.financeAsOf, periodStart: meta.financePeriodStart ?? null, source: meta.financeSource ?? null }
  : null;
const acquisitionsFreshness = meta.acquisitionsAsOf
  ? { asOf: meta.acquisitionsAsOf, periodStart: meta.acquisitionsPeriodStart ?? null, source: meta.acquisitionsSource ?? null }
  : null;
const contractsFreshness = meta.municipalContractsAvailable
  ? {
      asOf: meta.municipalContractsPeriodEnd ?? contracts.periodEnd ?? null,
      periodStart: meta.municipalContractsPeriodStart ?? contracts.periodStart ?? null,
      source: contracts.sourceSystem ?? meta.contractsPrimarySource ?? null,
    }
  : {
      asOf: contracts.asOf ?? baseAsOf,
      periodStart: null,
      source: contracts.sourceSystem ?? contracts.source ?? "PNCP",
    };

// Preserve freshness records produced by earlier source-specific overlays. This script
// normalizes municipal freshness, but must not erase PNCP/Câmara/Bahia source state.
const freshness = {
  ...(meta.dataFreshness ?? {}),
  baseSnapshot: { asOf: baseAsOf, source: "snapshot_base" },
  finance: financeFreshness,
  acquisitions: acquisitionsFreshness,
  contracts: contractsFreshness,
};

meta.freshnessModel = "per_source";
meta.dataFreshness = freshness;

// These payloads intentionally mix datasets with different source dates. Keep the
// legacy top-level asOf anchored to the base snapshot and expose freshness per source.
for (const payload of [money, search, analysis]) {
  payload.asOf = baseAsOf;
  payload.freshnessModel = "per_source";
  payload.dataFreshness = {
    ...(payload.dataFreshness ?? {}),
    ...freshness,
  };
}

// Comparisons are rebuilt solely from the current municipal acquisitions overlay.
comparisons.freshnessModel = "single_source";
comparisons.dataFreshness = { acquisitions: acquisitionsFreshness };
if (acquisitionsFreshness?.asOf) comparisons.asOf = acquisitionsFreshness.asOf;

// Dashboard may present multiple modules, so keep the same explicit source map.
dashboard.freshnessModel = "per_source";
dashboard.dataFreshness = {
  ...(dashboard.dataFreshness ?? {}),
  ...freshness,
};

writeJson("meta.json", meta);
writeJson("dashboard.json", dashboard);
writeJson("money.json", money);
writeJson("search.json", search);
writeJson("analysis.json", analysis);
writeJson("comparisons.json", comparisons);

console.log(`Freshness municipal normalizada por fonte; snapshot-base=${baseAsOf || "n/a"}, mais recente=${meta.latestSourceAsOf || "n/a"}.`);
