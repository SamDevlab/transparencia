import Link from "next/link";
import { loadWebData } from "../../lib/web-data";

export const metadata = { title: "Cobertura e transparência dos dados" };

function tone(status) {
  if (["complete_for_filter", "complete_for_api_query", "collected"].includes(status)) return "green";
  if (["partial", "source_mapped_not_normalized", "not_collected"].includes(status)) return "yellow";
  if (status === "unavailable") return "red";
  return "";
}

const stateSources = [
  ["Portal Transparência Bahia", "Receitas, despesas, pagamentos, licitações, contratos, pessoal, emendas e gestão fiscal.", "https://www.transparencia.ba.gov.br/"],
  ["TCE/BA — Execução da despesa", "CSV anual com acesso automatizado e detalhamento por unidade e credor.", "https://www.tce.ba.gov.br/dados-abertos/despesas"],
  ["TCE/BA — Contratos", "Dados abertos de contratos, contratado, objeto, valor, vigência e quantidade de aditivos.", "https://www.tce.ba.gov.br/dados-abertos/contratos"],
  ["TCE/BA — Licitações", "Procedimentos licitatórios em formato processável por máquina.", "https://www.tce.ba.gov.br/dados-abertos/procedimentos-licitatorios"],
  ["TCE/BA — Repasses e transferências", "Instrumentos, recebedores, CNPJ, valor atualizado e objeto.", "https://www.tce.ba.gov.br/dados-abertos/repasses-e-transferencias"],
];

export default function TransparenciaPage() {
  const data = loadWebData("transparency.json");
  return <>
    <section className="page-hero"><div className="shell"><span className="eyebrow">Transparência da própria plataforma</span><h1>Veja o que está completo, parcial ou ainda não quantificado.</h1><p>Além de mostrar números públicos, o projeto publica a cobertura de cada fonte. Falha de API, limitação metodológica ou dado ainda não normalizado ficam visíveis em vez de parecerem zero.</p></div></section>

    <section className="section compacto"><div className="shell coverage-grid source-coverage-grid">
      {data.datasets.map((item) => <article className="coverage-card source-card" key={item.id}><header><strong>{item.title}</strong><span className={`badge ${tone(item.status)}`}>{item.statusLabel}</span></header><p>{item.detail}</p><div className="source-foot"><span>{item.source}</span><Link href={item.href}>Consultar →</Link></div></article>)}
    </div></section>

    <section className="section"><div className="shell"><div className="section-head enxuto"><div><span className="eyebrow">Próxima cobertura pública</span><h2>Bahia estadual já está mapeada</h2></div><p>Essas fontes oficiais já têm rota e semântica registradas no repositório. Elas só receberão números próprios quando a coleta e a validação de cada conjunto forem concluídas.</p></div><div className="coverage-grid">{stateSources.map(([title, body, href]) => <a className="coverage-card source-card clicavel" href={href} target="_blank" rel="noreferrer" key={title}><header><strong>{title}</strong><span className="badge yellow">fonte mapeada</span></header><p>{body}</p><div className="source-foot"><span>Estado da Bahia</span><span>Abrir fonte ↗</span></div></a>)}</div></div></section>

    <section className="section"><div className="shell grid grid-2"><div className="card panel"><div className="panel-title"><h3>O que nunca fazemos</h3><span>integridade</span></div><div className="method-list"><div className="method-item"><strong>Falha não vira zero</strong><p>Se a fonte não responder, a cobertura é rebaixada.</p></div><div className="method-item"><strong>Agregado não vira gasto pessoal</strong><p>Um total de órgão ou Câmara não é distribuído entre agentes sem documento nominal.</p></div><div className="method-item"><strong>Indicador não vira acusação</strong><p>Concentração, déficit, contratação direta e valor alto são sinais descritivos.</p></div></div></div><div className="card panel"><div className="panel-title"><h3>Fontes centrais</h3><span>originais</span></div><div className="fontes-rapidas"><a href="https://transparencia.salvador.ba.gov.br/" target="_blank" rel="noreferrer"><strong>Prefeitura de Salvador ↗</strong><span>Finanças e aquisições.</span></a><a href="https://www.cms.ba.gov.br/" target="_blank" rel="noreferrer"><strong>Câmara Municipal ↗</strong><span>Legislativo e prestação de contas.</span></a><a href="https://www.gov.br/mdic/pt-br/assuntos/comercio-exterior/estatisticas/base-de-dados-bruta" target="_blank" rel="noreferrer"><strong>MDIC / Comex Stat ↗</strong><span>Comércio exterior.</span></a><a href="https://www.ba.gov.br/sei/relatorio-da-matriz-de-insumo-produto" target="_blank" rel="noreferrer"><strong>SEI / Matriz de Insumo-Produto ↗</strong><span>Encadeamentos econômicos da Bahia.</span></a></div></div></div></section>
  </>;
}
