import Link from "next/link";
import { loadWebData } from "../../lib/web-data";

export const metadata = { title: "Economia da Bahia e Salvador" };

function usd(value, compact = true) {
  return new Intl.NumberFormat("pt-BR", { style: "currency", currency: "USD", notation: compact ? "compact" : "standard", maximumFractionDigits: compact ? 1 : 2 }).format(Number(value ?? 0));
}

function Summary({ title, data, subtitle }) {
  if (!data) return <div className="card economy-summary unavailable"><span className="eyebrow">{title}</span><h3>Aguardando primeiro snapshot</h3><p>{subtitle}</p></div>;
  const s = data.summary;
  return <div className="card economy-summary">
    <span className="eyebrow">{title}</span>
    <h3>{usd(s.balance_fob)} de saldo</h3>
    <p>{subtitle}</p>
    <div className="economy-metrics"><div><span>Exportações</span><strong>{usd(s.exports_fob)}</strong></div><div><span>Importações</span><strong>{usd(s.imports_fob)}</strong></div><div><span>Corrente</span><strong>{usd(s.trade_flow_fob)}</strong></div></div>
  </div>;
}

export default function EconomiaPage() {
  const data = loadWebData("economy.json");
  const sourceMonth = data.coverage?.bahia?.source_month;
  const sourceYear = data.coverage?.bahia?.source_year;

  return <>
    <section className="page-hero economy-hero"><div className="shell">
      <span className="eyebrow">Inteligência econômica pública</span>
      <h1>O que a Bahia vende, compra e onde existem dependências para estudar.</h1>
      <p>Comércio exterior da Bahia e de empresas domiciliadas em Salvador, organizado por produto, país, saldo e concentração. A triagem produtiva ajuda a escolher o que investigar — não decide onde investir.</p>
      <div className="hero-actions"><Link className="button primary" href="/economia/oportunidades">Ver oportunidades para estudo →</Link><Link className="button" href="/economia/bahia">Explorar Bahia</Link><Link className="button" href="/economia/salvador">Explorar Salvador</Link></div>
    </div></section>

    <section className="section compacto"><div className="shell">
      <div className="notice"><span>●</span><div><strong>Fonte oficial:</strong> MDIC / Comex Stat{sourceMonth && sourceYear ? `, dados disponíveis no snapshot até ${String(sourceMonth).padStart(2, "0")}/${sourceYear}` : ""}. Valores em US$ FOB.</div></div>
    </div></section>

    <section className="section"><div className="shell grid grid-2">
      <Summary title="Bahia" data={data.bahia} subtitle="Exportações por UF produtora; importações pelo domicílio fiscal do importador." />
      <Summary title="Salvador" data={data.salvador} subtitle="Empresas domiciliadas em Salvador. Não significa necessariamente produção ou consumo físico na capital." />
    </div></section>

    <section className="section"><div className="shell">
      <div className="section-head enxuto"><div><span className="eyebrow">Escolha a pergunta</span><h2>Da balança comercial à capacidade produtiva</h2></div></div>
      <div className="question-grid">
        <Link className="question-card" href="/economia/bahia"><span>BA</span><div><strong>O que a Bahia mais importa e exporta?</strong><p>Produtos SH4, países, saldo e evolução mensal.</p></div></Link>
        <Link className="question-card" href="/economia/salvador"><span>SSA</span><div><strong>O que empresas de Salvador compram e vendem ao mundo?</strong><p>Consulta municipal com a metodologia correta do Comex Stat.</p></div></Link>
        <Link className="question-card" href="/economia/oportunidades"><span>↗</span><div><strong>Quais cadeias merecem estudo?</strong><p>Triagem por importação, déficit, crescimento, concentração e exportação relacionada.</p></div></Link>
        <Link className="question-card" href="/transparencia"><span>✓</span><div><strong>Quão completos estão os dados?</strong><p>Veja fonte, atualização e limitações de cada conjunto público.</p></div></Link>
      </div>
    </div></section>

    <section className="section"><div className="shell"><div className="notice warn"><span>!</span><div><strong>Dependência de outros estados é outra pergunta.</strong> Comércio exterior mede relações com outros países. A dependência interestadual será quantificada separadamente com a Matriz de Insumo-Produto da Bahia/SEI; o sistema não mistura as duas coisas.</div></div></div></section>
  </>;
}
