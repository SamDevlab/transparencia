export const metadata = { title: "Metodologia" };

const rules = [
  ["Sem fonte, sem fato", "Todo dado apresentado precisa apontar para uma fonte pública identificável."],
  ["Fonte primária primeiro", "Demonstrativos, sistemas oficiais, leis e portais públicos têm precedência sobre resumos ou notícias."],
  ["Estágios contábeis separados", "Dotação, empenho, liquidação e pagamento não são sinônimos e permanecem separados na interface."],
  ["Agregado não vira gasto individual", "Um total da Câmara, de um órgão ou de um credor não é atribuído a uma pessoa sem documento nominal que faça esse vínculo."],
  ["Falha da fonte não vira zero", "Tempo de resposta esgotado, limite de requisições ou erro da fonte são registrados como cobertura parcial ou indisponível."],
  ["Vínculos exigem evidência", "Pessoas e registros só são ligados por identificadores exatos ou por equivalência documentada em fonte oficial."],
  ["Sinal não é acusação", "Valor alto, concentração, dispensa ou inexigibilidade podem orientar uma consulta, mas não provam irregularidade."],
  ["Correções ficam explícitas", "Se uma coleta antes considerada completa apresentar falha, a condição é corrigida e a evidência anterior permanece identificada como superada."],
];

const statuses = [
  ["Completo para o filtro", "green", "A própria fonte fechou a contagem ou a paginação para aquele período e filtro."],
  ["Parcial", "yellow", "Os registros coletados são válidos, mas não é possível provar que representam a totalidade daquele recorte."],
  ["Indisponível", "red", "A fonte não respondeu de forma suficiente naquela tentativa e nenhuma ausência é tratada como zero."],
  ["Não executado", "", "Aquela etapa não foi consultada na atualização em questão."],
];

export default function MetodologiaPage() {
  return (
    <>
      <section className="page-hero">
        <div className="shell">
          <span className="eyebrow">Metodologia</span>
          <h1>O dado precisa ser útil sem parecer mais certo do que realmente é.</h1>
          <p>Cada informação mantém sua fonte, seu período e sua forma correta de leitura. Quando uma fonte não permite comprovar a cobertura total, isso aparece de maneira explícita.</p>
        </div>
      </section>

      <section className="section compacto"><div className="shell"><div className="section-head enxuto"><div><span className="eyebrow">Regras</span><h2>Princípios de integridade</h2></div></div><div className="method-list">{rules.map(([title, body]) => <div className="method-item" key={title}><strong>{title}</strong><p>{body}</p></div>)}</div></div></section>

      <section className="section"><div className="shell"><div className="section-head enxuto"><div><span className="eyebrow">Cobertura</span><h2>Como interpretar cada situação</h2></div></div><div className="coverage-grid">{statuses.map(([name, tone, description]) => <div className="coverage-card" key={name}><header><strong>{name}</strong><span className={`badge ${tone}`}>{name}</span></header><p>{description}</p></div>)}</div></div></section>

      <section className="section"><div className="shell"><div className="card panel"><div className="panel-title"><h3>Fontes principais</h3><span>consulte o original</span></div><div className="fontes-rapidas"><a href="https://transparencia.salvador.ba.gov.br/" target="_blank" rel="noreferrer"><strong>Portal da Transparência de Salvador ↗</strong><span>Receita, despesa, contratos e aquisições municipais.</span></a><a href="https://www.cms.ba.gov.br/" target="_blank" rel="noreferrer"><strong>Câmara Municipal de Salvador ↗</strong><span>Vereadores, atividade legislativa e prestação de contas.</span></a><a href="https://pncp.gov.br/" target="_blank" rel="noreferrer"><strong>Portal Nacional de Contratações Públicas ↗</strong><span>Fonte complementar para contratações e contratos.</span></a><a href="https://github.com/SamDevlab/transparencia/tree/city/salvador" target="_blank" rel="noreferrer"><strong>Dados, evidências e código ↗</strong><span>Arquivos de origem, verificações e documentação do projeto.</span></a></div></div></div></section>
    </>
  );
}
