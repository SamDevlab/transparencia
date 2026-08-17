import FinanceExplorer from "../../components/FinanceExplorer";
import { brl, loadWebData, parseBrlText } from "../../lib/web-data";

export const metadata = { title: "Finanças" };

function Stat({ label, value, meta, tone = "" }) {
  return <div className={`card stat ${tone}`}><span className="stat-label">{label}</span><div><span className="stat-value mono">{value}</span><div className="stat-meta">{meta}</div></div></div>;
}

export default function FinancasPage() {
  const data = loadWebData("finance.json");
  const summary = data.summary;
  const realized = parseBrlText(summary.revenue_totalizer?.Realizado);
  const forecast = parseBrlText(summary.revenue_totalizer?.Previsto);
  const committed = parseBrlText(summary.expense_totalizer?.Empenhado);
  const liquidated = parseBrlText(summary.expense_totalizer?.Liquidado);
  const paid = parseBrlText(summary.expense_totalizer?.Pago);
  const maxFunction = Math.max(...data.expenseFunctions.map((row) => Number(row.paid_value ?? 0)), 1);

  return (
    <>
      <section className="page-hero"><div className="shell"><span className="eyebrow">Receita e despesa</span><h1>As contas da Prefeitura, com cada estágio separado.</h1><p>Empenhado, liquidado e pago aparecem separadamente. Os valores por credor são totais agregados do período, não pagamentos individuais.</p><div className="kicker-row"><span className="badge green">fonte oficial</span><span className="badge">01/01/2026–17/08/2026</span><span className="badge">integridade SHA-256 preservada</span></div></div></section>

      <section className="section compacto"><div className="shell"><div className="grid grid-4"><Stat label="Receita prevista" value={brl(forecast, { compact: true })} meta="previsão anual" /><Stat label="Receita realizada" value={brl(realized, { compact: true })} meta="arrecadação no período" tone="accent" /><Stat label="Despesa empenhada" value={brl(committed, { compact: true })} meta="compromisso orçamentário" /><Stat label="Despesa paga" value={brl(paid, { compact: true })} meta={`liquidado: ${brl(liquidated, { compact: true })}`} tone="blue" /></div></div></section>

      <section className="section"><div className="shell grid grid-2"><div className="card panel"><div className="panel-title"><h3>Despesa paga por função</h3><span>principais funções</span></div><div className="bar-list">{data.expenseFunctions.slice(0, 10).map((row) => <div className="bar-row" key={`${row.dimension_code}-${row.dimension_name}`}><div className="bar-meta"><span title={row.dimension_name}>{row.dimension_name}</span><strong className="mono">{brl(row.paid_value, { compact: true })}</strong></div><div className="bar-track"><div className="bar-fill" style={{ width: `${Math.max(2, Number(row.paid_value ?? 0) / maxFunction * 100)}%` }} /></div></div>)}</div></div><div className="card panel"><div className="panel-title"><h3>Como ler os valores</h3><span>resumo</span></div><div className="method-list"><div className="method-item"><strong>Empenhado</strong><p>Reserva e compromisso da dotação. Não significa que o dinheiro já saiu do caixa.</p></div><div className="method-item"><strong>Liquidado</strong><p>Reconhecimento de que a entrega ou o direito do credor foi apurado.</p></div><div className="method-item"><strong>Pago</strong><p>Desembolso financeiro registrado pela fonte.</p></div></div></div></div></section>

      <section className="section"><div className="shell"><div className="section-head enxuto"><div><span className="eyebrow">Consulta</span><h2>Receitas e credores agregados</h2></div><p>Pesquise por nome ou código e copie a referência diretamente da tabela.</p></div><div className="notice warn" style={{ marginBottom: 18 }}><span>!</span><div><strong>Credores:</strong> a fonte publica 5.554 agregados no período. Esta tela mostra até os 750 maiores para consulta rápida.</div></div><FinanceExplorer /></div></section>
    </>
  );
}
