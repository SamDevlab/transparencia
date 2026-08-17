"use client";

import { useEffect, useMemo, useState } from "react";

function brl(value) {
  return new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" }).format(Number(value ?? 0));
}

function normalize(value) {
  return String(value ?? "").normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase();
}

function Copiar({ valor }) {
  const [copiado, setCopiado] = useState(false);
  if (!valor) return null;
  return (
    <button
      type="button"
      className="copiar"
      onClick={async () => {
        try {
          await navigator.clipboard.writeText(String(valor));
          setCopiado(true);
          setTimeout(() => setCopiado(false), 1300);
        } catch {
          setCopiado(false);
        }
      }}
    >
      {copiado ? "Copiado" : "Copiar"}
    </button>
  );
}

export default function FinanceExplorer() {
  const [data, setData] = useState(null);
  const [query, setQuery] = useState("");
  const [mode, setMode] = useState("creditors");

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    setQuery(params.get("busca") || "");
    setMode(params.get("tipo") === "receita" ? "revenue" : "creditors");
    fetch("/data/finance.json")
      .then((response) => {
        if (!response.ok) throw new Error("Falha ao carregar dados financeiros");
        return response.json();
      })
      .then(setData)
      .catch(() => setData({ error: true }));
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
  if (data.error) return <div className="card empty">Não foi possível carregar os dados financeiros desta publicação.</div>;

  return (
    <div>
      <div className="toolbar" style={{ gridTemplateColumns: "minmax(240px, 1fr) 220px" }}>
        <input className="input" value={query} onChange={(event) => setQuery(event.target.value)} placeholder={mode === "revenue" ? "Buscar natureza ou código de receita…" : "Buscar credor ou código…"} />
        <select className="select" value={mode} onChange={(event) => setMode(event.target.value)}>
          <option value="creditors">Despesa por credor</option>
          <option value="revenue">Receita por natureza</option>
        </select>
      </div>
      <div className="results-line"><span>Exibindo até 100 resultados.</span><span>{mode === "creditors" ? "Credor = total agregado no período" : "Receita = natureza publicada pela fonte"}</span></div>
      <div className="card table-card">
        <div className="table-wrap">
          {mode === "creditors" ? (
            <table>
              <thead><tr><th>Credor agregado</th><th>Código</th><th>Empenhado</th><th>Liquidado</th><th>Pago</th></tr></thead>
              <tbody>{rows.map((row, index) => <tr key={`${row.dimension_code}-${row.dimension_name}-${index}`}><td><strong>{row.dimension_name || "—"}</strong></td><td><div className="referencia-linha"><span className="mono">{row.dimension_code || "—"}</span><Copiar valor={row.dimension_code} /></div></td><td className="mono">{brl(row.committed_value)}</td><td className="mono">{brl(row.liquidated_value)}</td><td><strong className="mono">{brl(row.paid_value)}</strong></td></tr>)}</tbody>
            </table>
          ) : (
            <table>
              <thead><tr><th>Natureza</th><th>Código</th><th>Previsão</th><th>Realizado</th><th>Acumulado</th></tr></thead>
              <tbody>{rows.map((row, index) => <tr key={`${row.nature_code}-${index}`}><td><strong>{row.nature_name || "—"}</strong></td><td><div className="referencia-linha"><span className="mono">{row.nature_code || "—"}</span><Copiar valor={row.nature_code} /></div></td><td className="mono">{brl(row.forecast_value)}</td><td><strong className="mono">{brl(row.collected_value)}</strong></td><td className="mono">{brl(row.accumulated_value)}</td></tr>)}</tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  );
}
