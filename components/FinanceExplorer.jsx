"use client";

import { useEffect, useMemo, useState } from "react";

function brl(value) {
  return new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" }).format(Number(value ?? 0));
}

function normalize(value) {
  return String(value ?? "").normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase();
}

export default function FinanceExplorer() {
  const [data, setData] = useState(null);
  const [query, setQuery] = useState("");
  const [mode, setMode] = useState("creditors");

  useEffect(() => {
    fetch("/data/finance.json").then((response) => response.json()).then(setData).catch(() => setData({ error: true }));
  }, []);

  const rows = useMemo(() => {
    if (!data) return [];
    const needle = normalize(query);
    const source = mode === "revenue" ? data.revenue : data.expenseCreditors;
    return source.filter((row) => {
      if (!needle) return true;
      return normalize(mode === "revenue" ? `${row.nature_name} ${row.nature_code}` : `${row.dimension_name} ${row.dimension_code}`).includes(needle);
    }).slice(0, 100);
  }, [data, query, mode]);

  if (!data) return <div className="card loading">Carregando detalhamento financeiro…</div>;
  if (data.error) return <div className="card empty">Falha ao carregar o dataset financeiro deste deploy.</div>;

  return (
    <div>
      <div className="toolbar" style={{ gridTemplateColumns: "minmax(240px, 1fr) 220px" }}>
        <input className="input" value={query} onChange={(event) => setQuery(event.target.value)} placeholder={mode === "revenue" ? "Buscar natureza de receita…" : "Buscar credor agregado…"} />
        <select className="select" value={mode} onChange={(event) => setMode(event.target.value)}>
          <option value="creditors">Despesa por credor</option>
          <option value="revenue">Receita por natureza</option>
        </select>
      </div>
      <div className="results-line"><span>Exibindo até 100 resultados do recorte publicado.</span><span>{mode === "creditors" ? "Credor = agregado do período" : "Receita = natureza publicada"}</span></div>
      <div className="card table-card">
        <div className="table-wrap">
          {mode === "creditors" ? (
            <table>
              <thead><tr><th>Credor agregado</th><th>Empenhado</th><th>Liquidado</th><th>Pago</th></tr></thead>
              <tbody>{rows.map((row, index) => <tr key={`${row.dimension_code}-${row.dimension_name}-${index}`}><td><strong>{row.dimension_name || "—"}</strong><div className="muted mono">{row.dimension_code || ""}</div></td><td className="mono">{brl(row.committed_value)}</td><td className="mono">{brl(row.liquidated_value)}</td><td><strong className="mono">{brl(row.paid_value)}</strong></td></tr>)}</tbody>
            </table>
          ) : (
            <table>
              <thead><tr><th>Natureza</th><th>Previsão</th><th>Realizado</th><th>Acumulado</th></tr></thead>
              <tbody>{rows.map((row, index) => <tr key={`${row.nature_code}-${index}`}><td><strong>{row.nature_name || "—"}</strong><div className="muted mono">{row.nature_code || ""}</div></td><td className="mono">{brl(row.forecast_value)}</td><td><strong className="mono">{brl(row.collected_value)}</strong></td><td className="mono">{brl(row.accumulated_value)}</td></tr>)}</tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  );
}
