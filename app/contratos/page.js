import Link from "next/link";
import { brl, dateBR, integer, loadWebData, parseBrlText } from "../../lib/web-data";

export const metadata = { title: "Contratos" };

export default function ContratosPage() {
  const finance = loadWebData("finance.json");
  const contracts = loadWebData("contracts.json");
  const totals = finance.summary.contracts_totalizer ?? {};
  const contracted = parseBrlText(totals["Valor Contratual (Atualizado)"]);
  const committed = parseBrlText(totals["Empenhado no Período"]);
  const liquidated = parseBrlText(totals["Liquidado no período"]);
  const paid = parseBrlText(totals["Pago no período"]);
  const topContracts = contracts.rows.slice().sort((a, b) => Number(b.valorGlobal || 0) - Number(a.valorGlobal || 0)).slice(0, 20);

  return (
    <>
      <section className="page-hero">
        <div className="shell">
          <span className="eyebrow">Contratos</span>
          <h1>Execução municipal e contratos individualizados, sem misturar as fontes.</h1>
          <p>A Prefeitura fornece os totais e a execução agregada por unidade. O PNCP complementa a consulta com contratos individualizados, fornecedor, processo, valor e vigência.</p>
          <div className="kicker-row"><span className="badge green">totais municipais coletados</span><span className="badge">{integer(contracts.rows.length)} contratos PNCP preservados</span><span className="badge yellow">grade municipal detalhada parcial</span></div>
        </div>
      </section>

      <section className="section compacto"><div className="shell"><div className="grid grid-4"><div className="card stat accent"><span className="stat-label">Valor contratual atualizado</span><div><span className="stat-value">{brl(contracted, { compact: true })}</span><div className="stat-meta">totalizador oficial da Prefeitura</div></div></div><div className="card stat"><span className="stat-label">Empenhado</span><div><span className="stat-value">{brl(committed, { compact: true })}</span><div className="stat-meta">compromisso orçamentário municipal</div></div></div><div className="card stat"><span className="stat-label">Liquidado</span><div><span className="stat-value">{brl(liquidated, { compact: true })}</span><div className="stat-meta">obrigação reconhecida</div></div></div><div className="card stat blue"><span className="stat-label">Pago</span><div><span className="stat-value">{brl(paid, { compact: true })}</span><div className="stat-meta">desembolso registrado</div></div></div></div></div></section>

      <section className="section">
        <div className="shell">
          <div className="notice warn" style={{ marginBottom: 20 }}><span>!</span><div><strong>Duas coberturas diferentes:</strong> a grade individual da API municipal apresentou tempo de resposta esgotado e permanece parcial. Os contratos individualizados abaixo vêm do PNCP e são uma fonte complementar; eles não substituem silenciosamente a base municipal.</div></div>
          <div className="section-head enxuto"><div><span className="eyebrow">Contratos individualizados</span><h2>Maiores valores encontrados no PNCP</h2></div><Link className="button" href="/fornecedores">Explorar fornecedores →</Link></div>
          <div className="card table-card"><div className="table-wrap"><table><thead><tr><th>Contrato</th><th>Processo</th><th>Fornecedor</th><th>Unidade</th><th>Objeto</th><th>Valor global</th><th>Vigência</th></tr></thead><tbody>{topContracts.map((row) => <tr key={row.id}><td><a href={row.fonte} target="_blank" rel="noreferrer"><strong>{row.numero || "—"}</strong> ↗</a></td><td className="mono">{row.processo || "—"}</td><td>{row.documentoFornecedor ? <Link href={`/fornecedores/${encodeURIComponent(row.documentoFornecedor)}`}><strong>{row.fornecedor || "—"}</strong><div className="muted mono">{row.documentoFornecedor}</div></Link> : (row.fornecedor || "—")}</td><td>{row.unidade || "—"}</td><td className="object-cell">{row.objeto || "—"}</td><td><strong className="mono">{brl(row.valorGlobal)}</strong></td><td>{dateBR(row.vigenciaInicio)} → {dateBR(row.vigenciaFim)}</td></tr>)}</tbody></table></div></div>
          <div className="results-line"><span>{contracts.coverageNote}</span><a href="https://pncp.gov.br/" target="_blank" rel="noreferrer">Abrir Portal Nacional de Contratações Públicas ↗</a></div>
        </div>
      </section>

      <section className="section">
        <div className="shell">
          <div className="section-head enxuto"><div><span className="eyebrow">Execução municipal</span><h2>Valores agregados por unidade gestora</h2></div><p>{finance.contractUnits.length} unidades publicadas no recorte municipal.</p></div>
          <div className="card table-card"><div className="table-wrap"><table><thead><tr><th>Unidade</th><th>Valor contratado</th><th>Empenhado</th><th>Liquidado</th><th>Pago</th></tr></thead><tbody>{finance.contractUnits.map((row, index) => <tr key={`${row.unit_code}-${index}`}><td><strong>{row.unit_name || "—"}</strong><div className="muted mono">{row.unit_code || ""}</div></td><td className="mono">{brl(row.contracted_value)}</td><td className="mono">{brl(row.committed_value)}</td><td className="mono">{brl(row.liquidated_value)}</td><td><strong className="mono">{brl(row.paid_value)}</strong></td></tr>)}</tbody></table></div></div>
        </div>
      </section>
    </>
  );
}
