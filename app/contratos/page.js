import { brl, loadWebData, parseBrlText } from "../../lib/web-data";

export const metadata = { title: "Contratos" };

export default function ContratosPage() {
  const finance = loadWebData("finance.json");
  const dashboard = loadWebData("dashboard.json");
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
          <h1>Execução contratual com cobertura explícita.</h1>
          <p>A Prefeitura publica totalizadores e execução agregada por unidade gestora. A grade de contratos individualizados é tratada separadamente porque a rota oficial detalhada apresentou timeout nas sondas do projeto.</p>
          <div className="kicker-row"><span className="badge green">agregados coletados</span><span className="badge yellow">grade detalhada parcial</span><span className="badge">PNCP complementar</span></div>
        </div>
      </section>

      <section className="section"><div className="shell"><div className="grid grid-4"><div className="card stat accent"><span className="stat-label">Valor contratual atualizado</span><div><span className="stat-value">{brl(contracted, { compact: true })}</span><div className="stat-meta">totalizador oficial</div></div></div><div className="card stat"><span className="stat-label">Empenhado no período</span><div><span className="stat-value">{brl(committed, { compact: true })}</span><div className="stat-meta">não é pagamento</div></div></div><div className="card stat"><span className="stat-label">Liquidado no período</span><div><span className="stat-value">{brl(liquidated, { compact: true })}</span><div className="stat-meta">estágio de liquidação</div></div></div><div className="card stat blue"><span className="stat-label">Pago no período</span><div><span className="stat-value">{brl(paid, { compact: true })}</span><div className="stat-meta">desembolso reportado</div></div></div></div></div></section>

      <section className="section">
        <div className="shell">
          <div className="notice warn" style={{ marginBottom: 22 }}><span>!</span><div><strong>Limitação documentada:</strong> a chamada oficial da grade detalhada de contratos apresentou timeout. O coletor adaptativo preserva respostas válidas e marca janelas que falham como parciais; timeout nunca é mostrado como “zero contratos”.</div></div>
          <div className="section-head"><div><span className="eyebrow">Unidades gestoras</span><h2>Execução agregada publicada</h2></div><p>{finance.contractUnits.length} unidades no snapshot do Portal da Transparência.</p></div>
          <div className="card table-card"><div className="table-wrap"><table><thead><tr><th>Unidade</th><th>Valor contratado</th><th>Empenhado</th><th>Liquidado</th><th>Pago</th></tr></thead><tbody>{finance.contractUnits.map((row, index) => <tr key={`${row.unit_code}-${index}`}><td><strong>{row.unit_name || "—"}</strong><div className="muted mono">{row.unit_code || ""}</div></td><td className="mono">{brl(row.contracted_value)}</td><td className="mono">{brl(row.committed_value)}</td><td className="mono">{brl(row.liquidated_value)}</td><td><strong className="mono">{brl(row.paid_value)}</strong></td></tr>)}</tbody></table></div></div>
        </div>
      </section>

      <section className="section"><div className="shell grid grid-2"><div className="coverage-card"><header><strong>Portal de Salvador</strong><span className="badge yellow">partial detail</span></header><p>{dashboard.finalStatus.datasets?.prefeitura_detailed_contract_grid?.production_behavior || "A cobertura detalhada depende da disponibilidade da API municipal."}</p></div><div className="coverage-card"><header><strong>PNCP</strong><span className="badge">reconciliação</span></header><p>Contratos do PNCP são coletados para CNPJs descobertos nas contratações e mantidos como fonte complementar, sem substituir silenciosamente a base municipal.</p></div></div></section>
    </>
  );
}
