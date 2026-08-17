import { brl, loadWebData, parseBrlText } from "../../lib/web-data";

export const metadata = { title: "Contratos" };

export default function ContratosPage() {
  const finance = loadWebData("finance.json");
  const totals = finance.summary.contracts_totalizer ?? {};
  const contracted = parseBrlText(totals["Valor Contratual (Atualizado)"]);
  const committed = parseBrlText(totals["Empenhado no Período"]);
  const liquidated = parseBrlText(totals["Liquidado no período"]);
  const paid = parseBrlText(totals["Pago no período"]);

  return (
    <>
      <section className="page-hero">
        <div className="shell">
          <span className="eyebrow">Contratos</span>
          <h1>Execução contratual publicada pela Prefeitura.</h1>
          <p>Valores contratuais e execução financeira por unidade gestora. A consulta detalhada de contratos permanece identificada como parcial quando a fonte oficial não responde dentro do tempo esperado.</p>
          <div className="kicker-row"><span className="badge green">totais oficiais coletados</span><span className="badge yellow">detalhamento parcial</span><span className="badge">PNCP como fonte complementar</span></div>
        </div>
      </section>

      <section className="section compacto"><div className="shell"><div className="grid grid-4"><div className="card stat accent"><span className="stat-label">Valor contratual atualizado</span><div><span className="stat-value">{brl(contracted, { compact: true })}</span><div className="stat-meta">totalizador oficial</div></div></div><div className="card stat"><span className="stat-label">Empenhado</span><div><span className="stat-value">{brl(committed, { compact: true })}</span><div className="stat-meta">compromisso orçamentário</div></div></div><div className="card stat"><span className="stat-label">Liquidado</span><div><span className="stat-value">{brl(liquidated, { compact: true })}</span><div className="stat-meta">obrigação reconhecida</div></div></div><div className="card stat blue"><span className="stat-label">Pago</span><div><span className="stat-value">{brl(paid, { compact: true })}</span><div className="stat-meta">desembolso registrado</div></div></div></div></div></section>

      <section className="section">
        <div className="shell">
          <div className="notice warn" style={{ marginBottom: 20 }}><span>!</span><div><strong>Cobertura:</strong> a grade individual de contratos apresentou tempo de resposta esgotado em consultas oficiais. O sistema não transforma essa falha em “zero contratos”.</div></div>
          <div className="section-head enxuto"><div><span className="eyebrow">Unidades gestoras</span><h2>Execução agregada</h2></div><p>{finance.contractUnits.length} unidades publicadas no recorte.</p></div>
          <div className="card table-card"><div className="table-wrap"><table><thead><tr><th>Unidade</th><th>Valor contratado</th><th>Empenhado</th><th>Liquidado</th><th>Pago</th></tr></thead><tbody>{finance.contractUnits.map((row, index) => <tr key={`${row.unit_code}-${index}`}><td><strong>{row.unit_name || "—"}</strong><div className="muted mono">{row.unit_code || ""}</div></td><td className="mono">{brl(row.contracted_value)}</td><td className="mono">{brl(row.committed_value)}</td><td className="mono">{brl(row.liquidated_value)}</td><td><strong className="mono">{brl(row.paid_value)}</strong></td></tr>)}</tbody></table></div></div>
          <div className="results-line"><span>O PNCP é usado para comparação e complementação, sem substituir silenciosamente a fonte municipal.</span><a href="https://pncp.gov.br/" target="_blank" rel="noreferrer">Abrir PNCP ↗</a></div>
        </div>
      </section>
    </>
  );
}
