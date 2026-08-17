"use client";

import { useEffect, useMemo, useState } from "react";

function normalizar(valor) {
  return String(valor ?? "")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase();
}

function Copiar({ valor, rotulo }) {
  const [copiado, setCopiado] = useState(false);
  if (!valor) return null;
  return (
    <button
      type="button"
      className="copiar"
      onClick={async () => {
        try {
          await navigator.clipboard.writeText(valor);
          setCopiado(true);
          setTimeout(() => setCopiado(false), 1400);
        } catch {
          setCopiado(false);
        }
      }}
      title={`Copiar ${rotulo}`}
    >
      {copiado ? "Copiado" : "Copiar"}
    </button>
  );
}

export default function AgentsExplorer() {
  const [dados, setDados] = useState(null);
  const [busca, setBusca] = useState("");
  const [poder, setPoder] = useState("todos");
  const [funcao, setFuncao] = useState("todos");

  useEffect(() => {
    const parametros = new URLSearchParams(window.location.search);
    const buscaInicial = parametros.get("busca") || "";
    setBusca(buscaInicial);
    fetch("/data/agents.json")
      .then((resposta) => {
        if (!resposta.ok) throw new Error("Falha ao carregar agentes públicos");
        return resposta.json();
      })
      .then(setDados)
      .catch(() => setDados({ rows: [], error: true }));
  }, []);

  const funcoes = useMemo(() => {
    if (!dados?.rows) return [];
    const valores = new Set();
    for (const pessoa of dados.rows) {
      if (pessoa.cargo) valores.add(pessoa.cargo);
      for (const item of pessoa.funcoes ?? []) valores.add(item);
    }
    return [...valores].sort((a, b) => a.localeCompare(b, "pt-BR"));
  }, [dados]);

  const resultados = useMemo(() => {
    if (!dados?.rows) return [];
    const termo = normalizar(busca.trim());
    return dados.rows.filter((pessoa) => {
      if (poder !== "todos" && pessoa.poder !== poder) return false;
      if (funcao !== "todos" && pessoa.cargo !== funcao && !(pessoa.funcoes ?? []).includes(funcao)) return false;
      if (!termo) return true;
      return normalizar([
        pessoa.nome,
        pessoa.cargo,
        pessoa.orgao,
        pessoa.partido,
        pessoa.periodo,
        ...(pessoa.funcoes ?? []),
      ].join(" ")).includes(termo);
    });
  }, [dados, busca, poder, funcao]);

  if (!dados) return <div className="card loading">Carregando agentes públicos…</div>;
  if (dados.error) return <div className="card empty">Não foi possível carregar os agentes desta publicação.</div>;

  return (
    <div>
      <div className="toolbar agentes-filtros">
        <input
          className="input"
          value={busca}
          onChange={(evento) => setBusca(evento.target.value)}
          placeholder="Buscar nome, cargo, órgão ou partido…"
          aria-label="Buscar agente público"
        />
        <select className="select" value={poder} onChange={(evento) => setPoder(evento.target.value)} aria-label="Filtrar por poder">
          <option value="todos">Todos os poderes</option>
          <option value="Executivo">Executivo</option>
          <option value="Legislativo">Legislativo</option>
        </select>
        <select className="select" value={funcao} onChange={(evento) => setFuncao(evento.target.value)} aria-label="Filtrar por função">
          <option value="todos">Todas as funções</option>
          {funcoes.map((item) => <option value={item} key={item}>{item}</option>)}
        </select>
      </div>

      <div className="results-line">
        <span><strong>{resultados.length.toLocaleString("pt-BR")}</strong> agentes encontrados</span>
        <span>Dados de contato só aparecem quando publicados pela fonte oficial.</span>
      </div>

      <div className="agentes-grid">
        {resultados.map((pessoa) => (
          <article className="agente-card" key={pessoa.id}>
            <div className="agente-cabecalho">
              <div>
                <span className={`badge ${pessoa.poder === "Executivo" ? "green" : ""}`}>{pessoa.poder}</span>
                <h3>{pessoa.nome}</h3>
                <p>{pessoa.cargo}</p>
              </div>
              {pessoa.partido && <span className="partido">{pessoa.partido}</span>}
            </div>

            <dl className="agente-dados">
              <div><dt>Órgão</dt><dd>{pessoa.orgao || "—"}</dd></div>
              {pessoa.periodo && <div><dt>Período</dt><dd>{pessoa.periodo}</dd></div>}
              {(pessoa.funcoes ?? []).length > 0 && <div><dt>Função na Câmara</dt><dd>{pessoa.funcoes.join(" · ")}</dd></div>}
              {pessoa.telefone && <div><dt>Telefone</dt><dd><span className="mono">{pessoa.telefone}</span><Copiar valor={pessoa.telefone} rotulo="telefone" /></dd></div>}
              {pessoa.email && <div><dt>E-mail</dt><dd><span>{pessoa.email}</span><Copiar valor={pessoa.email} rotulo="e-mail" /></dd></div>}
            </dl>

            <div className="agente-acoes">
              <a className="button" href={pessoa.fonte} target="_blank" rel="noreferrer">Fonte oficial ↗</a>
              {pessoa.fonteComplementar && <a className="button discreto" href={pessoa.fonteComplementar} target="_blank" rel="noreferrer">Fonte complementar ↗</a>}
            </div>
          </article>
        ))}
      </div>

      {resultados.length === 0 && <div className="card empty">Nenhum agente corresponde aos filtros selecionados.</div>}
    </div>
  );
}
