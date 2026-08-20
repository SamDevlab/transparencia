"use client";

import { useEffect, useMemo, useState } from "react";

function normalizar(valor) {
  return String(valor ?? "").normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase();
}

function usd(valor, compacto = false) {
  return new Intl.NumberFormat("pt-BR", {
    style: "currency",
    currency: "USD",
    notation: compacto ? "compact" : "standard",
    maximumFractionDigits: compacto ? 1 : 2,
  }).format(Number(valor ?? 0));
}

function pct(valor) {
  return new Intl.NumberFormat("pt-BR", { style: "percent", maximumFractionDigits: 1 }).format(Number(valor ?? 0));
}

export default function TradeExplorer({ scope }) {
  const [dados, setDados] = useState(null);
  const [busca, setBusca] = useState("");
  const [visao, setVisao] = useState("produtos");
  const [saldo, setSaldo] = useState("todos");
  const [ordem, setOrdem] = useState("movimento");

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    setBusca(params.get("busca") || "");
    fetch("/data/economy.json")
      .then((resposta) => resposta.json())
      .then(setDados)
      .catch(() => setDados({ available: false }));
  }, []);

  const resultados = useMemo(() => {
    const data = dados?.[scope];
    if (!data) return [];
    const origem = visao === "paises" ? data.countries : data.products;
    const termo = normalizar(busca.trim());
    return origem
      .filter((row) => {
        const balance = Number(row.balance_fob ?? 0);
        if (saldo === "deficit" && balance >= 0) return false;
        if (saldo === "superavit" && balance <= 0) return false;
        if (!termo) return true;
        return normalizar([
          row.sh4,
          row.product,
          row.country,
          row.country_code,
          row.top_import_country?.country,
          row.top_export_country?.country,
        ].filter(Boolean).join(" ")).includes(termo);
      })
      .sort((a, b) => {
        if (ordem === "importacoes") return Number(b.imports_fob ?? 0) - Number(a.imports_fob ?? 0);
        if (ordem === "exportacoes") return Number(b.exports_fob ?? 0) - Number(a.exports_fob ?? 0);
        if (ordem === "saldo") return Number(a.balance_fob ?? 0) - Number(b.balance_fob ?? 0);
        return (Number(b.imports_fob ?? 0) + Number(b.exports_fob ?? 0)) - (Number(a.imports_fob ?? 0) + Number(a.exports_fob ?? 0));
      })
      .slice(0, 120);
  }, [dados, scope, busca, visao, saldo, ordem]);

  if (!dados) return <div className="card loading">Carregando comércio exterior…</div>;
  if (!dados.available || !dados[scope]) return <div className="card empty">O snapshot econômico ainda não está disponível para esta publicação. A cobertura da fonte continua visível na página de Transparência.</div>;

  return (
    <div>
      <div className="toolbar trade-toolbar">
        <input className="input" value={busca} onChange={(e) => setBusca(e.target.value)} placeholder="Buscar SH4, produto ou país…" />
        <select className="select" value={visao} onChange={(e) => setVisao(e.target.value)}>
          <option value="produtos">Produtos SH4</option>
          <option value="paises">Países</option>
        </select>
        <select className="select" value={saldo} onChange={(e) => setSaldo(e.target.value)}>
          <option value="todos">Todos os saldos</option>
          <option value="deficit">Saldo negativo</option>
          <option value="superavit">Saldo positivo</option>
        </select>
        <select className="select" value={ordem} onChange={(e) => setOrdem(e.target.value)}>
          <option value="movimento">Maior corrente</option>
          <option value="importacoes">Maiores importações</option>
          <option value="exportacoes">Maiores exportações</option>
          <option value="saldo">Maior déficit</option>
        </select>
      </div>
      <div className="results-line"><span><strong>{resultados.length}</strong> resultados exibidos</span><span>Valores FOB em dólares dos EUA</span></div>
      <div className="card table-card">
        <div className="table-wrap">
          {visao === "produtos" ? (
            <table className="trade-table"><thead><tr><th>SH4 / produto</th><th>Exportações</th><th>Importações</th><th>Saldo</th><th>Principal origem</th><th>Concentração</th></tr></thead>
              <tbody>{resultados.map((row, index) => <tr key={`${row.sh4}-${index}`}><td><strong>{row.sh4 || "—"}</strong><div>{row.product || "Não informado"}</div></td><td className="mono">{usd(row.exports_fob)}</td><td className="mono">{usd(row.imports_fob)}</td><td className={`mono ${Number(row.balance_fob) < 0 ? "saldo-negativo" : "saldo-positivo"}`}>{usd(row.balance_fob)}</td><td>{row.top_import_country?.country || "—"}</td><td>{pct(row.import_country_top_share)}</td></tr>)}</tbody>
            </table>
          ) : (
            <table className="trade-table"><thead><tr><th>País</th><th>Exportações</th><th>Importações</th><th>Saldo</th><th>Participação nas importações</th></tr></thead>
              <tbody>{resultados.map((row, index) => <tr key={`${row.country_code}-${index}`}><td><strong>{row.country || "—"}</strong><div className="muted mono">{row.country_code || ""}</div></td><td className="mono">{usd(row.exports_fob)}</td><td className="mono">{usd(row.imports_fob)}</td><td className={`mono ${Number(row.balance_fob) < 0 ? "saldo-negativo" : "saldo-positivo"}`}>{usd(row.balance_fob)}</td><td>{pct(row.import_share)}</td></tr>)}</tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  );
}
