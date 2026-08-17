import Link from "next/link";
import { brl, integer, loadWebData, parseBrlText, dateBR } from "../lib/web-data";

export const metadata = {
  title: "Visão geral",
};

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
  const revenueRealized = parseBrlText(finance.revenue_totalizer?.Realizado);
  const expensePaid = parseBrlText(finance.expense_totalizer?.Pago);
  const acquisitionTotal = parseBrlText(acq.summary?.api_reported_total_value_brl_text);

  return (
    <>
      <section className="hero">
        <div className="shell">
          <span className="eyebrow">Dados públicos, com contexto</span>
          <h1>Entenda para onde vai o dinheiro de Salvador.</h1>
          <p>
            Receita, despesa, aquisições, contratos e Câmara reunidos em uma interface pública. Cada número mantém a fonte e o escopo de cobertura; sinais de valor alto ou concentração não são tratados como prova de irregularidade.
          </p>
          <div className="hero-actions">
            <Link className="button primary" href="/licitacoes">Explorar licitações →</Link>
            <Link className="button" href="/financas">Ver finanças</Link>
            <Link className="button" href="/metodologia">Como os dados são tratados</Link>
          </div>
        </div>
      </section>

      <section className="section">
        <div className="shell">
          <div className="notice">
            <span aria-hidden="true">●</span>
            <div><strong>Recorte desta publicação:</strong> dados consolidados até {dateBR(data.asOf)}. A completude é sempre limitada à fonte e ao filtro documentados no repositório.</div>
          </div>
        </div>
      </section>

      <section className="section">
        <div className="shell">
          <div className="section-head">
            <div><span className="eyebrow">Panorama</span><h2>Salvador em números</h2></div>
            <p>Valores oficiais do Portal da Transparência no período 01/01/2026–17/08/2026, preservados com proveniência.</p>
          </div>
          <div className="grid grid-4">
            <Stat label="Receita realizada" value={brl(revenueRealized, { compact: true })} meta="Portal da Transparência" tone="accent" />
            <Stat label="Despesa paga" value={brl(expensePaid, { compact: true })} meta="não confundir com empenhado/liquidado" />
            <Stat label="Aquisições declaradas" value={brl(acquisitionTotal, { compact: true })} meta={`${integer(acq.summary?.records_received)} registros`} tone="blue" />
            <Stat label="Câmara" value={integer(data.officialsCount)} meta="nomes exibidos no cadastro oficial observado" />
          </div>
        </div>
      </section>

      <section className="section">
        <div className="shell grid grid-2">
          <div className="card panel">
            <div className="panel-title"><h3>Maiores órgãos por valor declarado</h3><span>Aquisições 2026</span></div>
            <BarList rows={acq.byAgency.slice(0, 8)} />
          </div>
          <div className="card panel">
            <div className="panel-title"><h3>Aquisições por tipo</h3><span>registros / valor</span></div>
            <div className="bar-list">
              {acq.byType.map((row) => (
                <div className="bar-row" key={row.acquisition_type}>
                  <div className="bar-meta"><span>{row.acquisition_type}</span><strong>{integer(row.records)} · {brl(row.declared_value, { compact: true })}</strong></div>
                  <div className="bar-track"><div className="bar-fill" style={{ width: `${Math.max(3, (Number(row.declared_value) / Math.max(...acq.byType.map((x) => Number(x.declared_value)), 1)) * 100)}%` }} /></div>
                </div>
              ))}
            </div>
            <div className="notice warn" style={{ marginTop: 20 }}>
              <span>!</span><div><strong>Leitura correta:</strong> dispensa e inexigibilidade são modalidades previstas em lei; a presença delas, sozinha, não indica ilícito.</div>
            </div>
          </div>
        </div>
      </section>

      <section className="section">
        <div className="shell">
          <div className="section-head">
            <div><span className="eyebrow">Aquisições</span><h2>Maiores valores publicados</h2></div>
            <Link className="button" href="/licitacoes">Pesquisar os {integer(acq.summary?.records_received)} registros →</Link>
          </div>
          <div className="card table-card">
            <div className="table-wrap">
              <table>
                <thead><tr><th>Órgão</th><th>Objeto</th><th>Tipo</th><th>Publicação</th><th>Valor</th></tr></thead>
                <tbody>
                  {acq.top.slice(0, 8).map((row) => (
                    <tr key={row.id}>
                      <td><strong>{row.orgao || "—"}</strong></td>
                      <td className="object-cell">{row.objeto || "—"}<div className="muted mono">{row.processo || row.numero || ""}</div></td>
                      <td><span className="badge">{row.tipo || row.modalidade || "—"}</span></td>
                      <td>{dateBR(row.publicadoEm)}</td>
                      <td><strong className="mono">{brl(row.valor)}</strong></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </section>

      <section className="section">
        <div className="shell">
          <div className="section-head">
            <div><span className="eyebrow">Integridade</span><h2>O que este site promete — e o que não promete</h2></div>
          </div>
          <div className="coverage-grid">
            <div className="coverage-card"><header><strong>Aquisições municipais</strong><span className="badge green">complete_for_filter</span></header><p>{integer(acq.summary?.records_received)} de {integer(acq.summary?.api_reported_total_records)} registros e {integer(acq.summary?.pages_collected)} de {integer(acq.summary?.api_reported_pages)} páginas no recorte publicado.</p></div>
            <div className="coverage-card"><header><strong>Contratos individualizados</strong><span className="badge yellow">parcial</span></header><p>A API municipal detalhada apresentou timeout em sondas. O projeto preserva o que responde e nunca converte timeout em “zero contratos”.</p></div>
            <div className="coverage-card"><header><strong>Câmara — empenhos</strong><span className="badge yellow">validado por regra</span></header><p>O coletor só promove completude quando a paginação termina e 100% dos identificadores visíveis são normalizados.</p></div>
            <div className="coverage-card"><header><strong>Interpretação</strong><span className="badge">descritiva</span></header><p>Valor alto, concentração, dispensa ou inexigibilidade servem para orientar investigação documental; não são conclusões de corrupção ou irregularidade.</p></div>
          </div>
        </div>
      </section>
    </>
  );
}
