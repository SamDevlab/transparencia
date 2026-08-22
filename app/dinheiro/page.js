import Link from "next/link";
import MoneyFlowExplorer from "../../components/MoneyFlowExplorer";
import { brl, integer, loadWebData, parseBrlText } from "../../lib/web-data";

export const metadata = { title: "Para onde foi o dinheiro?" };

export default function DinheiroPage() {
  const data = loadWebData("money.json");
  const receita = parseBrlText(data.financeSummary?.revenue_totalizer?.Realizado);
  const pago = parseBrlText(data.financeSummary?.expense_totalizer?.Pago);
  const empenhado = parseBrlText(data.financeSummary?.expense_totalizer?.Empenhado);
  const liquidado = parseBrlText(data.financeSummary?.expense_totalizer?.Liquidado);
  const links = data.municipalDocumentaryLinks ?? {};

  return (
    <>
      <section className="page-hero"><div className="shell"><span className="eyebrow">Para onde foi o dinheiro?</span><h1>Comece pelos totais e avance apenas até onde a documentação permite.</h1><p>Receita, empenho, liquidação e pagamento permanecem como estágios contábeis separados. A camada documental municipal liga aquisição a contrato quando o número oficial do processo coincide exatamente; ela não inventa um vínculo do contrato até o pagamento.</p></div></section>

      <section className="section compacto"><div className="shell grid grid-4"><div className="card stat accent"><span className="stat-label">Receita realizada</span><div><span className="stat-value">{brl(receita, { compact: true })}</span><div className="stat-meta">arrecadação no período</div></div></div><div className="card stat"><span className="stat-label">Empenhado</span><div><span className="stat-value">{brl(empenhado, { compact: true })}</span><div className="stat-meta">compromisso orçamentário</div></div></div><div className="card stat"><span className="stat-label">Liquidado</span><div><span className="stat-value">{brl(liquidado, { compact: true })}</span><div className="stat-meta">direito do credor reconhecido</div></div></div><div className="card stat blue"><span className="stat-label">Pago</span><div><span className="stat-value">{brl(pago, { compact: true })}</span><div className="stat-meta">desembolso registrado</div></div></div></div></section>

      {links.processesWithExactContracts != null && <section className="section compacto"><div className="shell"><div className="section-head enxuto"><div><span className="eyebrow">Fio documental municipal</span><h2>Aquisição → contrato, por identificador exato</h2></div><Link className="button" href="/relacoes">Explorar relações →</Link></div><div className="grid grid-3"><div className="card stat"><span className="stat-label">Processos vinculados</span><div><span className="stat-value">{integer(links.processesWithExactContracts)}</span><div className="stat-meta">aquisições com contrato exato</div></div></div><div className="card stat"><span className="stat-label">Contratos únicos ligados</span><div><span className="stat-value">{integer(links.uniqueContractsLinked ?? 0)}</span><div className="stat-meta">na grade municipal publicada</div></div></div><div className="card stat accent"><span className="stat-label">Pares documentais</span><div><span className="stat-value">{integer(links.exactPairs ?? 0)}</span><div className="stat-meta">processo ↔ contrato</div></div></div></div><div className="notice" style={{ marginTop: 16 }}><span>i</span><div><strong>Não é um total de pagamentos rastreados.</strong> {data.municipalDocumentaryAccountingRule}</div></div></div></section>}

      <section className="section"><div className="shell grid grid-2"><div className="card panel"><div className="panel-title"><h3>Despesa paga por função</h3><span>agregado oficial</span></div><div className="bar-list">{data.expenseFunctions.slice(0, 10).map((row) => { const max = Number(data.expenseFunctions[0]?.paid_value || 1); return <div className="bar-row" key={`${row.dimension_code}-${row.dimension_name}`}><div className="bar-meta"><span>{row.dimension_name}</span><strong>{brl(row.paid_value, { compact: true })}</strong></div><div className="bar-track"><div className="bar-fill" style={{ width: `${Math.max(2, Number(row.paid_value || 0) / max * 100)}%` }} /></div></div>; })}</div></div><div className="card panel"><div className="panel-title"><h3>O que pode ser ligado diretamente</h3><span>regra de evidência</span></div><p className="muted">A aquisição municipal pode ser ligada ao contrato municipal pelo mesmo número oficial de processo. Totais por função e execução financeira continuam agregados e não são atribuídos a um contrato ou pessoa sem um identificador nominal da própria fonte.</p><div className="notice"><span>✓</span><div>{data.municipalDocumentaryIdentityRule || "Isso evita transformar proximidade de nomes em uma relação que a documentação não comprovou."}</div></div></div></div></section>

      <section className="section"><div className="shell"><div className="section-head enxuto"><div><span className="eyebrow">Navegação</span><h2>Do órgão aos documentos relacionados</h2></div><p>Escolha uma secretaria ou órgão e veja somente relações sustentadas pelas fontes publicadas.</p></div><MoneyFlowExplorer /><div className="results-line"><span>{data.coverageNote}</span><Link href="/relacoes">Abrir índice de relações exatas →</Link></div></div></section>
    </>
  );
}
