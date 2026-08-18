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
    contract.publicadoEm ? { data: contract.publicadoEm, tipo: "Publicação", titulo: `${contract.numero || "Contrato"} publicado no PNCP`, fonte: contract.fonte } : null,
    contract.vigenciaFim ? { data: contract.vigenciaFim, tipo: "Vigência", titulo: `${contract.numero || "Contrato"} — fim previsto`, fonte: contract.fonte } : null,
  ]).filter(Boolean).sort((a, b) => String(a.data).localeCompare(String(b.data)));

  return (
    <>
      <section className="page-hero">
        <div className="shell">
          <span className="eyebrow">Fornecedor</span>
          <h1>{supplier.nome}</h1>
          <p className="mono">{supplier.documento || "Documento não informado"}</p>
          <div className="kicker-row"><span className="badge green">{supplier.quantidadeContratos} contrato(s) PNCP</span><span className="badge">{brl(supplier.valorGlobal)} em valor global no recorte</span></div>
        </div>
      </section>

      <section className="section compacto">
        <div className="shell grid grid-3">
          <div className="card stat accent"><span className="stat-label">Valor global</span><div><span className="stat-value">{brl(supplier.valorGlobal, { compact: true })}</span><div className="stat-meta">soma dos contratos PNCP preservados</div></div></div>
          <div className="card stat"><span className="stat-label">Contratos</span><div><span className="stat-value">{supplier.quantidadeContratos}</span><div className="stat-meta">no recorte complementar</div></div></div>
          <div className="card stat blue"><span className="stat-label">Unidades contratantes</span><div><span className="stat-value">{supplier.unidades.length}</span><div className="stat-meta">unidades distintas no PNCP</div></div></div>
        </div>
      </section>

      <section className="section">
        <div className="shell">
          <div className="section-head enxuto"><div><span className="eyebrow">Relações</span><h2>Como este fornecedor aparece na base</h2></div><p>As relações abaixo vêm do próprio contrato PNCP; não são inferidas por semelhança de nome.</p></div>
          {supplier.contratos.slice(0, 4).map((contract) => (
            <RelationshipGraph key={contract.id} nodes={[
              { tipo: "Unidade", titulo: contract.unidade || "Não informada" },
              { tipo: "Processo", titulo: contract.processo || "Sem número", href: contract.processo ? `/buscar?q=${encodeURIComponent(contract.processo)}` : undefined },
              { tipo: "Contrato", titulo: contract.numero || "PNCP", detalhe: brl(contract.valorGlobal) },
              { tipo: "Fornecedor", titulo: supplier.nome },
            ]} />
          ))}
        </div>
      </section>

      <section className="section" id="contratos">
        <div className="shell">
          <div className="section-head enxuto"><div><span className="eyebrow">Contratos</span><h2>Contratos publicados no PNCP</h2></div><p>Valores contratuais, não equivalentes automaticamente a pagamentos.</p></div>
          <div className="card table-card"><div className="table-wrap"><table><thead><tr><th>Contrato</th><th>Processo</th><th>Unidade</th><th>Objeto</th><th>Valor global</th><th>Vigência</th></tr></thead><tbody>{supplier.contratos.map((contract) => <tr key={contract.id}><td><a href={contract.fonte} target="_blank" rel="noreferrer"><strong>{contract.numero || "—"}</strong> ↗</a></td><td className="mono">{contract.processo || "—"}</td><td>{contract.unidade || "—"}</td><td className="object-cell">{contract.objeto || "—"}</td><td><strong className="mono">{brl(contract.valorGlobal)}</strong></td><td>{dateBR(contract.vigenciaInicio)} → {dateBR(contract.vigenciaFim)}</td></tr>)}</tbody></table></div></div>
          <SourceDetails source={supplier.contratos[0]?.fonte} note={data.coverageNote} method="Fornecedor, documento, unidade e valores são lidos diretamente dos registros de contrato preservados do PNCP." />
        </div>
      </section>

      <section className="section"><div className="shell"><div className="section-head enxuto"><div><span className="eyebrow">Linha do tempo</span><h2>Publicações e vigências</h2></div></div><Timeline items={timeline} /></div></section>

      <section className="section compacto"><div className="shell"><div className="notice warn"><span>!</span><div><strong>Interpretação:</strong> o fato de uma empresa ter vários contratos ou concentrar valor em uma unidade serve para orientar consulta documental; sozinho, isso não prova favorecimento, sobrepreço ou irregularidade.</div></div><div style={{ marginTop: 16 }}><Link className="button" href="/fornecedores">← Voltar aos fornecedores</Link></div></div></section>
    </>
  );
}
