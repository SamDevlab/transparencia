import Link from "next/link";

export const metadata = { title: "Metodologia" };

const rules = [
  ["Sem fonte, sem fato", "Todo dado apresentado precisa apontar para uma fonte pública identificável."],
  ["Fonte primária primeiro", "Demonstrativos, sistemas oficiais, leis e portais públicos têm precedência sobre resumos ou notícias."],
  ["Estágios contábeis separados", "Dotação, empenho, liquidação e pagamento não são sinônimos e permanecem separados na interface."],
  ["Agregado não vira gasto individual", "Um total da Câmara, de um órgão ou de um credor não é atribuído a uma pessoa sem documento nominal que faça esse vínculo."],
  ["Falha da fonte não vira zero", "Tempo de resposta esgotado, limite de requisições ou erro da fonte são registrados como cobertura parcial ou indisponível."],
  ["Vínculos exigem evidência", "Pessoas, processos, contratos e fornecedores só são ligados por identificadores exatos ou equivalência documentada."],
  ["Sinal não é acusação", "Valor alto, concentração, contratação direta ou déficit comercial podem orientar uma consulta, mas não provam irregularidade ou inviabilidade econômica."],
  ["Triagem não é recomendação", "O índice produtivo organiza setores para estudo. Ele não conclui que a Bahia deve produzir localmente um item importado."],
];

const statuses = [
  ["Completo para o filtro", "green", "A própria fonte fechou a contagem ou a paginação para aquele período e filtro."],
  ["Parcial", "yellow", "Os registros coletados são válidos, mas não é possível provar que representam a totalidade daquele recorte."],
  ["Indisponível", "red", "A fonte não respondeu de forma suficiente naquela tentativa e nenhuma ausência é tratada como zero."],
  ["Fonte mapeada", "yellow", "A fonte oficial foi identificada, mas a normalização necessária para publicar o indicador ainda não terminou."],
];

export default function MetodologiaPage() {
  return <>
    <section className="page-hero"><div className="shell"><span className="eyebrow">Metodologia</span><h1>O dado precisa ser útil sem parecer mais certo do que realmente é.</h1><p>Cada informação mantém sua fonte, período, cobertura e forma correta de leitura. As novas análises econômicas seguem a mesma regra da transparência pública.</p></div></section>

    <section className="section compacto"><div className="shell"><div className="section-head enxuto"><div><span className="eyebrow">Regras</span><h2>Princípios de integridade</h2></div></div><div className="method-list">{rules.map(([title, body]) => <div className="method-item" key={title}><strong>{title}</strong><p>{body}</p></div>)}</div></div></section>

    <section className="section"><div className="shell grid grid-2"><div className="card panel"><div className="panel-title"><h3>Bahia no Comex Stat</h3><span>dados gerais</span></div><p className="muted">Nas exportações por UF, a Bahia representa a UF produtora da mercadoria. Nas importações, representa o domicílio fiscal da empresa importadora.</p></div><div className="card panel"><div className="panel-title"><h3>Salvador no Comex Stat</h3><span>dados municipais</span></div><p className="muted">Exportações e importações são atribuídas ao domicílio fiscal da empresa. Por isso o site não chama esses números de “produção de Salvador” ou “consumo de Salvador”.</p></div></div></section>

    <section className="section"><div className="shell"><div className="notice warn"><span>!</span><div><strong>Outros estados:</strong> comércio internacional não mede dependência de São Paulo, Minas Gerais, Pernambuco etc. Essa camada será calculada separadamente a partir da Matriz de Insumo-Produto da Bahia/SEI e fontes inter-regionais adequadas.</div></div></div></section>

    <section className="section"><div className="shell"><div className="section-head enxuto"><div><span className="eyebrow">Cobertura</span><h2>Como interpretar cada situação</h2></div><Link href="/transparencia">Ver situação atual de cada fonte →</Link></div><div className="coverage-grid">{statuses.map(([name, tone, description]) => <div className="coverage-card" key={name}><header><strong>{name}</strong><span className={`badge ${tone}`}>{name}</span></header><p>{description}</p></div>)}</div></div></section>

    <section className="section"><div className="shell"><div className="card panel"><div className="panel-title"><h3>Fontes principais</h3><span>consulte o original</span></div><div className="fontes-rapidas"><a href="https://transparencia.salvador.ba.gov.br/" target="_blank" rel="noreferrer"><strong>Portal da Transparência de Salvador ↗</strong><span>Receita, despesa, contratos e aquisições municipais.</span></a><a href="https://www.cms.ba.gov.br/" target="_blank" rel="noreferrer"><strong>Câmara Municipal de Salvador ↗</strong><span>Vereadores, atividade legislativa e prestação de contas.</span></a><a href="https://www.gov.br/mdic/pt-br/assuntos/comercio-exterior/estatisticas/base-de-dados-bruta" target="_blank" rel="noreferrer"><strong>MDIC / Comex Stat ↗</strong><span>Comércio exterior da Bahia e das empresas domiciliadas em Salvador.</span></a><a href="https://www.ba.gov.br/sei/relatorio-da-matriz-de-insumo-produto" target="_blank" rel="noreferrer"><strong>SEI / Matriz de Insumo-Produto ↗</strong><span>Encadeamentos econômicos e futura camada interestadual.</span></a></div></div></div></section>
  </>;
}
