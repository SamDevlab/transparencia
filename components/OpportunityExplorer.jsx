"use client";

import { useEffect, useMemo, useState } from "react";

function normalizar(valor) {
  return String(valor ?? "").normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase();
}

function usd(valor) {
  return new Intl.NumberFormat("pt-BR", { style: "currency", currency: "USD", notation: "compact", maximumFractionDigits: 1 }).format(Number(valor ?? 0));
}

function pct(valor) {
  if (valor == null) return "sem base comparável";
  return new Intl.NumberFormat("pt-BR", { style: "percent", maximumFractionDigits: 1 }).format(Number(valor));
}

const labels = {
  import_scale: "Escala das importações",
  trade_deficit: "Déficit comercial",
  import_growth: "Crescimento das importações",
  country_concentration: "Concentração por país",
  related_export_capacity: "Exportação relacionada no mesmo SH4",
};

export default function OpportunityExplorer() {
  const [dados, setDados] = useState(null);
  const [escopo, setEscopo] = useState("bahia");
  const [busca, setBusca] = useState("");
  const [faixa, setFaixa] = useState("todos");
  const [aberto, setAberto] = useState(null);

  useEffect(() => {
    fetch("/data/economy.json").then((r) => r.json()).then(setDados).catch(() => setDados({ available: false }));
  }, []);

  const rows = useMemo(() => {
    const origem = dados?.[escopo]?.opportunities ?? [];
    const termo = normalizar(busca);
    return origem.filter((row) => {
      if (faixa !== "todos" && row.screening?.label !== faixa) return false;
      if (!termo) return true;
      return normalizar(`${row.sh4} ${row.product} ${row.top_import_country?.country || ""}`).includes(termo);
    }).slice(0, 100);
  }, [dados, escopo, busca, faixa]);

  if (!dados) return <div className="card loading">Carregando triagem produtiva…</div>;
  if (!dados.available) return <div className="card empty">A triagem será preenchida automaticamente após o primeiro snapshot econômico do Comex Stat.</div>;

  return (
    <div>
      <div className="toolbar opportunity-toolbar">
        <input className="input" value={busca} onChange={(e) => setBusca(e.target.value)} placeholder="Buscar SH4 ou produto…" />
        <select className="select" value={escopo} onChange={(e) => setEscopo(e.target.value)}>
          <option value="bahia">Bahia</option>
          <option value="salvador">Empresas de Salvador</option>
        </select>
        <select className="select" value={faixa} onChange={(e) => setFaixa(e.target.value)}>
          <option value="todos">Todas as faixas</option>
          <option value="triagem_alta">Triagem alta</option>
          <option value="triagem_media">Triagem média</option>
          <option value="triagem_baixa">Triagem baixa</option>
        </select>
      </div>

      <div className="opportunity-list">
        {rows.map((row, index) => {
          const id = `${escopo}-${row.sh4 || index}`;
          const open = aberto === id;
          return <article className="opportunity-card" key={id}>
            <button type="button" className="opportunity-head" onClick={() => setAberto(open ? null : id)}>
              <div><span className="badge">SH4 {row.sh4 || "—"}</span><h3>{row.product}</h3><p>Importações {usd(row.imports_fob)} · Exportações {usd(row.exports_fob)} · crescimento {pct(row.import_growth_yoy)}</p></div>
              <div className="score-ring"><strong>{Number(row.screening?.score ?? 0).toFixed(0)}</strong><small>/100</small></div>
            </button>
            {open && <div className="opportunity-detail">
              <div className="notice warn"><span>!</span><div><strong>Triagem, não recomendação.</strong> A nota prioriza produtos para estudo. Não mede sozinha viabilidade industrial, custos, tecnologia, infraestrutura, licenciamento ou produtividade.</div></div>
              <div className="score-components">
                {Object.entries(row.screening?.components ?? {}).map(([key, value]) => <div className="score-component" key={key}><div><span>{labels[key] || key}</span><strong>{Number(value).toFixed(1)} pts</strong></div><div className="bar-track"><div className="bar-fill" style={{ width: `${Math.min(100, Number(value) / (key === "import_scale" ? 30 : key === "trade_deficit" ? 25 : 15) * 100)}%` }} /></div></div>)}
              </div>
              <div className="grid grid-3 triage-facts"><div><span>Saldo</span><strong className={Number(row.balance_fob) < 0 ? "saldo-negativo" : "saldo-positivo"}>{usd(row.balance_fob)}</strong></div><div><span>Principal origem</span><strong>{row.top_import_country?.country || "—"}</strong></div><div><span>Participação da principal origem</span><strong>{pct(row.import_country_top_share)}</strong></div></div>
            </div>}
          </article>;
        })}
      </div>
      {!rows.length && <div className="card empty">Nenhum produto corresponde aos filtros.</div>}
    </div>
  );
}
