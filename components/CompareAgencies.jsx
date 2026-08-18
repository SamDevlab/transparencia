"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

function brl(value, compact = false) {
  return new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL", notation: compact ? "compact" : "standard", maximumFractionDigits: compact ? 1 : 2 }).format(Number(value ?? 0));
}

function Metric({ label, a, b, format = (v) => v }) {
  const av = Number(a ?? 0);
  const bv = Number(b ?? 0);
  const max = Math.max(av, bv, 1);
  return (
    <div className="comparacao-metrica">
      <strong>{label}</strong>
      <div className="comparacao-linha"><span>{format(av)}</span><div><i style={{ width: `${Math.max(2, av / max * 100)}%` }} /></div></div>
      <div className="comparacao-linha"><span>{format(bv)}</span><div><i style={{ width: `${Math.max(2, bv / max * 100)}%` }} /></div></div>
    </div>
  );
}

export default function CompareAgencies() {
  const [data, setData] = useState(null);
  const [aId, setAId] = useState("");
  const [bId, setBId] = useState("");

  useEffect(() => {
    fetch("/data/comparisons.json").then((r) => r.json()).then((payload) => {
      setData(payload);
      setAId(payload.agencies?.[0]?.id || "");
      setBId(payload.agencies?.[1]?.id || payload.agencies?.[0]?.id || "");
    }).catch(() => setData({ error: true }));
  }, []);

  const a = useMemo(() => data?.agencies?.find((row) => row.id === aId), [data, aId]);
  const b = useMemo(() => data?.agencies?.find((row) => row.id === bId), [data, bId]);

  if (!data) return <div className="card loading">Carregando comparação…</div>;
  if (data.error) return <div className="card empty">Não foi possível carregar a comparação.</div>;

  return (
    <div>
      <div className="comparacao-seletores">
        <label>Órgão A<select className="select" value={aId} onChange={(e) => setAId(e.target.value)}>{data.agencies.map((row) => <option value={row.id} key={row.id}>{row.nome}</option>)}</select></label>
        <span>×</span>
        <label>Órgão B<select className="select" value={bId} onChange={(e) => setBId(e.target.value)}>{data.agencies.map((row) => <option value={row.id} key={row.id}>{row.nome}</option>)}</select></label>
      </div>
      {a && b && <>
        <div className="comparacao-nomes"><Link href={`/orgaos/${a.id}`}>{a.nome} →</Link><Link href={`/orgaos/${b.id}`}>{b.nome} →</Link></div>
        <div className="card panel comparacao-painel">
          <Metric label="Valor declarado em aquisições" a={a.valorDeclarado} b={b.valorDeclarado} format={(v) => brl(v, true)} />
          <Metric label="Quantidade de aquisições" a={a.quantidade} b={b.quantidade} format={(v) => Math.round(v).toLocaleString("pt-BR")} />
          <Metric label="Valor médio" a={a.valorMedio} b={b.valorMedio} format={(v) => brl(v, true)} />
          <Metric label="Contratação direta por quantidade" a={a.percentualContratacaoDireta * 100} b={b.percentualContratacaoDireta * 100} format={(v) => `${v.toFixed(1).replace(".", ",")}%`} />
        </div>
        <div className="notice warn" style={{ marginTop: 16 }}><span>!</span><div>Diferença entre órgãos não é sinônimo de eficiência ou irregularidade: secretarias têm missões, orçamentos e perfis de compra diferentes.</div></div>
      </>}
    </div>
  );
}
