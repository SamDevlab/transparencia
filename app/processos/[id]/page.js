import { notFound } from "next/navigation";
import Link from "next/link";
import RelationshipGraph from "../../../components/RelationshipGraph";
import SourceDetails from "../../../components/SourceDetails";
import Timeline from "../../../components/Timeline";
import { brl, dateBR, loadWebData } from "../../../lib/web-data";

function agencyHref(name) {
  if (!name) return undefined;
  const slug = String(name)
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-|-$/g, "");
  return slug ? `/orgaos/${slug}` : undefined;
}

export default async function ProcessoPage({ params }) {
  const { id } = await params;
  const data = loadWebData("processes.json");
  const row = data.rows.find((item) => item.id === id);
  if (!row) notFound();

  return (
    <>
      <section className="page-hero"><div className="shell"><span className="eyebrow">Processo e aquisição</span><h1>{row.processo || row.numero || "Registro municipal"}</h1><p>{row.objeto || "Objeto não informado na base normalizada."}</p><div className="kicker-row"><span className="badge green">{row.tipo || "Aquisição"}</span>{row.modalidade && <span className="badge">{row.modalidade}</span>}<span className="badge">{brl(row.valor)}</span>{row.contratosExatos?.length > 0 && <span className="badge green">{row.contratosExatos.length} contrato(s) por processo exato</span>}</div></div></section>

      <section className="section compacto"><div className="shell perfil-duas-colunas"><div className="card panel"><div className="panel-title"><h3>Referências para consulta</h3><span>copie ou abra a fonte</span></div><dl className="perfil-dados"><div><dt>Processo</dt><dd className="mono">{row.processo || "—"}</dd></div><div><dt>Número da aquisição</dt><dd className="mono">{row.numero || "—"}</dd></div><div><dt>Aviso/modalidade no sistema</dt><dd className="mono">{row.aviso || "—"}</dd></div><div><dt>Órgão</dt><dd>{row.orgao || "—"}</dd></div><div><dt>Unidade</dt><dd>{row.unidade || "—"}</dd></div><div><dt>Publicação</dt><dd>{dateBR(row.publicadoEm)}</dd></div></dl></div><div className="card panel"><div className="panel-title"><h3>Valor e fundamento</h3><span>sem mudar a semântica da fonte</span></div><div className="stat-value mono">{brl(row.valor)}</div><p className="muted">O campo é exibido como valor declarado da aquisição porque a fonte não foi reinterpretada como homologação, pagamento ou valor final de contrato.</p>{row.fundamento && <p><strong>Fundamento informado:</strong> {row.fundamento}</p>}</div></div></section>

      {row.contratosExatos?.length > 0 && <section className="section"><div className="shell"><div className="section-head enxuto"><div><span className="eyebrow">Relação documental</span><h2>Contratos com o mesmo número oficial de processo</h2></div><p>Vínculo feito por igualdade exata após normalização documental; objeto, fornecedor e similaridade textual não criam relação.</p></div>{row.contratosExatos.map((contract, index) => {
        const municipal = contract.sourceSystem === "SALVADOR_TRANSPARENCIA_API_CONTRATOS";
        const sourceName = municipal ? "Transparência Salvador" : "PNCP";
        const nodes = [
          { tipo: "Órgão", titulo: row.orgao || "Prefeitura", href: agencyHref(row.orgao) },
          { tipo: "Processo", titulo: row.processo || "—" },
          { tipo: "Contrato", titulo: contract.numero || contract.numeroSigef || sourceName, detalhe: brl(contract.valorGlobal), href: `/contratos/${encodeURIComponent(contract.id)}` },
          contract.fornecedor ? { tipo: "Fornecedor", titulo: contract.fornecedor, href: contract.documentoFornecedor ? `/fornecedores/${encodeURIComponent(contract.documentoFornecedor)}` : undefined } : null,
        ].filter(Boolean);
        return <div key={`${contract.id}-${index}`} className="relacao-bloco"><RelationshipGraph nodes={nodes} /><SourceDetails source={contract.fonte} method="Correspondência exata do número do processo após normalização apenas documental; nenhuma semelhança textual cria o vínculo." note={`${sourceName} é a fonte do contrato exibido. Valor da aquisição, valor contratual, empenho, liquidação e pagamento permanecem conceitos separados.`} /></div>;
      })}</div></section>}

      <section className="section"><div className="shell"><div className="section-head enxuto"><div><span className="eyebrow">Linha do tempo</span><h2>Marcos publicados</h2></div></div><Timeline items={row.linhaDoTempo} /><SourceDetails source={row.fonte} title="Fonte da aquisição" note="Snapshot municipal preservado com proveniência no repositório." /></div></section>

      <section className="section compacto"><div className="shell"><Link className="button" href={`/licitacoes?busca=${encodeURIComponent(row.processo || row.numero || "")}`}>← Voltar à consulta de licitações</Link></div></section>
    </>
  );
}
