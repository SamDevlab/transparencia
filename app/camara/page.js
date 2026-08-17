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

  return (
    <>
      <section className="page-hero">
        <div className="shell">
          <span className="eyebrow">Poder Legislativo</span>
          <h1>Câmara Municipal de Salvador.</h1>
          <p>Atividade legislativa e prestação de contas institucional. Vereadores, funções da Mesa Diretora e contatos ficam reunidos na página de agentes públicos.</p>
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

      <section className="section">
        <div className="shell">
          <div className="section-head enxuto"><div><span className="eyebrow">Prestação de contas</span><h2>Valores institucionais da Câmara</h2></div><p>Competência 11/2025. Cada cartão abre o documento oficial correspondente.</p></div>
          <div className="grid grid-3">
            {cmsFiscal.map((row) => (
              <a className="card stat" href={row.source_url} target="_blank" rel="noreferrer" key={row.metric}>
                <span className="stat-label">{humanMetric(row.metric)}</span>
                <div><span className="stat-value mono" style={{ fontSize: 28 }}>{brl(row.value_brl)}</span><div className="stat-meta">{stageLabel(row.budget_stage)} · abrir fonte ↗</div></div>
              </a>
            ))}
          </div>
          <div className="notice warn" style={{ marginTop: 18 }}><span>!</span><div>Os <strong>R$ 55.800,00 em diárias</strong> são um total institucional da Câmara. O sistema não distribui esse valor entre vereadores sem documento nominal.</div></div>
        </div>
      </section>
    </>
  );
}
