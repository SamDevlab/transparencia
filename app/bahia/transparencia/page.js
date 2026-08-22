import Link from "next/link";
import { brl, integer, loadWebData } from "../../../lib/web-data";

export const metadata = { title: "Transparência estadual da Bahia" };

function shortHash(value) {
  return value ? `${String(value).slice(0, 12)}…` : "—";
}

function datePt(value) {
  if (!value) return "não informada";
  const date = new Date(value);
  return Number.isNaN(date.getTime())
    ? String(value)
    : new Intl.DateTimeFormat("pt-BR", { dateStyle: "short", timeZone: "America/Bahia" }).format(date);
}

export default function BahiaTransparenciaPage() {
  const data = loadWebData("bahia-transparency.json");
  const revenue = data.sefaz?.revenues;
  const revenueSummary = revenue?.summary;
  const revenueTotals = revenueSummary?.selected_year_totals;
  const procurement = data.sefaz?.procurements;
  const procurementSummary = procurement?.summary;
  const primaryProcurement = procurementSummary?.primary_licitacoes;
  const expenses = data.sefaz?.expenses;
  const primaryExpense = expenses?.summary?.primary_table;
  const payments = data.sefaz?.payments;
  const annualPayment = payments?.summary?.selected_year_payment;
  const contracts = data.sefaz?.contracts;
  const primaryContract = contracts?.summary?.primary_table;
  const contractValue = primaryContract?.contract_value;
  const moneyFlow = data.sefaz?.moneyFlow;
  const flow = moneyFlow?.summary;
  const sefazProcessed = data.sefaz?.summary?.processed ?? 0;
  const sefazExpected = data.sefaz?.summary?.expected ?? 5;

  return <>
    <section className="page-hero"><div className="shell">
      <span className="eyebrow">Estado da Bahia</span>
      <h1>Transparência estadual, sem excesso de informação.</h1>
      <p>Receitas, execução da despesa, compras, contratos e pagamentos em uma única visão. Cada número mantém o conceito publicado pela fonte e os detalhes técnicos ficam disponíveis sem ocupar a leitura principal.</p>
      <div className="kicker-row">
        <span className="badge green">{integer(sefazProcessed)}/{integer(sefazExpected)} bases SEFAZ processadas</span>
        <span className="badge">snapshot {data.snapshot || "não disponível"}</span>
        {flow && <span className="badge green">fio do dinheiro por chaves exatas</span>}
      </div>
    </div></section>

    <section className="section compacto"><div className="shell">
      <div className="section-head enxuto"><div><span className="eyebrow">Visão geral</span><h2>Os números que importam primeiro</h2></div><p>Valores do recorte de 2026 nas respectivas bases oficiais.</p></div>
      <div className="grid grid-4">
        <div className="card stat accent"><span className="stat-label">Receita arrecadada</span><div><span className="stat-value">{revenueTotals?.realized != null ? brl(revenueTotals.realized, { compact: true }) : "—"}</span><div className="stat-meta">base de receitas</div></div></div>
        <div className="card stat"><span className="stat-label">Despesa empenhada</span><div><span className="stat-value">{primaryExpense?.stage_totals?.committed?.sum != null ? brl(primaryExpense.stage_totals.committed.sum, { compact: true }) : "—"}</span><div className="stat-meta">compromisso orçamentário</div></div></div>
        <div className="card stat"><span className="stat-label">Despesa liquidada</span><div><span className="stat-value">{primaryExpense?.stage_totals?.liquidated?.sum != null ? brl(primaryExpense.stage_totals.liquidated.sum, { compact: true }) : "—"}</span><div className="stat-meta">despesa reconhecida</div></div></div>
        <div className="card stat blue"><span className="stat-label">Valor do Pagamento</span><div><span className="stat-value">{annualPayment?.sum != null ? brl(annualPayment.sum, { compact: true }) : "—"}</span><div className="stat-meta">base específica de pagamentos</div></div></div>
      </div>
    </div></section>

    <section className="section"><div className="shell">
      <div className="section-head enxuto"><div><span className="eyebrow">Compras públicas</span><h2>Da licitação ao contrato</h2></div><p>Licitação, instrumento e pagamento conservam suas próprias granularidades. O sistema só cria vínculo quando existe identificador oficial compatível.</p></div>
      <div className="grid grid-3">
        <Link className="coverage-card clicavel" href="/bahia/contratos"><header><strong>Licitações / aquisições</strong><span className="badge green">processado</span></header><p><strong>{integer(primaryProcurement?.rows_selected_year ?? 0)}</strong> processos/aquisições no recorte de 2026.</p><div className="source-foot"><span>Homologado: {primaryProcurement?.homologated_value?.sum != null ? brl(primaryProcurement.homologated_value.sum, { compact: true }) : "—"}</span><span>Ver relações →</span></div></Link>
        <Link className="coverage-card clicavel" href="/bahia/contratos"><header><strong>Instrumentos contratuais</strong><span className="badge green">deduplicado</span></header><p><strong>{integer(primaryContract?.unique_instruments ?? 0)}</strong> instrumentos únicos relacionados ao recorte da fonte.</p><div className="source-foot"><span>Valor consolidado: {contractValue?.deduplicated_sum != null ? brl(contractValue.deduplicated_sum, { compact: true }) : "—"}</span><span>Ver contratos →</span></div></Link>
        <Link className="coverage-card clicavel" href="/bahia/contratos"><header><strong>Fio do dinheiro</strong><span className={`badge ${flow ? "green" : "yellow"}`}>{flow ? "vínculo exato" : "em processamento"}</span></header><p>{flow ? <><strong>{integer(flow.instruments_end_to_end)}</strong> instrumento(s) encontrados nas três etapas por identificador oficial.</> : "O cruzamento processo → instrumento → pagamento está sendo construído sem aproximação textual."}</p><div className="source-foot"><span>{flow?.payment_value_end_to_end != null ? `Pagamentos vinculados: ${brl(flow.payment_value_end_to_end, { compact: true })}` : "Sem número inferido"}</span><span>Detalhar →</span></div></Link>
      </div>
    </div></section>

    {primaryExpense?.top_agencies?.paid?.length > 0 && <section className="section"><div className="shell">
      <div className="section-head enxuto"><div><span className="eyebrow">Execução</span><h2>Maiores valores pagos por órgão</h2></div><p>Agregação do campo <code>{primaryExpense.schema?.detected_fields?.stages?.paid || "VAL_PAGO"}</code> da base de despesas.</p></div>
      <div className="compact-list">{primaryExpense.top_agencies.paid.slice(0, 8).map((item) => <div className="compact-row" key={item.name}><strong>{item.name}</strong><strong>{brl(item.paid)}</strong></div>)}</div>
    </div></section>}

    <section className="section"><div className="shell grid grid-2">
      <div className="card panel"><div className="panel-title"><h3>Estágios contábeis</h3><span>não são equivalentes</span></div><div className="compact-list">
        <div className="compact-row"><strong>Empenhado</strong><span>{primaryExpense?.stage_totals?.committed?.sum != null ? brl(primaryExpense.stage_totals.committed.sum) : "—"}</span></div>
        <div className="compact-row"><strong>Liquidado</strong><span>{primaryExpense?.stage_totals?.liquidated?.sum != null ? brl(primaryExpense.stage_totals.liquidated.sum) : "—"}</span></div>
        <div className="compact-row"><strong>Pago na base de despesas</strong><span>{primaryExpense?.stage_totals?.paid?.sum != null ? brl(primaryExpense.stage_totals.paid.sum) : "—"}</span></div>
        <div className="compact-row"><strong>Valor do Pagamento</strong><span>{annualPayment?.sum != null ? brl(annualPayment.sum) : "—"}</span></div>
      </div><p className="muted">Os dois últimos vêm de bases diferentes e não são igualados automaticamente.</p></div>
      <div className="card panel"><div className="panel-title"><h3>Cobertura</h3><span>estado da coleta</span></div><div className="compact-list">
        <div className="compact-row"><strong>SEFAZ prioritária</strong><span>{integer(sefazProcessed)}/{integer(sefazExpected)}</span></div>
        <div className="compact-row"><strong>Catálogos CKAN</strong><span>{integer(data.summary?.ckan_datasets_collected ?? 0)}/{integer(data.summary?.ckan_datasets_expected ?? 6)}</span></div>
        <div className="compact-row"><strong>TCE/BA</strong><span>{integer(data.summary?.tce_datasets_processed ?? 0)} conjunto(s) processado(s)</span></div>
      </div><p className="muted">Indisponibilidade do TCE permanece explícita e nunca é convertida em zero.</p></div>
    </div></section>

    <section className="section compacto"><div className="shell"><details className="card panel"><summary><strong>Fontes, arquivos e detalhes técnicos</strong></summary><div className="section-subblock">
      <p className="muted">Informações de auditoria ficam aqui para não competir com os dados principais.</p>
      <div className="compact-list">
        {[
          ["Receitas", revenue],
          ["Licitações", procurement],
          ["Despesas", expenses],
          ["Pagamentos", payments],
          ["Contratos", contracts],
        ].map(([label, item]) => <div className="compact-row" key={label}><div><strong>{label}</strong><span>{item?.resource?.name || "arquivo não disponível"} · atualização {datePt(item?.resource?.last_modified)}</span></div><span>SHA-256 {shortHash(item?.evidence?.sha256)}</span></div>)}
      </div>
      <p className="muted">Arquivos brutos grandes são processados temporariamente. CPF e nomes de recebedores não são republicados nesta camada agregada.</p>
      <div className="hero-actions"><Link className="button" href="/metodologia">Ver metodologia completa</Link></div>
    </div></details></div></section>
  </>;
}
