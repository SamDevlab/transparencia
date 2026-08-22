import Link from "next/link";
import { notFound } from "next/navigation";
import { brl, integer, loadWebData } from "../../../../lib/web-data";

export async function generateMetadata({ params }) {
  const { id } = await params;
  return { title: `Instrumento ${id} · Contratos Bahia` };
}

export default async function BahiaContratoProfilePage({ params }) {
  const { id } = await params;
  const data = loadWebData("bahia-transparency.json");
  const moneyFlow = data.sefaz?.moneyFlow;
  const item = (moneyFlow?.top_end_to_end ?? []).find((row) => String(row.instrument_id) === String(id));

  if (!item) notFound();

  const processes = item.procurement_process_ids ?? [];

  return <>
    <section className="page-hero"><div className="shell">
      <span className="eyebrow">Estado da Bahia · cadeia documental</span>
      <h1>Instrumento {item.instrument_id}</h1>
      <p>Perfil público construído somente com identificadores administrativos e agregações que possuem vínculo exato entre aquisição, instrumento e pagamento.</p>
      <div className="hero-actions"><Link className="button" href="/bahia/contratos">← Contratos estaduais</Link></div>
      <div className="kicker-row"><span className="badge green">cadeia ponta a ponta verificada</span><span className="badge">recorte de {moneyFlow?.selected_year ?? 2026}</span></div>
    </div></section>

    <section className="section compacto"><div className="shell grid grid-4">
      <div className="card stat accent"><span className="stat-label">Valor pago no recorte</span><div><span className="stat-value">{brl(item.payment_value, { compact: true })}</span><div className="stat-meta">soma dos pagamentos vinculados</div></div></div>
      <div className="card stat"><span className="stat-label">Pagamentos</span><div><span className="stat-value">{integer(item.payment_ids)}</span><div className="stat-meta">identificadores distintos</div></div></div>
      <div className="card stat"><span className="stat-label">Empenhos</span><div><span className="stat-value">{integer(item.commitment_ids)}</span><div className="stat-meta">etapa orçamentária preservada</div></div></div>
      <div className="card stat blue"><span className="stat-label">Liquidações</span><div><span className="stat-value">{integer(item.liquidation_ids)}</span><div className="stat-meta">etapa contábil preservada</div></div></div>
    </div></section>

    <section className="section"><div className="shell grid grid-2">
      <div className="card panel">
        <div className="panel-title"><h3>Processo(s) de aquisição</h3><span>{integer(processes.length)} vínculo(s)</span></div>
        <div className="compact-list">{processes.map((processId) => <div className="compact-row" key={processId}><strong>{processId}</strong><span>identificador oficial normalizado</span></div>)}</div>
      </div>
      <div className="card panel">
        <div className="panel-title"><h3>Como interpretar</h3><span>sem inferências</span></div>
        <div className="compact-list">
          <div className="compact-row"><strong>Licitação / aquisição</strong><span>processo oficial relacionado</span></div>
          <div className="compact-row"><strong>Instrumento</strong><span>{item.instrument_id}</span></div>
          <div className="compact-row"><strong>Pagamento</strong><span>{integer(item.payment_rows)} linha(s) no recorte</span></div>
        </div>
        <p className="muted">O valor exibido é o total de pagamentos encontrados no recorte anual para este instrumento. Ele não é tratado como valor total do contrato.</p>
      </div>
    </div></section>

    <section className="section compacto"><div className="shell"><details className="card panel"><summary><strong>Rastreabilidade e privacidade</strong></summary><div className="section-subblock">
      <p className="muted">{moneyFlow?.identity_rule}</p>
      <p className="muted">{moneyFlow?.interpretation}</p>
      <p className="muted">{moneyFlow?.privacy_rule}</p>
      <div className="compact-list"><div className="compact-row"><strong>Fonte</strong><span>{moneyFlow?.source || "SEFAZ/AGE Bahia"}</span></div></div>
    </div></details></div></section>
  </>;
}
