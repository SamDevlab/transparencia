import fs from "node:fs";
import path from "node:path";

export function loadWebData(name) {
  const file = path.join(process.cwd(), "public", "data", name);
  return JSON.parse(fs.readFileSync(file, "utf8"));
}

export function brl(value, { compact = false } = {}) {
  const numeric = Number(value ?? 0);
  return new Intl.NumberFormat("pt-BR", {
    style: "currency",
    currency: "BRL",
    notation: compact ? "compact" : "standard",
    maximumFractionDigits: compact ? 1 : 2,
  }).format(numeric);
}

export function integer(value) {
  return new Intl.NumberFormat("pt-BR").format(Number(value ?? 0));
}

export function dateBR(value) {
  if (!value) return "—";
  const date = new Date(`${String(value).slice(0, 10)}T12:00:00-03:00`);
  if (Number.isNaN(date.getTime())) return String(value);
  return new Intl.DateTimeFormat("pt-BR").format(date);
}

export function parseBrlText(value) {
  if (typeof value === "number") return value;
  if (!value) return 0;
  return Number(String(value).replace(/\./g, "").replace(",", ".")) || 0;
}
