import { notFound } from "next/navigation";
import Link from "next/link";
import { brl, integer, loadWebData, dateBR } from "../../../lib/web-data";

export default async function OrgaoPage({ params }) {
  const { id } = await params;
  const data = loadWebData("agencies.json");
  const agency = data.rows.find((row) => row.id === id);
  if (!agency) notFound();

  return (
    <>
      <section className="page-hero"><div className="shell"><span className="eyebrow">Órgão público</span><h1>{agency.nome}</h1><p>Perfil construído com as aquisições publicadas pela Prefeitura no recorte auditado.</p><div className="kicker-row">{agency.sigla && <span className="badge green">{agency.sigla}</span>}<span className="badge">{integer(agency.quantidade)} registros</span></div></div></section>

      <section className="section compacto"><div className="shell grid grid-4"><div className="card stat accent"><span className="stat-label">Valor declarado</span><div><span className="stat-value">{brl(agency.valorDeclarado, { compact: true })}</span><div className="stat-meta">soma das aquisições do recorte</div></div></div><div className="card stat"><span className="stat-label">Aquisições</span><div><span className="stat-value">{integer(agency.quantidade)}</span><div className="stat-meta">registros municipais</div></div></div><div className="card stat"><span className="stat-label">Valor médio</span><div><span className="stat-value">{brl(agency.valorMedio, { compact: true })}</span><div className="stat-meta">média descritiva</div></div></div><div className="card stat blue"><span className="stat-label">Contratação direta</span><div><span className="stat-value">{Math.round(agency.percentualContratacaoDireta * 100)}%</span><div className="stat-meta">dispensa + inexigibilidade por quantidade</div></div></div></div></section>

      <section className="section"><div className="shell grid grid-2"><div className="card panel"><div className="panel-title"><h3>Formas de contratação</h3><span>quantidade / valor</span></div><div className="method-list simples">{agency.tipos.map((row) => <div className="method-item" key={row.tipo}><strong>{row.tipo}</strong><p>{integer(row.quantidade)} registro(s) · {brl(row.valor)}</p></div>)}</div></div><div className="card panel"><div className="panel-title"><h3>Como interpretar</h3><span>sem inferência indevida</span></div><p className="muted">O percentual de contratação direta descreve a modalidade publicada. Ele não é um índice de irregularidade. Para avaliar um processo é necessário abrir o registro, o fundamento e os documentos da fonte.</p><Link className="button" href={`/licitacoes?orgao=${encodeURIComponent(agency.nome)}`}>Abrir todas as aquisições deste órgão →</Link></div></div></section>

      <section className="section"><div className="shell"><div className="section-head enxuto"><div><span className="eyebrow">Processos</span><h2>Maiores valores do órgão</h2></div><Link className="button" href="/comparar">Comparar com outro órgão</Link></div><div className="card table-card"><div className="table-wrap"><table><thead><tr><th>Referência</th><th>Objeto</th><th>Tipo</th><th>Publicação</th><th>Valor</th><th></th></tr></thead><tbody>{agency.maiores.map((row) => <tr key={row.id}><td className="mono"><strong>{row.processo || row.numero || "—"}</strong></td><td className="object-cell">{row.objeto || "—"}</td><td>{row.tipo || "—"}</td><td>{dateBR(row.publicadoEm)}</td><td><strong className="mono">{brl(row.valor)}</strong></td><td><Link className="button" href={`/processos/${encodeURIComponent(row.id)}`}>Detalhes →</Link></td></tr>)}</tbody></table></div></div></div></section>

      <section className="section compacto"><div className="shell"><Link className="button" href="/orgaos">← Voltar aos órgãos</Link></div></section>
    </>
  );
}
