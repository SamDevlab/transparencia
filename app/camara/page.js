import { brl, integer, loadWebData } from "../../lib/web-data";

export const metadata = { title: "Câmara Municipal" };

function humanMetric(metric) {
  const labels = {
    dotacao_atualizada_total: "Dotação atualizada",
    despesa_empenhada_acumulada_total: "Empenhado acumulado",
    despesa_liquidada_acumulada_total: "Liquidado acumulado",
    despesa_paga_acumulada_total: "Pago acumulado",
    diarias_no_pais_servicos_tecnicos_administrativos: "Diárias no país — agregado CMS",
  };
  return labels[metric] ?? metric.replaceAll("_", " ");
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
          <p>Composição observada, produção legislativa agregada e dados fiscais institucionais. A interface não atribui gasto institucional a vereador sem fonte nominal que faça esse vínculo.</p>
          <div className="kicker-row"><span className="badge">20ª legislatura · 2025–2028</span><span className="badge green">fontes CMS</span><span className="badge yellow">licenças exigem ato específico</span></div>
        </div>
      </section>

      <section className="section">
        <div className="shell grid grid-3">
          <div className="card stat accent"><span className="stat-label">Nomes no cadastro observado</span><div><span className="stat-value">{integer(data.officials.length)}</span><div className="stat-meta">lista geral da CMS no snapshot</div></div></div>
          <div className="card stat"><span className="stat-label">Sessões em 2025</span><div><span className="stat-value">{integer(sessions?.value_numeric)}</span><div className="stat-meta">86 ordinárias, 34 solenes, 32 especiais, 1 extraordinária, 2 itinerantes</div></div></div>
          <div className="card stat blue"><span className="stat-label">Projetos de lei apresentados</span><div><span className="stat-value">{integer(bills?.value_numeric)}</span><div className="stat-meta">vereadores + Mesa Executiva, agregado de 2025</div></div></div>
        </div>
      </section>

      <section className="section">
        <div className="shell">
          <div className="notice warn" style={{ marginBottom: 22 }}><span>!</span><div><strong>Composição ≠ exercício em cada data.</strong> A página geral da Câmara listava 43 nomes, mas licenças e substituições precisam ser confirmadas pelos atos correspondentes antes de análises individuais.</div></div>
          <div className="section-head"><div><span className="eyebrow">Representação</span><h2>Nomes exibidos pela Câmara</h2></div><p>Partido e legislatura são mantidos conforme o seed oficial do projeto.</p></div>
          <div className="people-grid">
            {data.officials.map((person) => (
              <a className="person-card" href={person.source_url} target="_blank" rel="noreferrer" key={`${person.name}-${person.party}`}>
                <strong>{person.name}</strong>
                <span>{person.party || "Partido não informado"} · {person.office || "Vereador(a)"}</span>
              </a>
            ))}
          </div>
        </div>
      </section>

      <section className="section">
        <div className="shell">
          <div className="section-head"><div><span className="eyebrow">Prestação de contas</span><h2>Dados institucionais da Câmara</h2></div><p>Competência 11/2025. Valores extraídos do demonstrativo oficial e mantidos com estágio contábil.</p></div>
          <div className="grid grid-3">
            {cmsFiscal.map((row) => (
              <a className="card stat" href={row.source_url} target="_blank" rel="noreferrer" key={row.metric}>
                <span className="stat-label">{humanMetric(row.metric)}</span>
                <div><span className="stat-value mono" style={{ fontSize: 28 }}>{brl(row.value_brl)}</span><div className="stat-meta">{row.budget_stage} · fonte oficial ↗</div></div>
              </a>
            ))}
          </div>
          <div className="notice warn" style={{ marginTop: 18 }}><span>!</span><div>Os <strong>R$ 55.800,00 em diárias</strong> são um gasto agregado da Câmara no demonstrativo. O frontend não atribui esse valor a nenhum vereador específico.</div></div>
        </div>
      </section>

      <section className="section"><div className="shell"><div className="coverage-card"><header><strong>Empenhos da CMS</strong><span className="badge yellow">regra de completude</span></header><p>O coletor usa a paginação real do ScriptCase e só marca uma coleta como completa quando a fonte chega ao fim e cada número de empenho visível foi normalizado. Um snapshot antigo subcapturado foi explicitamente invalidado.</p></div></div></section>
    </>
  );
}
