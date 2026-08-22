import Link from "next/link";
import { loadWebData } from "../../lib/web-data";

export const metadata = { title: "Cobertura e transparência dos dados" };

function tone(status) {
  if (["complete_for_filter", "complete_for_api_query", "collected", "complete_for_metadata_collection", "complete_for_defined_collection"].includes(status)) return "green";
  if (["partial", "partial_with_verified_sources", "source_mapped_not_normalized", "not_collected", "historical_baseline_normalized"].includes(status)) return "yellow";
  if (status === "unavailable") return "red";
  return "";
}

export default function TransparenciaPage() {
  const data = loadWebData("transparency.json");
  return <>
    <section className="page-hero"><div className="shell"><span className="eyebrow">Cobertura dos dados</span><h1>O que está disponível e até onde cada fonte permite afirmar.</h1><p>Falha de fonte, limitação metodológica e dado ainda não normalizado ficam explícitos. Ausência de resposta nunca é apresentada como zero.</p></div></section>

    <section className="section compacto"><div className="shell coverage-grid source-coverage-grid">
      {data.datasets.map((item) => <article className="coverage-card source-card" key={item.id}><header><strong>{item.title}</strong><span className={`badge ${tone(item.status)}`}>{item.statusLabel}</span></header><p>{item.detail}</p><div className="source-foot"><span>{item.source}</span><Link href={item.href}>Consultar →</Link></div></article>)}
    </div></section>

    <section className="section"><div className="shell grid grid-2"><div className="card panel"><div className="panel-title"><h3>Regras de integridade</h3><span>sempre aplicadas</span></div><div className="method-list"><div className="method-item"><strong>Falha não vira zero</strong><p>Se a fonte não responder, a cobertura é rebaixada.</p></div><div className="method-item"><strong>Agregado não vira gasto pessoal</strong><p>Total de órgão ou Câmara não é atribuído a uma pessoa sem documento nominal.</p></div><div className="method-item"><strong>Indicador não vira acusação</strong><p>Concentração, déficit, contratação direta e valor alto são pontos para análise.</p></div><div className="method-item"><strong>Vínculo não é aproximado</strong><p>Relações entre processo, contrato e pagamento exigem identificadores oficiais compatíveis.</p></div></div></div><div className="card panel"><div className="panel-title"><h3>Fontes centrais</h3><span>originais</span></div><div className="fontes-rapidas"><a href="https://transparencia.salvador.ba.gov.br/" target="_blank" rel="noreferrer"><strong>Prefeitura de Salvador ↗</strong><span>Finanças e aquisições.</span></a><a href="https://www.cms.ba.gov.br/" target="_blank" rel="noreferrer"><strong>Câmara Municipal ↗</strong><span>Legislativo e prestação de contas.</span></a><a href="https://dados.ba.gov.br/" target="_blank" rel="noreferrer"><strong>Dados Abertos da Bahia ↗</strong><span>Receitas, despesas, pagamentos, licitações e contratos estaduais.</span></a><a href="https://www.gov.br/mdic/pt-br/assuntos/comercio-exterior/estatisticas/base-de-dados-bruta" target="_blank" rel="noreferrer"><strong>MDIC / Comex Stat ↗</strong><span>Comércio exterior.</span></a></div></div></div></section>
  </>;
}
