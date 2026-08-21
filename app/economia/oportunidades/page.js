import OpportunityExplorer from "../../../components/OpportunityExplorer";
import { loadWebData } from "../../../lib/web-data";

export const metadata = { title: "Oportunidades para estudo produtivo" };

function percent(value) {
  return new Intl.NumberFormat("pt-BR", { style: "percent", maximumFractionDigits: 2 }).format(Number(value ?? 0));
}

export default function OportunidadesPage() {
  const economy = loadWebData("economy.json");
  const interstate = economy.interstate;
  const baseline = interstate?.baseline;
  const metrics = baseline?.metrics ?? {};
  const sectors = interstate?.keySectors?.sectors ?? [];

  return <>
    <section className="page-hero"><div className="shell"><span className="eyebrow">Mapa de dependências</span><h1>Cadeias que merecem estudo de desenvolvimento local.</h1><p>A triagem do comércio exterior combina escala das importações, déficit, crescimento, concentração em países fornecedores e presença de exportações relacionadas. A dependência entre estados é tratada em uma camada diferente, com evidência da SEI.</p></div></section>

    <section className="section compacto"><div className="shell"><div className="notice warn"><span>!</span><div><strong>Não é uma lista de “fábricas para abrir”.</strong> Custos, tecnologia, insumos, infraestrutura, produtividade, escala, licenciamento, capital, mercado e impactos ambientais precisam ser estudados separadamente.</div></div></div></section>

    <section className="section"><div className="shell"><div className="section-head enxuto"><div><span className="eyebrow">Triagem explicável</span><h2>Por que cada produto recebeu sua nota?</h2></div><p>Clique em um produto para abrir os componentes da nota e os dados que a sustentam.</p></div><OpportunityExplorer /></div></section>

    <section className="section"><div className="shell">
      <div className="section-head enxuto"><div><span className="eyebrow">Dependência de outros estados</span><h2>Linha de base estrutural da Bahia</h2></div><p>Matriz interestadual de {baseline?.reference_year ?? "—"}. Os números abaixo não são apresentados como fotografia de 2026.</p></div>
      {baseline ? <>
        <div className="grid grid-4">
          <div className="card stat accent"><span className="stat-label">Valor agregado da própria Bahia</span><div><span className="stat-value">{percent(metrics.domestic_value_added_share_in_bahia_interstate_exports)}</span><div className="stat-meta">nas exportações interestaduais do estudo</div></div></div>
          <div className="card stat"><span className="stat-label">Valor agregado vindo de outros estados</span><div><span className="stat-value">{percent(metrics.other_states_value_added_share_in_bahia_interstate_exports)}</span><div className="stat-meta">insumos interestaduais incorporados no estudo</div></div></div>
          <div className="card stat blue"><span className="stat-label">Participação para trás</span><div><span className="stat-value">{percent(metrics.backward_participation_fva_over_exports)}</span><div className="stat-meta">dependência de insumos de outras regiões</div></div></div>
          <div className="card stat"><span className="stat-label">Participação para frente</span><div><span className="stat-value">{percent(metrics.forward_participation_dvx_over_exports)}</span><div className="stat-meta">valor baiano incorporado por outras regiões</div></div></div>
        </div>
        <div className="notice warn" style={{ marginTop: 18 }}><span>!</span><div><strong>Linha de base histórica.</strong> {baseline.interpretation?.warning}</div></div>
      </> : <div className="card empty">A linha de base interestadual ainda não está disponível nesta publicação.</div>}
    </div></section>

    <section className="section"><div className="shell"><div className="section-head enxuto"><div><span className="eyebrow">Encadeamentos produtivos</span><h2>Setores-chave identificados pela MIP Bahia</h2></div><p>Referência estrutural de {interstate?.keySectors?.reference_year ?? "—"}; serve para priorizar estudos, não para medir capacidade atual.</p></div>
      <div className="card table-card"><div className="table-wrap"><table><thead><tr><th>Setor</th><th>Ligação para frente</th><th>Ligação para trás</th><th>Leitura</th></tr></thead><tbody>{sectors.map((row) => <tr key={row.sector}><td><strong>{row.sector}</strong></td><td className="mono">{Number(row.forward_linkage).toLocaleString("pt-BR", { maximumFractionDigits: 3 })}</td><td className="mono">{Number(row.backward_linkage).toLocaleString("pt-BR", { maximumFractionDigits: 3 })}</td><td>{row.forward_linkage > 1 && row.backward_linkage > 1 ? "Setor-chave na metodologia publicada" : "Encadeamento estrutural"}</td></tr>)}</tbody></table></div></div>
      <div className="results-line"><span>As referências históricas são deliberadamente separadas dos dados correntes do Comex Stat.</span><a href={baseline?.source?.url || "https://www.ba.gov.br/sei/relatorio-da-matriz-de-insumo-produto"} target="_blank" rel="noreferrer">Abrir fonte da SEI ↗</a></div>
    </div></section>
  </>;
}
