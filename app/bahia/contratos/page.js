import Link from "next/link";
import { brl, integer, loadWebData } from "../../../lib/web-data";

export const metadata = { title: "Contratos estaduais da Bahia" };

function shortHash(value) {
  return value ? `${String(value).slice(0, 12)}…` : "—";
}

export default function BahiaContratosPage() {
  const data = loadWebData("bahia-transparency.json");
  const contracts = data.sefaz?.contracts;
  const summary = contracts?.summary;
  const primary = summary?.primary_table;
  const moneyFlow = data.sefaz?.moneyFlow;
  const flow = moneyFlow?.summary;
  const coverage = data.coverage?.sefaz_data?.contratos;

  if (!primary) {
    return <>
      <section className="page-hero"><div className="shell"><span className="eyebrow">Estado da Bahia</span><h1>Contratos estaduais</h1><p>Nenhum número será exibido até a tabela contratual passar pela validação e pela deduplicação por identificador oficial.</p><div className="hero-actions"><Link className="button" href="/bahia/transparencia">← Transparência estadual</Link></div></div></section>
      <section className="section compacto"><div className="shell"><div className="notice warn"><span>!</span><div><strong>{coverage?.status === "unavailable" ? "Coleta indisponível nesta execução." : "Coleta em processamento."}</strong> {coverage?.error || "Ausência de resumo não significa zero contratos."}</div></div></div></section>
    </>;
  }

  const value = primary.contract_value;
  const dedup = primary.deduplication ?? {};
  const agencies = primary.top_agencies ?? [];
  const suppliers = primary.top_suppliers_cnpj_only ?? [];
  const statuses = primary.top_statuses ?? [];
  const topFlow = moneyFlow?.top_end_to_end ?? [];

  return <>
    <section className="page-hero"><div className="shell">
      <span className="eyebrow">Estado da Bahia · SEFAZ/FIPLAN</span>
      <h1>Contratos e caminho do dinheiro</h1>
      <p>A base é consolidada por identificador oficial de instrumento. Linhas repetidas da view, aditivos e relações auxiliares não viram novos contratos.</p>
      <div className="hero-actions"><Link className="button" href="/bahia/transparencia">← Visão estadual</Link></div>
      <div className="kicker-row"><span className="badge green">{integer(primary.unique_instruments)} instrumentos únicos</span><span className="badge">recorte relacionado a 2026</span>{flow && <span className="badge green">{integer(flow.instruments_end_to_end)} vínculos de ponta a ponta</span>}</div>
    </div></section>

    <section className="section compacto"><div className="shell grid grid-4">
      <div className="card stat accent"><span className="stat-label">Instrumentos únicos</span><div><span className="stat-value">{integer(primary.unique_instruments)}</span><div className="stat-meta">deduplicados pela chave oficial</div></div></div>
      <div className="card stat"><span className="stat-label">Valor consolidado</span><div><span className="stat-value">{value?.deduplicated_sum != null ? brl(value.deduplicated_sum, { compact: true }) : "—"}</span><div className="stat-meta">{value?.field || "campo não identificado"}</div></div></div>
      <div className="card stat"><span className="stat-label">Processos relacionados</span><div><span className="stat-value">{integer(primary.unique_process_keys)}</span><div className="stat-meta">identificadores únicos no recorte</div></div></div>
      <div className="card stat blue"><span className="stat-label">Valor sem conflito</span><div><span className="stat-value">{integer(dedup.instruments_with_single_value)}</span><div className="stat-meta">instrumentos usados na soma</div></div></div>
    </div></section>

    <section className="section"><div className="shell">
      <div className="section-head enxuto"><div><span className="eyebrow">Fio do dinheiro</span><h2>Processo → instrumento → pagamento</h2></div><p>O vínculo só existe quando os identificadores oficiais coincidem após remover pontuação e espaços. Não há aproximação por nome ou objeto.</p></div>
      {flow ? <>
        <div className="grid grid-4">
          <div className="card stat"><span className="stat-label">Licitação → contrato</span><div><span className="stat-value">{integer(flow.instruments_procurement_to_contract)}</span><div className="stat-meta">instrumentos com vínculo exato</div></div></div>
          <div className="card stat"><span className="stat-label">Contrato → pagamento</span><div><span className="stat-value">{integer(flow.instruments_contract_to_payment)}</span><div className="stat-meta">instrumentos com pagamento em 2026</div></div></div>
          <div className="card stat accent"><span className="stat-label">Ponta a ponta</span><div><span className="stat-value">{integer(flow.instruments_end_to_end)}</span><div className="stat-meta">presentes nas três etapas</div></div></div>
          <div className="card stat blue"><span className="stat-label">Pagamentos vinculados</span><div><span className="stat-value">{brl(flow.payment_value_end_to_end, { compact: true })}</span><div className="stat-meta">somente instrumentos ponta a ponta</div></div></div>
        </div>
        {topFlow.length > 0 && <div className="section-subblock"><h3>Maiores pagamentos com cadeia completa</h3><div className="compact-list">{topFlow.slice(0, 12).map((item) => <div className="compact-row" key={item.instrument_id}><div><strong>Instrumento {item.instrument_id}</strong><span>{integer(item.procurement_process_ids?.length ?? 0)} processo(s) · {integer(item.payment_ids)} pagamento(s) · {integer(item.commitment_ids)} empenho(s) · {integer(item.liquidation_ids)} liquidação(ões)</span></div><strong>{brl(item.payment_value)}</strong></div>)}</div></div>}
      </> : <div className="notice warn"><span>!</span><div><strong>Cruzamento em processamento.</strong> A página mantém contratos disponíveis, mas não mostra contagem de vínculos até licitações e pagamentos serem reconciliados por chave oficial.</div></div>}
    </div></section>

    <section className="section"><div className="shell grid grid-2">
      <div><div className="section-head enxuto"><div><span className="eyebrow">Órgãos</span><h2>Maiores valores consolidados</h2></div></div><div className="compact-list">{agencies.slice(0, 10).map((item) => <div className="compact-row" key={item.name}><div><strong>{item.name}</strong><span>{integer(item.contracts)} instrumento(s)</span></div><strong>{brl(item.value)}</strong></div>)}</div></div>
      <div><div className="section-head enxuto"><div><span className="eyebrow">Fornecedores empresariais</span><h2>Maiores agregados por CNPJ</h2></div></div><div className="compact-list">{suppliers.slice(0, 10).map((item) => <div className="compact-row" key={item.cnpj}><div><strong>{item.name}</strong><span>CNPJ {item.cnpj} · {integer(item.contracts)} instrumento(s)</span></div><strong>{brl(item.value)}</strong></div>)}</div></div>
    </div></section>

    {statuses.length > 0 && <section className="section compacto"><div className="shell"><details className="card panel"><summary><strong>Situações publicadas pela fonte</strong></summary><div className="kicker-row" style={{marginTop:"1rem"}}>{statuses.slice(0, 15).map((item) => <span className="badge" key={item.name}>{item.name}: {integer(item.instruments)}</span>)}</div></details></div></section>}

    <section className="section compacto"><div className="shell"><details className="card panel"><summary><strong>Fonte, deduplicação e rastreabilidade</strong></summary><div className="section-subblock">
      <div className="compact-list">
        <div className="compact-row"><strong>Linhas relacionais no recorte</strong><span>{integer(dedup.raw_relation_rows)}</span></div>
        <div className="compact-row"><strong>Instrumentos únicos</strong><span>{integer(dedup.unique_instruments)}</span></div>
        <div className="compact-row"><strong>Sem valor</strong><span>{integer(dedup.instruments_without_value)}</span></div>
        <div className="compact-row"><strong>Valores conflitantes excluídos</strong><span>{integer(dedup.instruments_with_conflicting_values)}</span></div>
        <div className="compact-row"><strong>SHA-256 do ZIP</strong><span><code>{shortHash(contracts.evidence?.sha256)}</code></span></div>
      </div>
      <p className="muted">{dedup.value_policy}</p>
      <p className="muted">“Relacionado ao recorte 2026” não é sinônimo de “assinado em 2026” sem campo temporal específico que comprove essa interpretação.</p>
      <p className="muted">CPF é excluído da camada pública. CNPJ empresarial aparece somente em agregações. Valor alto ou fornecedor recorrente não constitui evidência de irregularidade.</p>
    </div></details></div></section>
  </>;
}
