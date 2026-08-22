"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

function brl(value, compact = false) {
  return new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL", notation: compact ? "compact" : "standard", maximumFractionDigits: compact ? 1 : 2 }).format(Number(value ?? 0));
}

export default function MoneyFlowExplorer() {
  const [data, setData] = useState(null);
  const [agencyId, setAgencyId] = useState("");

  useEffect(() => {
    fetch("/data/money.json").then((r) => r.json()).then((payload) => {
      setData(payload);
      setAgencyId(payload.agencies?.[0]?.id || "");
    }).catch(() => setData({ error: true }));
  }, []);

  const agency = useMemo(() => data?.agencies?.find((row) => row.id === agencyId), [data, agencyId]);
  const links = useMemo(() => {
    if (!data || !agency) return [];
    return data.exactCrossSourceLinks.filter((row) => row.orgao === agency.nome).slice(0, 12);
  }, [data, agency]);

  if (!data) return <div className="card loading">Carregando fluxo dos dados…</div>;
  if (data.error) return <div className="card empty">Não foi possível carregar este recorte.</div>;

  return (
    <div>
      <div className="seletor-fluxo">
        <label htmlFor="orgao-fluxo">Escolha um órgão</label>
        <select id="orgao-fluxo" className="select" value={agencyId} onChange={(e) => setAgencyId(e.target.value)}>
          {data.agencies.map((row) => <option key={row.id} value={row.id}>{row.nome}</option>)}
        </select>
      </div>

      {agency && <>
        <div className="fluxo-resumo">
          <Link href={`/orgaos/${agency.id}`} className="fluxo-no principal"><span>Órgão</span><strong>{agency.nome}</strong><small>Abrir perfil →</small></Link>
          <div className="fluxo-conector">→</div>
          <div className="fluxo-no"><span>Aquisições publicadas</span><strong>{agency.quantidade.toLocaleString("pt-BR")}</strong><small>{brl(agency.valorDeclarado, true)} em valor declarado</small></div>
          <div className="fluxo-conector">→</div>
          <div className="fluxo-no"><span>Vínculos exatos com contratos</span><strong>{links.length}</strong><small>mesmo número oficial de processo</small></div>
        </div>

        {links.length > 0 ? <div className="relacoes-lista">{links.map((link) => link.contratos.map((contract, index) => <article className="relacao-dinheiro" key={`${link.processoId}-${contract.numero}-${index}`}><div className="relacao-coluna"><span>Processo</span><Link href={`/processos/${encodeURIComponent(link.processoId)}`}><strong className="mono">{link.processo || "—"}</strong></Link><small>{link.objeto}</small></div><div className="relacao-seta grande">→</div><div className="relacao-coluna"><span>Contrato municipal</span><strong>{contract.numero || "Contrato"}</strong><small>{brl(contract.valorGlobal)}</small></div><div className="relacao-seta grande">→</div><div className="relacao-coluna"><span>Fornecedor empresarial</span>{contract.documentoFornecedor ? <Link href={`/fornecedores/${encodeURIComponent(contract.documentoFornecedor)}`}><strong>{contract.fornecedor || "Empresa"}</strong><small className="mono">{contract.documentoFornecedor}</small></Link> : <><strong>Não publicado nesta relação</strong><small>Exigimos CNPJ estruturado e evidência exata para exibir fornecedor.</small></>}</div></article>))}</div> : <div className="notice warn"><span>!</span><div><strong>Nenhum vínculo exato exibido para este órgão.</strong> Isso não significa ausência de contratos. Significa apenas que, no recorte publicado, não houve coincidência exata do número oficial do processo entre aquisição e grade municipal de contratos.</div></div>}
      </>}
    </div>
  );
}
