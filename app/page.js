import Link from "next/link";
import { brl, integer, loadWebData, parseBrlText, dateBR } from "../lib/web-data";

export const metadata = { title: "Visão geral" };

function Stat({ label, value, meta, tone = "" }) {
  return <div className={`card stat ${tone}`}><span className="stat-label">{label}</span><div><span className="stat-value mono">{value}</span><div className="stat-meta">{meta}</div></div></div>;
}

const atalhos = [
  ["/buscar", "⌕", "Buscar pessoa, empresa ou processo", "Pesquise CNPJ, contrato, órgão, agente público, produto ou código sem trocar de página."],
  ["/dinheiro", "R$", "Para onde foi o dinheiro em Salvador?", "Parta dos totais e avance até processos, contratos e fornecedores quando houver vínculo comprovado."],
  ["/bahia/transparencia", "BA", "Como estão as contas da Bahia?", "Receitas, despesas, licitações, contratos e pagamentos estaduais em uma visão enxuta."],
  ["/economia/oportunidades", "↗", "Onde a Bahia depende de fora?", "Importações, déficit, concentração e cadeias que merecem estudo produtivo."],
  ["/economia/salvador", "SSA", "O que Salvador compra e vende ao mundo?", "Comércio exterior das empresas domiciliadas na capital, por produto e país."],
  ["/agentes", "◎", "Quem administra Salvador?", "Prefeito, vice, secretários verificados e vereadores, com fonte oficial."],
];

export default function HomePage() {
  const data = loadWebData("dashboard.json");
  const finance = data.finance;
  const receita = parseBrlText(finance.revenue_totalizer?.Realizado);
  const pago = parseBrlText(finance.expense_totalizer?.Pago);
  const aquisicoes = parseBrlText(data.acquisitions.summary?.api_reported_total_value_brl_text);

  return <>
    <section className="hero hero-clean"><div className="shell"><span className="eyebrow">Transparência e economia sem labirinto</span><h1>O que você quer descobrir sobre Salvador e a Bahia?</h1><p>Comece pela pergunta. O sistema organiza a referência, o conceito contábil e a fonte oficial sem exigir que você saiba em qual portal procurar.</p><div className="hero-actions"><Link className="button primary" href="/buscar">Começar uma busca →</Link><Link className="button" href="/dinheiro">Seguir o dinheiro</Link><Link className="button" href="/economia">Explorar economia</Link></div></div></section>

    <section className="section compacto"><div className="shell"><div className="notice"><span>●</span><div><strong>Cobertura sempre visível.</strong> Salvador usa a coleta auditada mais recente; Bahia e comércio exterior mantêm seus próprios períodos e fontes. <Link href="/transparencia">Ver cobertura dos dados</Link>.</div></div></div></section>

    <section className="section"><div className="shell"><div className="atalhos-grid">{atalhos.map(([href, icon, title, body]) => <Link href={href} className="atalho-card" key={href}><span className="atalho-icone">{icon}</span><strong>{title}</strong><p>{body}</p><small>Abrir →</small></Link>)}</div></div></section>

    <section className="section"><div className="shell"><div className="section-head enxuto"><div><span className="eyebrow">Salvador</span><h2>Quatro números para se orientar</h2></div><p>Recorte financeiro municipal consolidado até {dateBR(data.asOf)}.</p></div><div className="grid grid-4"><Stat label="Receita realizada" value={brl(receita, { compact: true })} meta="arrecadação no período" tone="accent" /><Stat label="Despesa paga" value={brl(pago, { compact: true })} meta="desembolso registrado" /><Stat label="Aquisições publicadas" value={brl(aquisicoes, { compact: true })} meta={`${integer(data.acquisitions.summary?.records_received)} registros`} tone="blue" /><Stat label="Agentes catalogados" value={integer(data.agents?.total)} meta={`${integer(data.agents?.vereadores)} vereadores + Executivo verificado`} /></div></div></section>

    <section className="section compacto"><div className="shell"><div className="results-line"><span>Valor alto, repetição, déficit comercial, concentração ou contratação direta são indicadores para consulta, não conclusões de irregularidade.</span><Link href="/metodologia">Entender as regras →</Link></div></div></section>
  </>;
}
