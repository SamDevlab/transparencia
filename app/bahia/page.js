import Link from "next/link";
import { loadWebData } from "../../lib/web-data";

export const metadata = { title: "Bahia" };

export default function BahiaPage() {
  const economy = loadWebData("economy.json");
  const transparency = loadWebData("bahia-transparency.json");
  const baseline = economy.interstate?.baseline;
  const contractsReady = Boolean(transparency.sefaz?.contracts?.summary?.primary_table);

  return <>
    <section className="page-hero"><div className="shell"><span className="eyebrow">Bahia</span><h1>Economia e transparência estadual no mesmo mapa.</h1><p>Comércio exterior, dependência produtiva e contas públicas aparecem em camadas separadas, cada uma com seu período e sua fonte.</p><div className="hero-actions"><Link className="button primary" href="/economia/bahia">Comércio exterior →</Link><Link className="button" href="/bahia/transparencia">Transparência estadual</Link><Link className="button" href="/bahia/contratos">Contratos estaduais</Link><Link className="button" href="/economia/oportunidades">Dependências produtivas</Link></div></div></section>

    <section className="section compacto"><div className="shell grid grid-4">
      <Link className="coverage-card clicavel" href="/economia/bahia"><header><strong>Comércio exterior</strong><span className={`badge ${economy.bahia ? "green" : "yellow"}`}>{economy.bahia ? "dados disponíveis" : "aguardando coleta"}</span></header><p>Exportações, importações, saldo, produtos e países da Bahia.</p></Link>
      <Link className="coverage-card clicavel" href="/economia/oportunidades"><header><strong>Dependência interestadual</strong><span className="badge green">linha de base histórica</span></header><p>{baseline ? `Estrutura baseada na matriz interestadual de ${baseline.reference_year}, com o ano sempre visível.` : "Fonte estadual mapeada."}</p></Link>
      <Link className="coverage-card clicavel" href="/bahia/transparencia"><header><strong>Transparência estadual</strong><span className={`badge ${transparency.available ? "green" : "yellow"}`}>{transparency.available ? "dados processados" : `${transparency.mappedSources} fontes mapeadas`}</span></header><p>Receitas, despesas, pagamentos, licitações e cobertura das fontes estaduais.</p></Link>
      <Link className="coverage-card clicavel" href="/bahia/contratos"><header><strong>Contratos estaduais</strong><span className={`badge ${contractsReady ? "green" : "yellow"}`}>{contractsReady ? "base processada" : "em processamento"}</span></header><p>Instrumentos, fornecedores e caminho documental até os pagamentos quando há chave oficial.</p></Link>
    </div></section>

    <section className="section"><div className="shell"><div className="notice"><span>●</span><div><strong>As escalas não são misturadas.</strong> Bahia e Salvador possuem fontes, conceitos e períodos próprios. Um dado estadual não é usado para preencher uma lacuna municipal e vice-versa.</div></div></div></section>
  </>;
}
