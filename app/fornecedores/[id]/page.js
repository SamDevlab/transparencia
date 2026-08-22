import { notFound } from "next/navigation";
import Link from "next/link";
import RelationshipGraph from "../../../components/RelationshipGraph";
import SourceDetails from "../../../components/SourceDetails";
import Timeline from "../../../components/Timeline";
import { brl, dateBR, loadWebData } from "../../../lib/web-data";

export default async function FornecedorPage({ params }) {
  const { id } = await params;
  const data = loadWebData("suppliers.json");
  const supplier = data.rows.find((row) => row.id === id);
  if (!supplier) notFound();

  const timeline = supplier.contratos.flatMap((contract) => [
    contract.assinadoEm ? { data: contract.assinadoEm, tipo: "Contrato", titulo: `${contract.numero || "Contrato"} assinado`, fonte: contract.fonte } : null,
    contract.publicadoEm ? { data: contract.publicadoEm, tipo: "Publicação", titulo: `${contract.numero || "Contrato"} publicado`, fonte: contract.fonte } : null,
    contract.vigenciaFim ? { data: contract.vigenciaFim, tipo: "Vigência", titulo: `${contract.numero || "Contrato"} — fim previsto`, fonte: contract.fonte } : null,
  ]).filter(Boolean).sort((a, b) => String(a.data).localeCompare(String(b.data)));
  const municipalLinked = supplier.contratos.filter((contract) => contract.supplierEvidence).length;
  const pncpOnly = supplier.contratos.length - municipalLinked;

  return (
    <>
      <section className="page-hero">
        <div className="shell">
          <span className="eyebrow">Fornecedor empresarial</span>
          <h1>{supplier.nome}</h1>
          <p className="mono">CNPJ {supplier.documento}</p>
          <div className="kicker-row"><span className="badge green">{supplier.quantidadeContratos} contrato(s)</span><span className="badge">{brl(supplier.valorGlobal)} em valor contratual no recorte</span>{municipalLinked > 0 && <span className="badge green">{municipalLinked} vínculo(s) municipal(is) exato(s)</span>}{pncpOnly > 0 && <span className="badge">{pncpOnly} registro(s) PNCP complementar(es)</span>}</div>
        </div>
      </section>

      <section className="section compacto">
        <div className="shell grid grid-3">
          <div className="card stat accent"><span className="stat-label">Valor contratual</span><div><span className="stat-value">{brl(supplier.valorGlobal, { compact: true })}</span><div className="stat-meta">soma dos contratos associados neste diretório</div></div></div>
          <div className="card stat"><span className="stat-label">Contratos</span><div><span className="stat-value">{supplier.quantidadeContratos}</span><div className="stat-meta">com CNPJ empresarial estruturado</div></div></div>
          <div className="card stat blue"><span className="stat-label">Unidades contratantes</span><div><span className="stat-value">{supplier.unidades.length}</span><div className="stat-meta">unidades distintas no recorte publicado</div></div></div>
        </div>
      </section>

      <section className="section">
        <div className="shell">
          <div className="section-head enxuto"><div><span className="eyebrow">Relações</span><h2>Como esta empresa foi ligada aos contratos</h2></div><p>O CNPJ vem de fonte estruturada. Similaridade de nome ou de objeto nunca cria vínculo.</p></div>
          {supplier.contratos.slice(0, 6).map((contract) => (
            <div key={contract.id} className="relacao-bloco">
              <RelationshipGraph nodes={[
                { tipo: "Unidade", titulo: contract.unidade || contract.orgao || "Não informada" },
                { tipo: "Processo", titulo: contract.processo || "Sem número", href: contract.processo ? `/buscar?q=${encodeURIComponent(contract.processo)}` : undefined },
                { tipo: "Contrato", titulo: contract.numero || contract.numeroSigef || "Contrato", detalhe: brl(contract.valorGlobal), href: `/contratos/${encodeURIComponent(contract.id)}` },
                { tipo: "Fornecedor", titulo: supplier.nome },
              ]} />
              {contract.supplierEvidence && <SourceDetails source={contract.supplierEvidence.sourceUrl || contract.fonte} title="Evidência do CNPJ" method={contract.supplierEvidence.rule} note={`Método: ${contract.supplierEvidence.method}. Processo: ${contract.supplierEvidence.processNumber || "—"}. O PNCP fornece o CNPJ empresarial; o contrato principal continua sendo o registro municipal.`} />}
            </div>
          ))}
        </div>
      </section>

      <section className="section" id="contratos">
        <div className="shell">
          <div className="section-head enxuto"><div><span className="eyebrow">Contratos</span><h2>Contratos associados à empresa</h2></div><p>Valores contratuais não equivalem automaticamente a empenhos, liquidações ou pagamentos.</p></div>
          <div className="card table-card"><div className="table-wrap"><table><thead><tr><th>Contrato</th><th>Processo</th><th>Unidade</th><th>Objeto</th><th>Valor</th><th>Vigência</th><th>Evidência</th></tr></thead><tbody>{supplier.contratos.map((contract) => <tr key={contract.id}><td><Link href={`/contratos/${encodeURIComponent(contract.id)}`}><strong>{contract.numero || contract.numeroSigef || "—"}</strong></Link>{contract.fonte && <div className="muted"><a href={contract.fonte} target="_blank" rel="noreferrer">fonte ↗</a></div>}</td><td className="mono">{contract.processo || "—"}</td><td>{contract.unidade || contract.orgao || "—"}</td><td className="object-cell">{contract.objeto || "—"}</td><td><strong className="mono">{brl(contract.valorGlobal)}</strong></td><td>{dateBR(contract.vigenciaInicio)} → {dateBR(contract.vigenciaFim)}</td><td>{contract.supplierEvidence ? "Prefeitura ↔ PNCP por identificadores exatos" : "PNCP complementar"}</td></tr>)}</tbody></table></div></div>
          <SourceDetails source={supplier.contratos[0]?.fonte} note={data.coverageNote} method="O diretório aceita somente CNPJ empresarial estruturado. Contratos municipais recebem fornecedor apenas por reconciliação documental exata; registros PNCP não ligados permanecem complementares." />
        </div>
      </section>

      <section className="section"><div className="shell"><div className="section-head enxuto"><div><span className="eyebrow">Linha do tempo</span><h2>Publicações e vigências</h2></div></div><Timeline items={timeline} /></div></section>

      <section className="section compacto"><div className="shell"><div className="notice warn"><span>!</span><div><strong>Interpretação:</strong> ter vários contratos ou concentrar valor em uma unidade é um dado descritivo para orientar consulta; sozinho, não prova favorecimento, sobrepreço ou irregularidade.</div></div><div style={{ marginTop: 16 }}><Link className="button" href="/fornecedores">← Voltar aos fornecedores</Link></div></div></section>
    </>
  );
}
