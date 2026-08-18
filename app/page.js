import Link from "next/link";
import { brl, integer, loadWebData, parseBrlText, dateBR } from "../lib/web-data";

export const metadata = { title: "Visão geral" };

function Stat({ label, value, meta, tone = "" }) {
  return <div className={`card stat ${tone}`}><span className="stat-label">{label}</span><div><span className="stat-value mono">{value}</span><div className="stat-meta">{meta}</div></div></div>;
}

const atalhos = [
  ["/buscar", "⌕", "Buscar qualquer coisa", "Pessoa, empresa, CNPJ, processo, contrato, órgão ou código."],
  ["/dinheiro", "R$", "Para onde foi o dinheiro?", "Comece pelos totais e navegue até processos, contratos e fornecedores quando houver vínculo exato."],
  ["/agentes", "◎", "Quem administra Salvador?", "Prefeito, vice, secretários verificados e vereadores, com fonte e contatos publicados."],
  ["/licitacoes", "▤", "Ver licitações e aquisições", "Pesquise os registros municipais por número, órgão, modalidade, objeto ou valor."],
  ["/analises", "◇", "O que merece análise?", "Valores elevados, repetição e concentração apresentados como sinais descritivos para abrir documentos."],
];

export default function HomePage() {
  const data = loadWebData("dashboard.json");
  const finance = data.finance;
  const receita = parseBrlText(finance.revenue_totalizer?.Realizado);
  const pago = parseBrlText(finance.expense_totalizer?.Pago);
  const aquisicoes = parseBrlText(data.acquisitions.summary?.api_reported_total_value_brl_text);

  return (
    <>
      <section className="hero hero-clean"><div className="shell"><span className="eyebrow">Transparência sem labirinto</span><h1>O que você quer descobrir sobre Salvador?</h1><p>Você não precisa saber em qual portal, tabela ou secretaria procurar. Comece por uma pergunta e o sistema leva até a referência e a fonte.</p><div className="hero-actions"><Link className="button primary" href="/buscar">Começar uma busca →</Link><Link className="button" href="/dinheiro">Seguir o dinheiro</Link></div></div></section>

      <section className="section compacto"><div className="shell"><div className="notice"><span>●</span><div><strong>Publicação auditada até {dateBR(data.asOf)}.</strong> O frontend escolhe automaticamente o snapshot mais recente que também possui estado final validado no repositório.</div></div></div></section>

      <section className="section"><div className="shell"><div className="atalhos-grid">{atalhos.map(([href, icon, title, body]) => <Link href={href} className="atalho-card" key={href}><span className="atalho-icone">{icon}</span><strong>{title}</strong><p>{body}</p><small>Abrir →</small></Link>)}</div></div></section>

      <section className="section"><div className="shell"><div className="section-head enxuto"><div><span className="eyebrow">Panorama</span><h2>Quatro números para se orientar</h2></div><p>Recorte financeiro de 01/01/2026 a 17/08/2026.</p></div><div className="grid grid-4"><Stat label="Receita realizada" value={brl(receita, { compact: true })} meta="arrecadação no período" tone="accent" /><Stat label="Despesa paga" value={brl(pago, { compact: true })} meta="desembolso registrado" /><Stat label="Aquisições publicadas" value={brl(aquisicoes, { compact: true })} meta={`${integer(data.acquisitions.summary?.records_received)} registros`} tone="blue" /><Stat label="Agentes catalogados" value={integer(data.agents?.total)} meta={`${integer(data.agents?.vereadores)} vereadores + Executivo verificado`} /></div></div></section>

      <section className="section"><div className="shell"><div className="section-head enxuto"><div><span className="eyebrow">Relações</span><h2>O que já pode ser cruzado</h2></div></div><div className="grid grid-3"><Link className="coverage-card clicavel" href="/fornecedores"><header><strong>Fornecedores</strong><span className="badge green">{integer(data.suppliers?.total)}</span></header><p>Perfis construídos a partir dos contratos PNCP preservados, com documento, valor, unidades e linha do tempo.</p></Link><Link className="coverage-card clicavel" href="/analises"><header><strong>Processos em duas fontes</strong><span className="badge">{integer(data.suppliers?.exactLinks)}</span></header><p>Relações Prefeitura ↔ PNCP feitas somente quando o número de processo coincide exatamente após normalização mínima.</p></Link><Link className="coverage-card clicavel" href="/comparar"><header><strong>Comparar órgãos</strong><span className="badge">lado a lado</span></header><p>Compare volume de aquisições, valor declarado, valor médio e proporção de contratação direta.</p></Link></div></div></section>

      <section className="section compacto"><div className="shell"><div className="results-line"><span>Valor alto, repetição, dispensa ou concentração não são classificados automaticamente como irregularidade.</span><Link href="/metodologia">Entender as regras →</Link></div></div></section>
    </>
  );
}
