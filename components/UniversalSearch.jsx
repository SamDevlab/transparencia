"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

function normalizar(valor) {
  return String(valor ?? "").normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase().trim();
}

const ORDEM = ["Pessoas", "Processos", "Fornecedores", "Órgãos", "Contratos", "Credores", "Receitas"];

export default function UniversalSearch() {
  const [dados, setDados] = useState(null);
  const [consulta, setConsulta] = useState("");
  const [historico, setHistorico] = useState([]);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    setConsulta(params.get("q") || params.get("busca") || "");
    try {
      setHistorico(JSON.parse(localStorage.getItem("transparencia_buscas") || "[]"));
    } catch {
      setHistorico([]);
    }
    fetch("/data/search.json")
      .then((resposta) => resposta.json())
      .then((payload) => setDados(payload.rows ?? []))
      .catch(() => setDados([]));
  }, []);

  function atualizarConsulta(valor) {
    setConsulta(valor);
    const url = new URL(window.location.href);
    if (valor) url.searchParams.set("q", valor);
    else url.searchParams.delete("q");
    window.history.replaceState({}, "", url);
  }

  function registrar(valor) {
    const texto = valor.trim();
    if (texto.length < 2) return;
    const novo = [texto, ...historico.filter((item) => normalizar(item) !== normalizar(texto))].slice(0, 6);
    setHistorico(novo);
    try { localStorage.setItem("transparencia_buscas", JSON.stringify(novo)); } catch {}
  }

  const resultados = useMemo(() => {
    if (!dados) return [];
    const termo = normalizar(consulta);
    if (termo.length < 2) return [];
    return dados
      .filter((item) => String(item.termos ?? "").includes(termo))
      .sort((a, b) => {
        const aTexto = normalizar(`${a.titulo} ${a.detalhe}`);
        const bTexto = normalizar(`${b.titulo} ${b.detalhe}`);
        const aExato = aTexto === termo ? 2 : aTexto.startsWith(termo) ? 1 : 0;
        const bExato = bTexto === termo ? 2 : bTexto.startsWith(termo) ? 1 : 0;
        return bExato - aExato;
      })
      .slice(0, 120);
  }, [dados, consulta]);

  const grupos = useMemo(() => {
    const map = new Map();
    for (const item of resultados) {
      const grupo = item.grupo || item.tipo || "Outros";
      const list = map.get(grupo) ?? [];
      list.push(item);
      map.set(grupo, list);
    }
    return [...map.entries()].sort((a, b) => {
      const ai = ORDEM.indexOf(a[0]);
      const bi = ORDEM.indexOf(b[0]);
      return (ai < 0 ? 99 : ai) - (bi < 0 ? 99 : bi);
    });
  }, [resultados]);

  return (
    <div>
      <div className="busca-grande">
        <span aria-hidden="true">⌕</span>
        <input
          autoFocus
          value={consulta}
          onChange={(e) => atualizarConsulta(e.target.value)}
          onKeyDown={(e) => { if (e.key === "Enter") registrar(consulta); }}
          placeholder="Digite pessoa, empresa, CNPJ, processo, contrato, órgão ou código…"
          aria-label="Buscar em todos os dados publicados"
        />
        {consulta && <button type="button" onClick={() => atualizarConsulta("")}>Limpar</button>}
      </div>

      {!consulta && historico.length > 0 && (
        <div className="buscas-recentes">
          <strong>Buscas recentes</strong>
          <div>{historico.map((item) => <button key={item} onClick={() => atualizarConsulta(item)}>{item}</button>)}</div>
        </div>
      )}

      {consulta.trim().length < 2 && <div className="consulta-orientacao">Digite pelo menos 2 caracteres. Você não precisa saber em qual tela o dado está.</div>}
      {dados && consulta.trim().length >= 2 && resultados.length === 0 && <div className="card empty">Nenhum resultado encontrado para “{consulta}”. Tente parte do nome ou número.</div>}

      <div className="grupos-busca">
        {grupos.map(([grupo, items]) => (
          <section className="grupo-busca" key={grupo}>
            <header><h2>{grupo}</h2><span>{items.length} resultado(s)</span></header>
            <div className="grupo-resultados">
              {items.slice(0, 20).map((item, index) => (
                <Link href={item.href} key={`${item.href}-${index}`} className="resultado-universal" onClick={() => registrar(consulta)}>
                  <span className="consulta-tipo">{item.tipo}</span>
                  <strong>{item.titulo}</strong>
                  <p>{item.detalhe}</p>
                  {item.referencia && <small>{item.referencia}</small>}
                </Link>
              ))}
            </div>
            {items.length > 20 && <p className="muted">Mostrando os 20 primeiros deste grupo. Refine a busca para reduzir os resultados.</p>}
          </section>
        ))}
      </div>
    </div>
  );
}
