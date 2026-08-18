import { notFound } from "next/navigation";
import Link from "next/link";
import SourceDetails from "../../../components/SourceDetails";
import Timeline from "../../../components/Timeline";
import { dateBR, loadWebData } from "../../../lib/web-data";

export default async function AgentePage({ params }) {
  const { id } = await params;
  const data = loadWebData("agents.json");
  const person = data.rows.find((row) => row.id === id);
  if (!person) notFound();

  const timeline = [
    person.periodo ? { data: String(person.periodo).match(/\d{4}/)?.[0] ? `${String(person.periodo).match(/\d{4}/)[0]}-01-01` : person.observadoEm, tipo: "Período", titulo: person.periodo } : null,
    person.observadoEm ? { data: person.observadoEm, tipo: "Verificação", titulo: "Cargo/cadastro verificado na fonte pública", fonte: person.fonte } : null,
  ].filter(Boolean);

  return (
    <>
      <section className="page-hero">
        <div className="shell">
          <span className="eyebrow">Agente público</span>
          <h1>{person.nome}</h1>
          <p>{person.cargo}{person.orgao ? ` · ${person.orgao}` : ""}</p>
          <div className="kicker-row"><span className={`badge ${person.poder === "Executivo" ? "green" : ""}`}>{person.poder}</span>{person.partido && <span className="badge">{person.partido}</span>}{person.periodo && <span className="badge">{person.periodo}</span>}</div>
        </div>
      </section>

      <section className="section compacto"><div className="shell perfil-duas-colunas"><div className="card panel"><div className="panel-title"><h3>Informações relevantes</h3><span>fonte pública</span></div><dl className="perfil-dados"><div><dt>Cargo</dt><dd>{person.cargo || "—"}</dd></div><div><dt>Órgão</dt><dd>{person.orgao || "—"}</dd></div>{person.partido && <div><dt>Partido</dt><dd>{person.partido}</dd></div>}{person.funcoes?.length > 0 && <div><dt>Funções adicionais</dt><dd>{person.funcoes.join(" · ")}</dd></div>}{person.telefone && <div><dt>Telefone oficial</dt><dd className="mono">{person.telefone}</dd></div>}{person.email && <div><dt>E-mail oficial</dt><dd>{person.email}</dd></div>}<div><dt>Verificado em</dt><dd>{dateBR(person.observadoEm)}</dd></div></dl></div><div className="card panel"><div className="panel-title"><h3>O que está ligado a esta pessoa?</h3><span>regra de evidência</span></div><p className="muted">Este perfil só exibe gasto individual quando uma fonte nominal vincula a despesa à pessoa. Gastos agregados da Prefeitura ou da Câmara não são rateados entre agentes.</p><div className="notice"><span>✓</span><div><strong>Sem atribuição artificial.</strong> Cargo, partido e contato podem vir do cadastro institucional; despesa exige documento nominal próprio.</div></div></div></div></section>

      <section className="section"><div className="shell"><div className="section-head enxuto"><div><span className="eyebrow">Linha do tempo</span><h2>Mandato, função e verificação</h2></div></div><Timeline items={timeline} /><SourceDetails source={person.fonte} secondary={person.fonteComplementar} observedAt={person.observadoEm} note={person.observacao} /></div></section>

      <section className="section compacto"><div className="shell"><Link className="button" href="/agentes">← Voltar aos agentes públicos</Link></div></section>
    </>
  );
}
