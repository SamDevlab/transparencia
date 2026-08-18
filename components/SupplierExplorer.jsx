"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

function normalizar(valor) {
  return String(valor ?? "").normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase();
}

function brl(valor) {
  return new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" }).format(Number(valor ?? 0));
}

export default function SupplierExplorer() {
  const [dados, setDados] = useState(null);
  const [busca, setBusca] = useState("");
  const [minContratos, setMinContratos] = useState("1");
  const [ordem, setOrdem] = useState("valor");

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    setBusca(params.get("busca") || "");
    fetch("/data/suppliers.json")
      .then((r) => r.json())
      .then(setDados)
      .catch(() => setDados({ rows: [], error: true }));
  }, []);

  const resultados = useMemo(() => {
    if (!dados?.rows) return [];
    const termo = normalizar(busca.trim());
    const min = Number(minContratos || 1);
    return dados.rows
      .filter((row) => row.quantidadeContratos >= min)
      .filter((row) => !termo || normalizar(`${row.nome} ${row.documento} ${row.unidades.map((u) => u.nome).join(" ")}`).includes(termo))
      .slice()
      .sort((a, b) => ordem === "contratos" ? b.quantidadeContratos - a.quantidadeContratos : Number(b.valorGlobal) - Number(a.valorGlobal));
  }, [dados, busca, minContratos, ordem]);

  if (!dados) return <div className="card loading">Carregando fornecedores…</div>;
  if (dados.error) return <div className="card empty">Não foi possível carregar os fornecedores desta publicação.</div>;

  return (
    <div>
      <div className="toolbar fornecedores-filtros">
        <input className="input" value={busca} onChange={(e) => setBusca(e.target.value)} placeholder="Buscar empresa, CNPJ ou unidade…" />
        <select className="select" value={minContratos} onChange={(e) => setMinContratos(e.target.value)}>
          <option value="1">1 ou mais contratos</option>
          <option value="2">2 ou mais contratos</option>
          <option value="3">3 ou mais contratos</option>
        </select>
        <select className="select" value={ordem} onChange={(e) => setOrdem(e.target.value)}>
          <option value="valor">Maior valor contratual</option>
          <option value="contratos">Mais contratos</option>
        </select>
      </div>
      <div className="results-line"><span><strong>{resultados.length}</strong> fornecedores no recorte PNCP publicado</span><span>Fonte complementar aos dados municipais</span></div>
      <div className="fornecedores-grid">
        {resultados.map((row) => (
          <Link className="fornecedor-card" href={`/fornecedores/${encodeURIComponent(row.id)}`} key={row.id}>
            <span className="badge">{row.tipo || "Fornecedor"}</span>
            <h3>{row.nome}</h3>
            <p className="mono">{row.documento || "Documento não informado"}</p>
            <div className="fornecedor-metricas">
              <span><b>{row.quantidadeContratos}</b> contrato(s)</span>
              <span><b>{brl(row.valorGlobal)}</b> valor global</span>
            </div>
            <small>{row.unidades[0]?.nome || "Unidade não informada"}</small>
          </Link>
        ))}
      </div>
      {resultados.length === 0 && <div className="card empty">Nenhum fornecedor corresponde aos filtros.</div>}
    </div>
  );
}
