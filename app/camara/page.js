import Link from "next/link";
import { brl, integer, loadWebData } from "../../lib/web-data";

export const metadata = { title: "Câmara Municipal" };

function humanMetric(metric) {
  const labels = {
    dotacao_atualizada_total: "Dotação atualizada",
    despesa_empenhada_acumulada_total: "Empenhado acumulado",
    despesa_liquidada_acumulada_total: "Liquidado acumulado",
    despesa_paga_acumulada_total: "Pago acumulado",
    diarias_no_pais_servicos_tecnicos_administrativos: "Diárias no país — total da Câmara",
  };
  return labels[metric] ?? metric.replaceAll("_", " ");
}

function stageLabel(stage) {
  const labels = {
    appropriation: "dotação",
    committed: "empenhado",
    liquidated: "liquidado",
    paid: "pago",
    planned: "previsto",
    realized_revenue: "receita realizada",
    reported_executed: "execução reportada",
    reported_result: "resultado reportado",
  };
  return labels[stage] ?? "valor publicado";
}

export default function CamaraPage() {
  const data = loadWebData("camara.json");
  const sessions = data.legislative.find((row) => row.metric === "sessoes_realizadas");
  const bills = data.legislative.find((row) => row.metric === "projetos_lei_vereadores_mesa_apresentados");
  const cmsFiscal = data.fiscal.filter((row) => row.entity === "Câmara Municipal de Salvador");
  const ledger = data.commitmentLedger;
  const auxiliary = data.auxiliary;

  return (
    <>
      <section className="page-hero">
        <div className="shell">
          <span className="eyebrow">Poder Legislativo</span>
          <h1>Câmara Municipal de Salvador.</h1>
          <p>Atividade legislativa e prestação de contas institucional. Vereadores, funções da Mesa Diretora e contatos ficam reunidos na página de agentes públicos. Dados contábeis institucionais não são automaticamente atribuídos a vereadores.</p>
          <div className="hero-actions"><Link className="button primary" href="/agentes?busca=">Ver vereadores e contatos →</Link></div>
        </div>
      </section>

      <section className="section compacto">
        <div className="shell grid grid-3">
          <div className="card stat accent"><span className="stat-label">Vereadores no cadastro</span><div><span className="stat-value">{integer(data.officials.length)}</span><div className="stat-meta">20ª Legislatura · 2025–2028</div></div></div>
          <div className="card stat"><span className="stat-label">Sessões em 2025</span><div><span className="stat-value">{integer(sessions?.value_numeric)}</span><div className="stat-meta">86 ordinárias · 34 solenes · 32 especiais</div></div></div>
          <div className="card stat blue"><span className="stat-label">Projetos de lei apresentados</span><div><span className="stat-value">{integer(bills?.value_numeric)}</span><div className="stat-meta">vereadores + Mesa Executiva em 2025</div></div></div>
        </div>
      </section>

      {ledger && <section className="section">
        <div className="shell">
          <div className="section-head enxuto"><div><span className="eyebrow">Empenhos atuais</span><h2>Ledger público da Câmara, preservando a etapa contábil.</h2></div><p>Observado em {ledger.asOf}. {ledger.completeForDefaultPublicView ? "A visão pública padrão foi percorrida até o esgotamento da fonte." : "A cobertura permanece parcial."}</p></div>
          <div className="grid grid-4">
            <div className="card stat accent"><span className="stat-label">Empenhos normalizados</span><div><span className="stat-value">{integer(ledger.records)}</span><div className="stat-meta">{integer(ledger.pagesWithRecords)} páginas com registros</div></div></div>
            <div className="card stat"><span className="stat-label">Valor empenhado no ledger</span><div><span className="stat-value">{brl(ledger.totalCommitted, { compact: true })}</span><div className="stat-meta">soma dos registros classificados como empenho</div></div></div>
            <div className="card stat"><span className="stat-label">Verba compensatória</span><div><span className="stat-value">{brl(ledger.parliamentaryCompensatoryAllowance?.committedValue ?? 0, { compact: true })}</span><div className="stat-meta">{integer(ledger.parliamentaryCompensatoryAllowance?.records ?? 0)} empenho(s) identificados pelo texto da fonte</div></div></div>
            <div className="card stat"><span className="stat-label">Relacionados a diárias/viagem</span><div><span className="stat-value">{brl(ledger.travelRelated?.committedValue ?? 0, { compact: true })}</span><div className="stat-meta">{integer(ledger.travelRelated?.records ?? 0)} empenho(s) sinalizados</div></div></div>
          </div>
          <div className="grid grid-2" style={{ marginTop: 18 }}>
            <div className="notice"><span>✓</span><div><strong>{ledger.completeForDefaultPublicView ? "Cobertura completa para a visão pública padrão." : "Cobertura parcial."}</strong> {ledger.coverageNote}</div></div>
            <div className="notice"><span>i</span><div><strong>Contabilidade e privacidade:</strong> {ledger.accountingRule} {ledger.privacyRule}</div></div>
          </div>
          <div className="results-line"><span>Parser de registros visíveis: {ledger.parserCompleteForVisibleRecords ? "completo" : "incompleto"} · fonte esgotada: {ledger.sourceExhausted ? "sim" : "não"}</span><a href={ledger.sourceUrl} target="_blank" rel="noreferrer">Abrir ledger oficial ↗</a></div>
        </div>
      </section>}

      {auxiliary && <section className="section">
        <div className="shell">
          <div className="section-head enxuto"><div><span className="eyebrow">Fontes auxiliares</span><h2>Viagens, documentos e certames com cobertura separada.</h2></div><p>Observado em {auxiliary.asOf}. Cada fonte mantém seu próprio status.</p></div>
          <div className="grid grid-3">
            <div className="card panel"><div className="panel-title"><h3>Despesas de viagem</h3><span>{auxiliary.travel?.complete ? "completo para a rota" : "parcial"}</span></div><div className="stat-value mono" style={{ fontSize: 28 }}>{brl(auxiliary.travel?.totalValue ?? 0)}</div><p>{integer(auxiliary.travel?.records ?? 0)} registros em {integer(auxiliary.travel?.pages ?? 0)} páginas. {integer(auxiliary.travel?.recordsWithProcessNumber ?? 0)} trazem número de processo.</p><p className="muted">{auxiliary.travel?.publicDetailRule}</p><a className="button" href="https://www.cms.ba.gov.br/transparencia/despesas-viagem" target="_blank" rel="noreferrer">Abrir fonte →</a></div>
            <div className="card panel"><div className="panel-title"><h3>Documentos de transparência</h3><span>{auxiliary.documents?.complete ? "catálogo coletado" : "parcial"}</span></div><div className="stat-value mono" style={{ fontSize: 28 }}>{integer(auxiliary.documents?.records ?? 0)}</div><p>links de prestação de contas e execução orçamentária/financeira preservados.</p><p className="muted">{auxiliary.documents?.publicDetailRule}</p><a className="button" href="https://www.cms.ba.gov.br/transparencia" target="_blank" rel="noreferrer">Abrir transparência da Câmara →</a></div>
            <div className="card panel"><div className="panel-title"><h3>Certames</h3><span>parcial</span></div><div className="stat-value mono" style={{ fontSize: 28 }}>{integer(auxiliary.certames?.recordsVisible ?? 0)}</div><p>itens normalizados apenas da página atualmente visível no servidor.</p><p className="muted">{auxiliary.certames?.coverageRule}</p><a className="button" href="https://cmsalvador.sys.inf.br/ca/licitacao/" target="_blank" rel="noreferrer">Abrir certames →</a></div>
          </div>
          {auxiliary.certames?.rows?.length > 0 && <div className="card table-card" style={{ marginTop: 18 }}><div className="table-wrap"><table><thead><tr><th>Modalidade</th><th>Número</th><th>Objeto</th><th>Status visível</th></tr></thead><tbody>{auxiliary.certames.rows.map((row, index) => <tr key={`${row.noticeNumber}-${index}`}><td>{row.modality || "—"}</td><td className="mono">{row.noticeNumber || "—"}</td><td className="object-cell">{row.object || "—"}</td><td>{row.latestStatusText || "—"}</td></tr>)}</tbody></table></div></div>}
        </div>
      </section>}

      <section className="section">
        <div className="shell">
          <div className="section-head enxuto"><div><span className="eyebrow">Prestação de contas histórica</span><h2>Valores institucionais da Câmara</h2></div><p>Competência 11/2025. Cada cartão abre o documento oficial correspondente.</p></div>
          <div className="grid grid-3">
            {cmsFiscal.map((row) => (
              <a className="card stat" href={row.source_url} target="_blank" rel="noreferrer" key={row.metric}>
                <span className="stat-label">{humanMetric(row.metric)}</span>
                <div><span className="stat-value mono" style={{ fontSize: 28 }}>{brl(row.value_brl)}</span><div className="stat-meta">{stageLabel(row.budget_stage)} · abrir fonte ↗</div></div>
              </a>
            ))}
          </div>
          <div className="notice warn" style={{ marginTop: 18 }}><span>!</span><div>Os <strong>R$ 55.800,00 em diárias</strong> do documento histórico são um total institucional da Câmara. O sistema não distribui esse valor entre vereadores sem documento nominal.</div></div>
        </div>
      </section>
    </>
  );
}
