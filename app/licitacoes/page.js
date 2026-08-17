import AcquisitionsExplorer from "../../components/AcquisitionsExplorer";
import { integer, loadWebData, parseBrlText, brl, dateBR } from "../../lib/web-data";

export const metadata = { title: "Licitações e aquisições" };

export default function LicitacoesPage() {
  const data = loadWebData("dashboard.json");
  const summary = data.acquisitions.summary;
  const total = parseBrlText(summary.api_reported_total_value_brl_text);

  return (
    <>
      <section className="page-hero">
        <div className="shell">
          <span className="eyebrow">Licitações e compras</span>
          <h1>Pesquise as aquisições publicadas pela Prefeitura.</h1>
          <p>Consulte objeto, órgão, processo, número, modalidade, data e valor. O recorte publicado fechou todas as páginas informadas pela fonte municipal.</p>
          <div className="kicker-row">
            <span className="badge green">completo para este filtro</span>
            <span className="badge">{integer(summary.records_received)} registros</span>
            <span className="badge">{integer(summary.pages_collected)} páginas</span>
            <span className="badge">até {dateBR(summary.period_end)}</span>
          </div>
        </div>
      </section>

      <section className="section compacto">
        <div className="shell grid grid-3">
          <div className="card stat accent"><span className="stat-label">Valor declarado</span><div><span className="stat-value">{brl(total, { compact: true })}</span><div className="stat-meta">total informado pela fonte</div></div></div>
          <div className="card stat"><span className="stat-label">Registros</span><div><span className="stat-value">{integer(summary.records_received)}</span><div className="stat-meta">{integer(summary.api_reported_total_records)} informados pela fonte</div></div></div>
          <div className="card stat blue"><span className="stat-label">Páginas coletadas</span><div><span className="stat-value">100%</span><div className="stat-meta">{integer(summary.pages_collected)} de {integer(summary.api_reported_pages)} páginas</div></div></div>
        </div>
      </section>

      <section className="section">
        <div className="shell">
          <div className="notice warn" style={{ marginBottom: 20 }}><span>!</span><div><strong>Leitura correta:</strong> dispensa, inexigibilidade ou valor alto são características do registro e não constituem, sozinhas, evidência de irregularidade.</div></div>
          <AcquisitionsExplorer />
        </div>
      </section>
    </>
  );
}
