import MoneyFlowExplorer from "../../components/MoneyFlowExplorer";
import { brl, loadWebData, parseBrlText } from "../../lib/web-data";

export const metadata = { title: "Para onde foi o dinheiro?" };

export default function DinheiroPage() {
  const data = loadWebData("money.json");
  const receita = parseBrlText(data.financeSummary?.revenue_totalizer?.Realizado);
  const pago = parseBrlText(data.financeSummary?.expense_totalizer?.Pago);
  const empenhado = parseBrlText(data.financeSummary?.expense_totalizer?.Empenhado);
  const liquidado = parseBrlText(data.financeSummary?.expense_totalizer?.Liquidado);

  return (
    <>
      <section className="page-hero"><div className="shell"><span className="eyebrow">Para onde foi o dinheiro?</span><h1>Comece pelo destino do recurso, não pela tabela contábil.</h1><p>Veja o total arrecadado e pago e depois navegue de órgão para processo, contrato e fornecedor quando existir relação exata entre as fontes.</p></div></section>

      <section className="section compacto"><div className="shell grid grid-4"><div className="card stat accent"><span className="stat-label">Receita realizada</span><div><span className="stat-value">{brl(receita, { compact: true })}</span><div className="stat-meta">arrecadação no período</div></div></div><div className="card stat"><span className="stat-label">Empenhado</span><div><span className="stat-value">{brl(empenhado, { compact: true })}</span><div className="stat-meta">compromisso orçamentário</div></div></div><div className="card stat"><span className="stat-label">Liquidado</span><div><span className="stat-value">{brl(liquidado, { compact: true })}</span><div className="stat-meta">direito do credor reconhecido</div></div></div><div className="card stat blue"><span className="stat-label">Pago</span><div><span className="stat-value">{brl(pago, { compact: true })}</span><div className="stat-meta">desembolso registrado</div></div></div></div></section>

      <section className="section"><div className="shell grid grid-2"><div className="card panel"><div className="panel-title"><h3>Despesa paga por função</h3><span>agregado oficial</span></div><div className="bar-list">{data.expenseFunctions.slice(0, 10).map((row) => { const max = Number(data.expenseFunctions[0]?.paid_value || 1); return <div className="bar-row" key={`${row.dimension_code}-${row.dimension_name}`}><div className="bar-meta"><span>{row.dimension_name}</span><strong>{brl(row.paid_value, { compact: true })}</strong></div><div className="bar-track"><div className="bar-fill" style={{ width: `${Math.max(2, Number(row.paid_value || 0) / max * 100)}%` }} /></div></div>; })}</div></div><div className="card panel"><div className="panel-title"><h3>O que pode ser ligado diretamente</h3><span>regra de evidência</span></div><p className="muted">Despesa por função e execução por unidade são totais agregados. O sistema só desenha caminho até contrato e fornecedor quando a própria fonte contém a relação ou quando o número do processo coincide exatamente entre Prefeitura e PNCP.</p><div className="notice"><span>✓</span><div>Isso evita transformar proximidade de nomes em uma relação que a documentação não comprovou.</div></div></div></div></section>

      <section className="section"><div className="shell"><div className="section-head enxuto"><div><span className="eyebrow">Navegação</span><h2>Do órgão ao fornecedor</h2></div><p>Escolha uma secretaria ou órgão e veja as relações comprovadas no recorte.</p></div><MoneyFlowExplorer /><div className="results-line"><span>{data.coverageNote}</span></div></div></section>
    </>
  );
}
