import { brl, integer, loadWebData } from "../../../lib/web-data";

export const metadata = { title: "Transparência estadual da Bahia" };

function statusLabel(value) {
  return {
    metadata_collected: "metadados coletados",
    processed: "processado",
    mapped: "fonte mapeada",
    unavailable: "indisponível nesta coleta",
    sources_mapped: "fontes mapeadas",
    partial: "parcial",
    partial_with_verified_sources: "parcial com fontes verificadas",
    complete_for_metadata_collection: "catálogo atualizado",
    complete_for_defined_collection: "rotina processada",
  }[value] ?? value ?? "não informado";
}

function tone(value) {
  if (["metadata_collected", "processed", "complete_for_metadata_collection", "complete_for_defined_collection"].includes(value)) return "green";
  if (["mapped", "sources_mapped", "partial", "partial_with_verified_sources", "not_run"].includes(value)) return "yellow";
  if (value === "unavailable") return "red";
  return "";
}

function datePt(value) {
  if (!value) return "—";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? String(value) : new Intl.DateTimeFormat("pt-BR", { dateStyle: "short", timeStyle: "short", timeZone: "America/Bahia" }).format(date);
}

export default function BahiaTransparenciaPage() {
  const data = loadWebData("bahia-transparency.json");
  const expenseTotals = data.tce?.expenses?.summary?.totals;
  const summary = data.summary ?? {};

  return <>
    <section className="page-hero"><div className="shell"><span className="eyebrow">Estado da Bahia</span><h1>Transparência estadual com cobertura visível.</h1><p>Esta área acompanha fontes estaduais separadamente da Prefeitura de Salvador. Receitas, despesas, pagamentos, contratos, licitações, diárias e dados do TCE entram com status e evidência próprios.</p><div className="kicker-row"><span className={`badge ${data.available ? "green" : "yellow"}`}>{data.available ? `snapshot ${data.snapshot}` : "primeiro snapshot em coleta"}</span><span className={`badge ${tone(data.status)}`}>{data.statusLabel || statusLabel(data.status)}</span><span className="badge">{integer(data.mappedSources)} fontes oficiais mapeadas</span></div></div></section>

    {data.available && <section className="section compacto"><div className="shell grid grid-3"><div className="card stat accent"><span className="stat-label">Catálogos SEFAZ/CKAN</span><div><span className="stat-value">{integer(summary.ckan_datasets_collected)}/{integer(summary.ckan_datasets_expected)}</span><div className="stat-meta">fontes consultadas nesta coleta</div></div></div><div className="card stat"><span className="stat-label">Conjuntos TCE processados</span><div><span className="stat-value">{integer(summary.tce_datasets_processed)}</span><div className="stat-meta">enriquecimento separado</div></div></div><div className="card stat blue"><span className="stat-label">Modo da coleta</span><div><span className="stat-value" style={{fontSize:"1.1rem"}}>{data.collectionMode === "metadata_only" ? "Metadados" : "Completo"}</span><div className="stat-meta">falha externa nunca vira zero</div></div></div></div></section>}

    {expenseTotals && <section className="section compacto"><div className="shell"><div className="section-head enxuto"><div><span className="eyebrow">TCE/BA</span><h2>Execução detalhada processada</h2></div><p>Os estágios permanecem separados.</p></div><div className="grid grid-4"><div className="card stat"><span className="stat-label">Linhas processadas</span><div><span className="stat-value">{integer(expenseTotals.rows)}</span><div className="stat-meta">arquivo anual do TCE</div></div></div><div className="card stat accent"><span className="stat-label">Valor empenhado</span><div><span className="stat-value">{brl(expenseTotals.committed, { compact: true })}</span><div className="stat-meta">soma do campo de empenho</div></div></div><div className="card stat"><span className="stat-label">Pagamento com retenções</span><div><span className="stat-value">{brl(expenseTotals.gross_paid, { compact: true })}</span><div className="stat-meta">campo publicado pelo TCE</div></div></div><div className="card stat blue"><span className="stat-label">Pagamento líquido</span><div><span className="stat-value">{brl(expenseTotals.net_paid, { compact: true })}</span><div className="stat-meta">ao credor</div></div></div></div></div></section>}

    <section className="section"><div className="shell"><div className="section-head enxuto"><div><span className="eyebrow">Catálogo estadual</span><h2>O que já está sob acompanhamento</h2></div><p>“Metadados coletados” significa que o catálogo oficial foi consultado e os recursos publicados foram identificados; não significa que todas as linhas desses arquivos já foram importadas.</p></div><div className="coverage-grid source-coverage-grid">{(data.sources ?? []).map((item) => {
      const current = item.status || "mapped";
      const resources = item.ckan?.resources ?? [];
      const tlsFallback = item.transport?.tls_verified === false;
      return <article className="coverage-card source-card" key={item.id}><header><strong>{item.title}</strong><span className={`badge ${tone(current)}`}>{statusLabel(current)}</span></header><p>{item.coverage || item.ckan?.notes || "Fonte oficial estadual."}</p>{item.ckan?.metadata_modified && <p className="muted">Metadados atualizados em {datePt(item.ckan.metadata_modified)}.</p>}{tlsFallback && <div className="notice warn" style={{marginTop:"0.7rem"}}><span>!</span><div>O runner não validou a cadeia TLS do portal. A consulta foi repetida no <strong>mesmo domínio oficial</strong> e o fallback ficou registrado.</div></div>}{resources.length > 0 && <details style={{marginTop:"0.8rem"}}><summary>Ver {integer(resources.length)} recurso(s) publicados</summary><div className="compact-list" style={{marginTop:"0.6rem"}}>{resources.map((resource) => <a className="compact-row" href={resource.url} target="_blank" rel="noreferrer" key={resource.id || resource.url}><div><strong>{resource.name || "Recurso oficial"}</strong><span>{resource.format || resource.mimetype || "formato não informado"}</span></div><span>abrir ↗</span></a>)}</div></details>}<div className="source-foot"><span>{item.publisher || item.ckan?.organization}</span><a href={item.dataset_url || item.documentation_url || item.access_url} target="_blank" rel="noreferrer">Abrir fonte ↗</a></div></article>;
    })}</div></div></section>

    <section className="section"><div className="shell grid grid-2"><div className="card panel"><div className="panel-title"><h3>Contratos do TCE/BA</h3><span>{statusLabel(data.coverage?.tce?.contracts?.status || data.coverage?.tce?.status)}</span></div>{data.tce?.contracts ? <><p><strong>{integer(data.tce.contracts.summary?.rows)}</strong> linhas processadas na fonte.</p><p className="muted">Valor declarado somado: {brl(data.tce.contracts.summary?.declared_value_sum)}</p></> : <p className="muted">O arquivo ainda não foi processado nesta publicação. A ausência não é interpretada como zero contratos.</p>}</div><div className="card panel"><div className="panel-title"><h3>Licitações do TCE/BA</h3><span>{statusLabel(data.coverage?.tce?.procurements?.status || data.coverage?.tce?.status)}</span></div>{data.tce?.procurements ? <><p><strong>{integer(data.tce.procurements.summary?.rows)}</strong> linhas processadas na fonte.</p><p className="muted">Valor declarado somado: {brl(data.tce.procurements.summary?.declared_value_sum)}</p></> : <p className="muted">O arquivo ainda não foi processado nesta publicação. A ausência não é interpretada como zero procedimentos.</p>}</div></div></section>

    <section className="section compacto"><div className="shell"><div className="notice warn"><span>!</span><div><strong>Privacidade e rastreabilidade:</strong> arquivos grandes do TCE são baixados temporariamente para cálculo de resumo e hash. O projeto não republica amostras brutas contendo CPF/CNPJ nesta camada.</div></div></div></section>
  </>;
}
