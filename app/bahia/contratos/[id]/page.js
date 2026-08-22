import Link from "next/link";
import { notFound } from "next/navigation";
import { brl, integer, loadWebData } from "../../../../lib/web-data";

export async function generateMetadata({ params }) {
  const { id } = await params;
  return { title: `Instrumento ${id} · Contratos Bahia` };
}

function joined(values) {
  return values?.length ? values.join(" · ") : "não informado";
}

export default async function BahiaContratoProfilePage({ params }) {
  const { id } = await params;
  const data = loadWebData("bahia-transparency.json");
  const moneyFlow = data.sefaz?.moneyFlow;
  const item = (moneyFlow?.top_end_to_end ?? []).find((row) => String(row.instrument_id) === String(id));

  if (!item) notFound();

  const processes = item.procurement_process_ids ?? [];
  const contract = item.contract_profile;
  const supplierLabel = contract?.supplier
    ? `${contract.supplier.name} · CNPJ ${contract.supplier.cnpj}`
    : contract?.has_private_person_supplier
      ? "Pessoa física — dado pessoal não republicado"
      : "não identificado sem ambiguidade";

  return <>
    <section className="page-hero"><div className="shell">
      <span className="eyebrow">Estado da Bahia · cadeia documental</span>
      <h1>Instrumento {item.instrument_id}</h1>
      <p>{contract?.object || "Perfil ligado por identificador oficial entre aquisição, instrumento contratual e pagamento. Campos ambíguos permanecem sem preenchimento em vez de serem inferidos."}</p>
      <div className="hero-actions"><Link className="button" href="/bahia/contratos">← Contratos estaduais</Link></div>
      <div className="kicker-row">
        <span className="badge green">cadeia ponta a ponta verificada</span>
        <span className="badge">recorte de {moneyFlow?.selected_year ?? 2026}</span>
        {contract && <span className="badge green">perfil contratual exato</span>}
      </div>
    </div></section>

    <section className="section compacto"><div className="shell grid grid-4">
      <div className="card stat accent"><span className="stat-label">Pago no recorte</span><div><span className="stat-value">{brl(item.payment_value, { compact: true })}</span><div className="stat-meta">pagamentos ligados ao instrumento</div></div></div>
      <div className="card stat"><span className="stat-label">Valor contratual</span><div><span className="stat-value">{contract?.contract_value != null ? brl(contract.contract_value, { compact: true }) : "—"}</span><div className="stat-meta">{contract?.contract_value_status === "conflicting_official_values" ? "valores oficiais conflitantes" : contract?.contract_value_field || "não disponível"}</div></div></div>
      <div className="card stat"><span className="stat-label">Pagamentos</span><div><span className="stat-value">{integer(item.payment_ids)}</span><div className="stat-meta">identificadores distintos</div></div></div>
      <div className="card stat blue"><span className="stat-label">Processos de aquisição</span><div><span className="stat-value">{integer(processes.length)}</span><div className="stat-meta">vínculos oficiais encontrados</div></div></div>
    </div></section>

    <section className="section"><div className="shell grid grid-2">
      <div className="card panel">
        <div className="panel-title"><h3>Contrato</h3><span>{contract ? "dados ligados pela chave oficial" : "aguardando enriquecimento"}</span></div>
        {contract ? <div className="compact-list">
          <div className="compact-row"><strong>Órgão</strong><span>{contract.agency || `não resolvido (${integer(contract.agency_variants)} variações)`}</span></div>
          <div className="compact-row"><strong>Fornecedor</strong><span>{supplierLabel}</span></div>
          <div className="compact-row"><strong>Situação</strong><span>{joined(contract.statuses)}</span></div>
          <div className="compact-row"><strong>Modalidade</strong><span>{joined(contract.modalities)}</span></div>
          <div className="compact-row"><strong>Objeto</strong><span>{contract.object || `não resolvido (${integer(contract.object_variants)} variações)`}</span></div>
        </div> : <p className="muted">A cadeia financeira já foi confirmada, mas este snapshot ainda não contém os campos descritivos do contrato. Nenhum valor é inferido para preencher a lacuna.</p>}
      </div>

      <div className="card panel">
        <div className="panel-title"><h3>Execução relacionada</h3><span>conceitos mantidos separados</span></div>
        <div className="compact-list">
          <div className="compact-row"><strong>Empenhos</strong><span>{integer(item.commitment_ids)}</span></div>
          <div className="compact-row"><strong>Liquidações</strong><span>{integer(item.liquidation_ids)}</span></div>
          <div className="compact-row"><strong>Pagamentos</strong><span>{integer(item.payment_ids)}</span></div>
          <div className="compact-row"><strong>Linhas de pagamento</strong><span>{integer(item.payment_rows)}</span></div>
        </div>
        <p className="muted">O valor pago no recorte anual não é tratado como valor total do contrato, saldo contratual ou obrigação ainda devida.</p>
      </div>
    </div></section>

    <section className="section"><div className="shell">
      <div className="section-head enxuto"><div><span className="eyebrow">Origem da contratação</span><h2>Processo(s) de aquisição vinculados</h2></div><p>Somente igualdade de identificadores oficiais cria a relação.</p></div>
      <div className="compact-list">{processes.map((processId) => <div className="compact-row" key={processId}><strong>{processId}</strong><span>identificador oficial normalizado</span></div>)}</div>
    </div></section>

    <section className="section compacto"><div className="shell"><details className="card panel"><summary><strong>Rastreabilidade, ambiguidades e privacidade</strong></summary><div className="section-subblock">
      <p className="muted">{moneyFlow?.identity_rule}</p>
      {moneyFlow?.contract_profile_identity_rule && <p className="muted">{moneyFlow.contract_profile_identity_rule}</p>}
      {moneyFlow?.contract_profile_ambiguity_rule && <p className="muted">{moneyFlow.contract_profile_ambiguity_rule}</p>}
      <p className="muted">{moneyFlow?.interpretation}</p>
      <p className="muted">{moneyFlow?.privacy_rule}</p>
      <div className="compact-list"><div className="compact-row"><strong>Fonte</strong><span>{moneyFlow?.source || "SEFAZ/AGE Bahia"}</span></div></div>
    </div></details></div></section>
  </>;
}
