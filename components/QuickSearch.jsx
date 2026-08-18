"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useMemo, useRef, useState } from "react";

function normalizar(valor) {
  return String(valor ?? "").normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase().trim();
}

export default function QuickSearch() {
  const router = useRouter();
  const [dados, setDados] = useState(null);
  const [consulta, setConsulta] = useState("");
  const [aberto, setAberto] = useState(false);
  const carregando = useRef(false);

  async function garantirDados() {
    if (dados || carregando.current) return;
    carregando.current = true;
    try {
      const resposta = await fetch("/data/search.json");
      if (!resposta.ok) throw new Error("Falha ao carregar a busca");
      const payload = await resposta.json();
      setDados(payload.rows ?? []);
    } catch {
      setDados([]);
    } finally {
      carregando.current = false;
    }
  }

  const resultados = useMemo(() => {
    const termo = normalizar(consulta);
    if (!dados || termo.length < 2) return [];
    return dados
      .filter((item) => String(item.termos ?? "").includes(termo))
      .sort((a, b) => {
        const aTexto = normalizar(`${a.titulo} ${a.detalhe}`);
        const bTexto = normalizar(`${b.titulo} ${b.detalhe}`);
        const aInicio = aTexto.startsWith(termo) ? 1 : 0;
        const bInicio = bTexto.startsWith(termo) ? 1 : 0;
        return bInicio - aInicio;
      })
      .slice(0, 10);
  }, [dados, consulta]);

  return (
    <div className="consulta-rapida">
      <div className="consulta-campo">
        <span aria-hidden="true">⌕</span>
        <input
          value={consulta}
          onFocus={() => { garantirDados(); setAberto(true); }}
          onChange={(evento) => { setConsulta(evento.target.value); garantirDados(); setAberto(true); }}
          onKeyDown={(evento) => {
            if (evento.key === "Escape") setAberto(false);
            if (evento.key === "Enter" && consulta.trim().length >= 2) {
              setAberto(false);
              router.push(`/buscar?q=${encodeURIComponent(consulta.trim())}`);
            }
          }}
          placeholder="Pessoa, CNPJ, processo, contrato, órgão…"
          aria-label="Consulta rápida"
        />
        {consulta && <button type="button" onClick={() => setConsulta("")} aria-label="Limpar busca">×</button>}
      </div>

      {aberto && consulta.trim().length >= 2 && (
        <div className="consulta-resultados">
          {!dados && <div className="consulta-vazio">Carregando consulta…</div>}
          {dados && resultados.length === 0 && <div className="consulta-vazio">Nenhum resultado encontrado.</div>}
          {resultados.map((item, indice) => (
            <Link href={item.href} className="consulta-item" key={`${item.tipo}-${item.href}-${indice}`} onClick={() => setAberto(false)}>
              <span className="consulta-tipo">{item.grupo || item.tipo} · {item.tipo}</span>
              <strong>{item.titulo}</strong>
              <small>{item.detalhe}</small>
              {item.referencia && <em>{item.referencia}</em>}
            </Link>
          ))}
          {dados && (
            <Link className="consulta-todos" href={`/buscar?q=${encodeURIComponent(consulta.trim())}`} onClick={() => setAberto(false)}>
              Ver todos os resultados →
            </Link>
          )}
        </div>
      )}
    </div>
  );
}
