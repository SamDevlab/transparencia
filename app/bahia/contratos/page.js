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
  const coverage = data.coverage?.sefaz_data?.contratos;

  if (!primary) {
    return <>
      <section className="page-hero"><div className="shell"><span className="eyebrow">Estado da Bahia</span><h1>Contratos estaduais</h1><p>O recurso oficial está mapeado, mas nenhum total será exibido até o ZIP de contratos passar pelo parser e a tabela principal ser identificada.</p><div className="hero-actions"><Link className="button" href="/bahia/transparencia">← Transparência estadual</Link></div></div></section>
      <section className="section compacto"><div className="shell"><div className="notice warn"><span>!</span><div><strong>{coverage?.status === "unavailable" ? "Coleta indisponível nesta execução." : "Coleta em processamento."}</strong> {coverage?.error || "A ausência do resumo não é interpretada como zero contratos."}</div></div></div></section>
    </>;
  }

  const fields = primary.schema?.detected_fields ?? {};
  const suppliers = primary.top_suppliers_cnpj_only ?? [];
  const agencies = primary.top_agencies ?? [];
  const statuses = primary.top_statuses ?? [];
  const contractValue = primary.contract_value;

  return <>
    <section className="page-hero"><div className="shell"><span className="eyebrow">Estado da Bahia · SEFAZ/FIPLAN</span><h1>Contratos estaduais {summary.selected_year || ""}</h1><p>Contratos são tratados como uma camada própria. Aditivos e tabelas relacionadas não são contados como novos contratos, e vínculos usam somente identificadores oficiais normalizados.</p><div className="hero-actions"><Link className="button" href="/bahia/transparencia">← Transparência estadual</Link></div><div className="kicker-row"><span className="badge green">base processada</span><span className="badge">{integer(primary.selected_rows)} registros no recorte</span><span className="badge">{integer(primary.instrument_index?.length ?? 0)} chaves de instrumento</span><span className="badge">{integer(primary.process_ids?.length ?? 0)} chaves de processo</span></div></div></section>

    <section className="section compacto"><div className="shell grid grid-4"><div className="card stat accent"><span className="stat-label">Contratos/registros em 2026</span><div><span className="stat-value">{integer(primary.selected_rows)}</span><div className="stat-meta">{primary.member}</div></div></div><div className="card stat"><span className="stat-label">Valor no campo contratual</span><div><span className="stat-value">{contractValue?.sum != null ? brl(contractValue.sum, { compact: true }) : "—"}</span><div className="stat-meta">{contractValue?.field || "campo não identificado"}</div></div></div><div className="card stat"><span className="stat-label">CNPJs empresariais agregados</span><div><span className="stat-value">{integer(suppliers.length)}</span><div className="stat-meta">top publicados; CPF não é republicado</div></div></div><div className="card stat blue"><span className="stat-label">Membros do ZIP</span><div><span className="stat-value">{integer(summary.archive?.processed_tabular_members ?? 0)}/{integer(summary.archive?.candidate_tabular_members ?? 0)}</span><div className="stat-meta">tabelas processadas</div></div></div></div></section>

    <section className="section"><div className="shell grid grid-2"><div className="card panel"><div className="panel-title"><h3>Campos oficiais identificados</h3><span>esquema real</span></div><div className="compact-list">{[
      ["Contrato/instrumento", fields.contract],
      ["Processo", fields.process],
      ["Órgão", fields.agency],
      ["Fornecedor", fields.supplier],
      ["Documento do fornecedor", fields.supplier_document],
      ["Situação", fields.status],
      ["Objeto", fields.object],
      ["Modalidade", fields.modality],
      ["Valor contratual", fields.contract_value],
    ].map(([label, value]) => <div className="compact-row" key={label}><strong>{label}</strong><span>{value || "não identificado"}</span></div>)}</div></div><div className="card panel"><div className="panel-title"><h3>Rastreabilidade</h3><span>evidência</span></div><p>SHA-256 do ZIP oficial: <code>{shortHash(contracts.evidence?.sha256)}</code></p><p className="muted">Arquivo: {contracts.resource?.name || "Contratos.zip"} · atualização da fonte: {contracts.resource?.last_modified || "não informada"}.</p><p className="muted">Regra de identidade: remoção de pontuação/espaço e padronização de maiúsculas. Não existe correspondência aproximada.</p></div></div></section>

    {agencies.length > 0 && <section className="section"><div className="shell"><div className="section-head enxuto"><div><span className="eyebrow">Órgãos</span><h2>Maiores agregados no recorte</h2></div><p>Os valores são agregados somente pela tabela principal e pelo campo contratual identificado.</p></div><div className="compact-list">{agencies.slice(0, 20).map((item) => <div className="compact-row" key={item.name}><div><strong>{item.name}</strong><span>{integer(item.rows)} registro(s)</span></div><strong>{brl(item.value)}</strong></div>)}</div></div></section>}

    {suppliers.length > 0 && <section className="section"><div className="shell"><div className="section-head enxuto"><div><span className="eyebrow">Fornecedores empresariais</span><h2>Maiores agregados por CNPJ</h2></div><p>A camada pública preserva CNPJ empresarial. CPF é deliberadamente excluído desse resumo.</p></div><div className="compact-list">{suppliers.slice(0, 30).map((item) => <div className="compact-row" key={item.cnpj}><div><strong>{item.name}</strong><span>CNPJ {item.cnpj} · {integer(item.contracts)} contrato(s) · {integer(item.rows)} registro(s)</span></div><strong>{brl(item.value)}</strong></div>)}</div></div></section>}

    {statuses.length > 0 && <section className="section compacto"><div className="shell"><div className="section-head enxuto"><div><span className="eyebrow">Situação</span><h2>Estados publicados pela fonte</h2></div></div><div className="kicker-row">{statuses.slice(0, 15).map((item) => <span className="badge" key={item.name}>{item.name}: {integer(item.rows)}</span>)}</div></div></section>}

    <section className="section compacto"><div className="shell"><div className="notice warn"><span>!</span><div><strong>Interpretação:</strong> valor alto, fornecedor recorrente ou muitos contratos são sinais descritivos para consulta, não evidência de irregularidade. Aditivos permanecem separados e a base de contratos não é igualada automaticamente aos pagamentos.</div></div></div></section>
  </>;
}
