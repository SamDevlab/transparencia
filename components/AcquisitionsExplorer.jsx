"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

const PAGE_SIZE = 25;

function normalize(value) {
  return String(value ?? "").normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase();
}

function brl(value) {
  return new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" }).format(Number(value ?? 0));
}

function dateBR(value) {
  if (!value) return "—";
  const parts = String(value).slice(0, 10).split("-");
  return parts.length === 3 ? `${parts[2]}/${parts[1]}/${parts[0]}` : value;
}

function badgeClass(type) {
  const normalized = normalize(type);
  if (normalized.includes("licit")) return "badge green";
  if (normalized.includes("dispensa") || normalized.includes("inexig")) return "badge yellow";
  return "badge";
}

function Copiar({ valor }) {
  const [copiado, setCopiado] = useState(false);
  if (!valor) return null;
  return (
    <button type="button" className="copiar" onClick={async () => {
      try {
        await navigator.clipboard.writeText(String(valor));
        setCopiado(true);
        setTimeout(() => setCopiado(false), 1300);
      } catch { setCopiado(false); }
    }}>{copiado ? "Copiado" : "Copiar"}</button>
  );
}

export default function AcquisitionsExplorer() {
  const [data, setData] = useState(null);
  const [query, setQuery] = useState("");
  const [type, setType] = useState("todos");
  const [agency, setAgency] = useState("todos");
  const [sort, setSort] = useState("valor_desc");
  const [focus, setFocus] = useState("todos");
  const [page, setPage] = useState(1);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    setQuery(params.get("busca") || "");
    setAgency(params.get("orgao") || "todos");
    setFocus(params.get("filtro") || "todos");
    fetch("/data/acquisitions.json")
      .then((response) => {
        if (!response.ok) throw new Error("Falha ao carregar aquisições");
        return response.json();
      })
      .then(setData)
      .catch(() => setData({ rows: [], error: true }));
  }, []);

  const types = useMemo(() => [...new Set((data?.rows ?? []).map((row) => row.tipo).filter(Boolean))].sort((a, b) => a.localeCompare(b, "pt-BR")), [data]);
  const agencies = useMemo(() => [...new Set((data?.rows ?? []).map((row) => row.orgao).filter(Boolean))].sort((a, b) => a.localeCompare(b, "pt-BR")), [data]);

  const filtered = useMemo(() => {
    if (!data) return [];
    const needle = normalize(query.trim());
    const rows = data.rows.filter((row) => {
      if (type !== "todos" && row.tipo !== type) return false;
      if (agency !== "todos" && row.orgao !== agency) return false;
      const direct = normalize(row.tipo).includes("dispensa") || normalize(row.tipo).includes("inexig");
      if (focus === "direta" && !direct) return false;
      if (focus === "milhao" && Number(row.valor ?? 0) < 1_000_000) return false;
      if (focus === "dez_milhoes" && Number(row.valor ?? 0) < 10_000_000) return false;
      if (!needle) return true;
      return normalize([row.objeto, row.orgao, row.unidade, row.processo, row.aviso, row.numero, row.modalidade, row.tipo, row.fundamento].join(" ")).includes(needle);
    });
    return rows.slice().sort((a, b) => {
      if (sort === "valor_asc") return Number(a.valor ?? 0) - Number(b.valor ?? 0);
      if (sort === "data_desc") return String(b.publicadoEm ?? "").localeCompare(String(a.publicadoEm ?? ""));
      if (sort === "data_asc") return String(a.publicadoEm ?? "").localeCompare(String(b.publicadoEm ?? ""));
      return Number(b.valor ?? 0) - Number(a.valor ?? 0);
    });
  }, [data, query, type, agency, sort, focus]);

  useEffect(() => setPage(1), [query, type, agency, sort, focus]);

  if (!data) return <div className="card loading">Carregando aquisições publicadas…</div>;
  if (data.error) return <div className="card empty">Não foi possível carregar os dados desta publicação.</div>;

  const pages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  const safePage = Math.min(page, pages);
  const visible = filtered.slice((safePage - 1) * PAGE_SIZE, safePage * PAGE_SIZE);

  return (
    <div>
      <div className="filtros-rapidos">
        <button className={focus === "todos" ? "ativo" : ""} onClick={() => setFocus("todos")}>Todos</button>
        <button className={focus === "direta" ? "ativo" : ""} onClick={() => setFocus("direta")}>Dispensa ou inexigibilidade</button>
        <button className={focus === "milhao" ? "ativo" : ""} onClick={() => setFocus("milhao")}>Acima de R$ 1 milhão</button>
        <button className={focus === "dez_milhoes" ? "ativo" : ""} onClick={() => setFocus("dez_milhoes")}>Acima de R$ 10 milhões</button>
      </div>

      <div className="toolbar">
        <input className="input" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Buscar objeto, processo, número ou órgão…" aria-label="Buscar aquisições" />
        <select className="select" value={type} onChange={(event) => setType(event.target.value)} aria-label="Filtrar por tipo"><option value="todos">Todos os tipos</option>{types.map((item) => <option key={item} value={item}>{item}</option>)}</select>
        <select className="select" value={agency} onChange={(event) => setAgency(event.target.value)} aria-label="Filtrar por órgão"><option value="todos">Todos os órgãos</option>{agencies.map((item) => <option key={item} value={item}>{item}</option>)}</select>
      </div>

      <div className="results-line"><span><strong>{filtered.length.toLocaleString("pt-BR")}</strong> registros encontrados</span><select className="select" style={{ width: 210 }} value={sort} onChange={(event) => setSort(event.target.value)} aria-label="Ordenar resultados"><option value="valor_desc">Maior valor</option><option value="valor_asc">Menor valor</option><option value="data_desc">Mais recentes</option><option value="data_asc">Mais antigos</option></select></div>

      <div className="card table-card"><div className="table-wrap"><table><thead><tr><th>Órgão</th><th>Objeto</th><th>Referências</th><th>Tipo</th><th>Publicação</th><th>Valor</th><th></th></tr></thead><tbody>{visible.map((row) => <tr key={row.id}><td><strong>{row.orgao || "—"}</strong><div className="muted">{row.unidade || ""}</div></td><td className="object-cell">{row.objeto || "—"}</td><td><div className="referencia-lista">{row.processo && <div className="referencia-linha"><b>Processo:</b><span className="mono">{row.processo}</span><Copiar valor={row.processo} /></div>}{row.numero && <div className="referencia-linha"><b>Aquisição:</b><span className="mono">{row.numero}</span><Copiar valor={row.numero} /></div>}{row.aviso && <div className="referencia-linha"><b>Aviso:</b><span className="mono">{row.aviso}</span><Copiar valor={row.aviso} /></div>}{!row.processo && !row.numero && !row.aviso && <span className="muted">Sem número exibido</span>}</div></td><td><span className={badgeClass(row.tipo)}>{row.tipo || row.modalidade || "—"}</span></td><td className="mono">{dateBR(row.publicadoEm)}</td><td><strong className="mono">{brl(row.valor)}</strong></td><td><div className="acoes-tabela"><Link className="button primary" href={`/processos/${encodeURIComponent(row.id)}`}>Detalhes</Link><a className="button discreto" href={row.fonte} target="_blank" rel="noreferrer">Fonte ↗</a></div></td></tr>)}</tbody></table></div>{!visible.length && <div className="empty">Nenhum registro corresponde aos filtros.</div>}</div>

      <div className="pagination"><button disabled={safePage <= 1} onClick={() => setPage((current) => Math.max(1, current - 1))}>← Anterior</button><span className="muted">Página {safePage} de {pages}</span><button disabled={safePage >= pages} onClick={() => setPage((current) => Math.min(pages, current + 1))}>Próxima →</button></div>
    </div>
  );
}
