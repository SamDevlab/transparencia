import OpportunityExplorer from "../../../components/OpportunityExplorer";
import { loadWebData } from "../../../lib/web-data";

export const metadata = { title: "Oportunidades para estudo produtivo" };

export default function OportunidadesPage() {
  const economy = loadWebData("economy.json");
  const interstate = economy.coverage?.interstate_dependency;

  return <>
    <section className="page-hero"><div className="shell"><span className="eyebrow">Mapa de dependências</span><h1>Cadeias que merecem estudo de desenvolvimento local.</h1><p>A nota de 0 a 100 combina escala das importações, déficit, crescimento, concentração em países fornecedores e presença de exportações relacionadas no mesmo SH4. Ela organiza perguntas; não substitui estudo de viabilidade.</p></div></section>

    <section className="section compacto"><div className="shell"><div className="notice warn"><span>!</span><div><strong>Não é uma lista de “fábricas para abrir”.</strong> Custos, tecnologia, insumos, infraestrutura, produtividade, escala, licenciamento, capital e impactos ambientais precisam ser estudados separadamente.</div></div></div></section>

    <section className="section"><div className="shell"><div className="section-head enxuto"><div><span className="eyebrow">Triagem explicável</span><h2>Por que cada produto recebeu sua nota?</h2></div><p>Clique em um produto para abrir os cinco componentes da nota e os dados que a sustentam.</p></div><OpportunityExplorer /></div></section>

    <section className="section"><div className="shell"><div className="coverage-card"><header><strong>Dependência de outros estados</strong><span className="badge yellow">fonte mapeada</span></header><p>{interstate?.note || "A Matriz de Insumo-Produto da Bahia/SEI está mapeada, mas a camada interestadual ainda não foi normalizada."}</p><div className="results-line"><span>Esta etapa será calculada separadamente do comércio exterior.</span><a href="https://www.ba.gov.br/sei/relatorio-da-matriz-de-insumo-produto" target="_blank" rel="noreferrer">Abrir fonte da SEI ↗</a></div></div></div></section>
  </>;
}
