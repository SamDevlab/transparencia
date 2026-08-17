import Link from "next/link";
import { brl, integer, loadWebData, parseBrlText, dateBR } from "../lib/web-data";

export const metadata = { title: "Visão geral" };

function Stat({ label, value, meta, tone = "" }) {
  return (
    <div className={`card stat ${tone}`}>
      <span className="stat-label">{label}</span>
      <div>
        <span className="stat-value mono">{value}</span>
        <div className="stat-meta">{meta}</div>
      </div>
    </div>
  );
}

function BarList({ rows }) {
  const max = Math.max(...rows.map((row) => Number(row.declared_value ?? 0)), 1);
  return (
    <div className="bar-list">
      {rows.map((row) => (
        <div className="bar-row" key={row.agency_name}>
          <div className="bar-meta">
            <span title={row.agency_name}>{row.agency_name}</span>
            <strong className="mono">{brl(row.declared_value, { compact: true })}</strong>
          </div>
          <div className="bar-track">
            <div className="bar-fill" style={{ width: `${Math.max(2, (Number(row.declared_value ?? 0) / max) * 100)}%` }} />
          </div>
        </div>
      ))}
    </div>
  );
}

export default function HomePage() {
  const data = loadWebData("dashboard.json");
  const finance = data.finance;
  const acq = data.acquisitions;
  const receitaRealizada = parseBrlText(finance.revenue_totalizer?.Realizado);
  const despesaPaga = parseBrlText(finance.expense_totalizer?.Pago);
  const totalAquisicoes = parseBrlText(acq.summary?.api_reported_total_value_brl_text);

  return (
    <>
      <section className="hero">
        <div className="shell">
          <span className="eyebrow">Dados públicos organizados</span>
          <h1>Consulte os gastos e a gestão pública de Salvador.</h1>
          <p>
            Pesquise finanças, licitações, contratos e agentes públicos em um só lugar. Use a busca no topo para localizar pessoa, processo, número, órgão, credor ou natureza de receita sem precisar decorar referências.
          </p>
          <div className="hero-actions">
            <Link className="button primary" href="/licitacoes">Consultar licitações →</Link>
            <Link className="button" href="/agentes">Ver agentes públicos</Link>
            <Link className="button" href="/financas">Ver finanças</Link>
          </div>
        </div>
      </section>

      <section className="section compacto">
        <div className="shell">
          <div className="notice">
            <span aria-hidden="true">●</span>
            <div><strong>Dados desta publicação:</strong> consolidados até {dateBR(data.asOf)}. Cada número mantém vínculo com sua fonte oficial.</div>
          </div>
        </div>
      </section>

      <section className="section">
        <div className="shell">
          <div className="section-head enxuto">
            <div><span className="eyebrow">Panorama</span><h2>Principais números</h2></div>
            <p>Recorte financeiro de 01/01/2026 a 17/08/2026.</p>
          </div>
          <div className="grid grid-4">
            <Stat label="Receita realizada" value={brl(receitaRealizada, { compact: true })} meta="arrecadação no período" tone="accent" />
            <Stat label="Despesa paga" value={brl(despesaPaga, { compact: true })} meta="pagamento efetivamente registrado" />
            <Stat label="Aquisições publicadas" value={brl(totalAquisicoes, { compact: true })} meta={`${integer(acq.summary?.records_received)} registros`} tone="blue" />
            <Stat label="Agentes catalogados" value={integer(data.agents?.total)} meta={`${integer(data.agents?.vereadores)} vereadores + Executivo verificado`} />
          </div>
        </div>
      </section>

      <section className="section">
        <div className="shell grid grid-2">
          <div className="card panel">
            <div className="panel-title"><h3>Órgãos com maior valor em aquisições</h3><span>2026</span></div>
            <BarList rows={acq.byAgency.slice(0, 8)} />
          </div>
          <div className="card panel">
            <div className="panel-title"><h3>Aquisições por forma de contratação</h3><span>quantidade e valor</span></div>
            <div className="bar-list">
              {acq.byType.map((row) => (
                <div className="bar-row" key={row.acquisition_type}>
                  <div className="bar-meta"><span>{row.acquisition_type}</span><strong>{integer(row.records)} · {brl(row.declared_value, { compact: true })}</strong></div>
                  <div className="bar-track"><div className="bar-fill" style={{ width: `${Math.max(3, (Number(row.declared_value) / Math.max(...acq.byType.map((x) => Number(x.declared_value)), 1)) * 100)}%` }} /></div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      <section className="section">
        <div className="shell">
          <div className="section-head enxuto">
            <div><span className="eyebrow">Aquisições</span><h2>Maiores valores publicados</h2></div>
            <Link className="button" href="/licitacoes">Pesquisar todos os registros →</Link>
          </div>
          <div className="card table-card">
            <div className="table-wrap">
              <table>
                <thead><tr><th>Órgão</th><th>Objeto e referência</th><th>Tipo</th><th>Publicação</th><th>Valor</th></tr></thead>
                <tbody>
                  {acq.top.slice(0, 6).map((row) => (
                    <tr key={row.id}>
                      <td><strong>{row.orgao || "—"}</strong></td>
                      <td className="object-cell">{row.objeto || "—"}<div className="muted mono">{row.processo ? `Processo ${row.processo}` : row.numero ? `Aquisição ${row.numero}` : ""}</div></td>
                      <td><span className="badge">{row.tipo || row.modalidade || "—"}</span></td>
                      <td>{dateBR(row.publicadoEm)}</td>
                      <td><strong className="mono">{brl(row.valor)}</strong></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
          <div className="results-line">
            <span>Dispensa, inexigibilidade ou valor elevado não são apresentados como irregularidade.</span>
            <Link href="/metodologia">Entender a metodologia →</Link>
          </div>
        </div>
      </section>
    </>
  );
}
