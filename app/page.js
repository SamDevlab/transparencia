import Link from "next/link";
import { brl, integer, loadWebData, parseBrlText, dateBR } from "../lib/web-data";

export const metadata = { title: "Visão geral" };

function Stat({ label, value, meta, tone = "" }) {
  return <div className={`card stat ${tone}`}><span className="stat-label">{label}</span><div><span className="stat-value mono">{value}</span><div className="stat-meta">{meta}</div></div></div>;
}

const atalhos = [
  ["/buscar", "⌕", "Buscar qualquer coisa", "Pessoa, empresa, CNPJ, processo, contrato, órgão, produto ou código."],
  ["/dinheiro", "R$", "Para onde foi o dinheiro?", "Comece pelos totais e navegue até processos, contratos e fornecedores quando houver vínculo exato."],
  ["/economia/oportunidades", "↗", "Onde a Bahia depende de fora?", "Veja importações, déficit, concentração por país e cadeias que merecem estudo produtivo."],
  ["/economia/salvador", "SSA", "O que Salvador compra e vende ao mundo?", "Comércio exterior das empresas domiciliadas na capital, por SH4 e país."],
  ["/agentes", "◎", "Quem administra Salvador?", "Prefeito, vice, secretários verificados e vereadores, com fonte e contatos publicados."],
  ["/licitacoes", "▤", "Ver licitações e aquisições", "Pesquise os registros municipais por número, órgão, modalidade, objeto ou valor."],
];

export default function HomePage() {
  const data = loadWebData("dashboard.json");
  const finance = data.finance;
  const receita = parseBrlText(finance.revenue_totalizer?.Realizado);
  const pago = parseBrlText(finance.expense_totalizer?.Pago);
  const aquisicoes = parseBrlText(data.acquisitions.summary?.api_reported_total_value_brl_text);

  return (
    <>
      <section className="hero hero-clean"><div className="shell"><span className="eyebrow">Transparência e economia sem labirinto</span><h1>O que você quer descobrir sobre Salvador e a Bahia?</h1><p>Você não precisa saber em qual portal, tabela ou secretaria procurar. Comece por uma pergunta e o sistema leva até a referência, a metodologia e a fonte oficial.</p><div className="hero-actions"><Link className="button primary" href="/buscar">Começar uma busca →</Link><Link className="button" href="/dinheiro">Seguir o dinheiro</Link><Link className="button" href="/economia">Explorar economia</Link></div></div></section>

      <section className="section compacto"><div className="shell"><div className="notice"><span>●</span><div><strong>Dados com cobertura explícita.</strong> Transparência municipal usa o snapshot auditado mais recente; comércio exterior usa a atualização oficial disponível do Comex Stat. Consulte <Link href="/transparencia">Cobertura dos dados</Link>.</div></div></div></section>

      <section className="section"><div className="shell"><div className="atalhos-grid">{atalhos.map(([href, icon, title, body]) => <Link href={href} className="atalho-card" key={href}><span className="atalho-icone">{icon}</span><strong>{title}</strong><p>{body}</p><small>Abrir →</small></Link>)}</div></div></section>

      <section className="section"><div className="shell"><div className="section-head enxuto"><div><span className="eyebrow">Salvador</span><h2>Quatro números para se orientar</h2></div><p>Recorte financeiro municipal consolidado até {dateBR(data.asOf)}.</p></div><div className="grid grid-4"><Stat label="Receita realizada" value={brl(receita, { compact: true })} meta="arrecadação no período" tone="accent" /><Stat label="Despesa paga" value={brl(pago, { compact: true })} meta="desembolso registrado" /><Stat label="Aquisições publicadas" value={brl(aquisicoes, { compact: true })} meta={`${integer(data.acquisitions.summary?.records_received)} registros`} tone="blue" /><Stat label="Agentes catalogados" value={integer(data.agents?.total)} meta={`${integer(data.agents?.vereadores)} vereadores + Executivo verificado`} /></div></div></section>

      <section className="section"><div className="shell"><div className="section-head enxuto"><div><span className="eyebrow">Relações públicas</span><h2>O que já pode ser cruzado com segurança</h2></div></div><div className="grid grid-3"><Link className="coverage-card clicavel" href="/fornecedores"><header><strong>Fornecedores</strong><span className="badge green">{integer(data.suppliers?.total)}</span></header><p>Perfis construídos a partir dos contratos PNCP preservados, com documento, valor, unidades e linha do tempo.</p></Link><Link className="coverage-card clicavel" href="/analises"><header><strong>Processos em duas fontes</strong><span className="badge">{integer(data.suppliers?.exactLinks)}</span></header><p>Relações Prefeitura ↔ PNCP feitas somente quando o número de processo coincide exatamente após normalização mínima.</p></Link><Link className="coverage-card clicavel" href="/transparencia"><header><strong>Cobertura das fontes</strong><span className="badge">abrir</span></header><p>Veja o que está completo, parcial, indisponível ou ainda aguardando normalização — inclusive a nova camada econômica.</p></Link></div></div></section>

      <section className="section compacto"><div className="shell"><div className="results-line"><span>Valor alto, repetição, déficit comercial, concentração ou contratação direta são indicadores descritivos, não conclusões automáticas.</span><Link href="/metodologia">Entender as regras →</Link></div></div></section>
    </>
  );
}
