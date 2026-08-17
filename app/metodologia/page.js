import { loadWebData } from "../../lib/web-data";

export const metadata = { title: "Metodologia" };

const rules = [
  ["Sem fonte, sem fato", "Todo dado apresentado precisa apontar para uma fonte pública identificável. Ausência de fonte impede a promoção de uma afirmação a fato no projeto."],
  ["Fonte primária primeiro", "Demonstrativos, APIs oficiais, leis e portais públicos têm precedência. Notícias oficiais ajudam no contexto, mas não substituem documentos contábeis quando eles existem."],
  ["Estágios contábeis separados", "Dotação, empenho, liquidação e pagamento não são sinônimos. A interface preserva o estágio publicado e não converte compromisso orçamentário em desembolso."],
  ["Agregado não vira gasto individual", "Total por credor, Câmara ou unidade não é atribuído a uma pessoa sem documento nominal que estabeleça esse vínculo."],
  ["Falha de fonte não vira zero", "Timeout, rate limit ou erro de API é registrado como parcial/indisponível. O sistema não interpreta silêncio técnico como inexistência de registros."],
  ["Reconciliação exata", "Vínculos entre bases usam identificadores normalizados exatos. Similaridade textual e fuzzy match podem auxiliar pesquisa, mas não são promovidos automaticamente a fato."],
  ["Sinal não é acusação", "Valor alto, concentração, dispensa ou inexigibilidade são características descritivas que podem orientar investigação; não provam irregularidade ou crime."],
  ["Correção acima de aparência", "Se uma coleta antes marcada como completa for descoberta como subcapturada, a reivindicação é retirada e o snapshot é explicitamente invalidado."],
];

const statuses = [
  ["complete_for_filter", "green", "A própria fonte fechou contagem/paginação para aquele filtro e período. Não significa completude universal da cidade."],
  ["partial", "yellow", "Os registros coletados são válidos, mas a fonte ou o parser não permitem provar cobertura total daquele filtro."],
  ["unavailable", "red", "A tentativa falhou e nenhum dado daquele run é usado para alegar completude."],
  ["not_run", "", "A etapa foi desabilitada explicitamente naquele run."],
];

export default function MetodologiaPage() {
  const dashboard = loadWebData("dashboard.json");
  const status = dashboard.finalStatus;

  return (
    <>
      <section className="page-hero">
        <div className="shell">
          <span className="eyebrow">Metodologia</span>
          <h1>Transparência também exige dizer o que não sabemos.</h1>
          <p>O objetivo é tornar dados públicos pesquisáveis sem aumentar artificialmente a certeza. Cada fonte tem um escopo de cobertura e cada transformação precisa preservar o sentido contábil e documental do dado.</p>
        </div>
      </section>

      <section className="section"><div className="shell"><div className="section-head"><div><span className="eyebrow">Regras</span><h2>Princípios de integridade</h2></div></div><div className="method-list">{rules.map(([title, body]) => <div className="method-item" key={title}><strong>{title}</strong><p>{body}</p></div>)}</div></div></section>

      <section className="section"><div className="shell"><div className="section-head"><div><span className="eyebrow">Cobertura</span><h2>Como interpretar os status</h2></div></div><div className="coverage-grid">{statuses.map(([name, tone, description]) => <div className="coverage-card" key={name}><header><strong>{name}</strong><span className={`badge ${tone}`}>{name}</span></header><p>{description}</p></div>)}</div></div></section>

      <section className="section"><div className="shell grid grid-2"><div className="card panel"><div className="panel-title"><h3>Validação do projeto</h3><span>{status.as_of}</span></div><div className="method-list"><div className="method-item"><strong>Testes Python</strong><p>{status.validation?.pytest || "ver validação versionada"}</p></div><div className="method-item"><strong>Parser ao vivo da CMS</strong><p>{status.validation?.cms_live_first_page?.visible_commitment_identifiers} identificadores visíveis, {status.validation?.cms_live_first_page?.parsed_commitment_identifiers} normalizados, {status.validation?.cms_live_first_page?.missing} faltantes.</p></div><div className="method-item"><strong>Status técnico</strong><p>{status.project_status}</p></div></div></div><div className="card panel"><div className="panel-title"><h3>Fontes centrais</h3><span>abrir original</span></div><div className="method-list"><a className="method-item" href="https://transparencia.salvador.ba.gov.br/" target="_blank" rel="noreferrer"><strong>Portal da Transparência de Salvador ↗</strong><p>Receita, despesa, contratos e aquisições municipais.</p></a><a className="method-item" href="https://www.cms.ba.gov.br/" target="_blank" rel="noreferrer"><strong>Câmara Municipal de Salvador ↗</strong><p>Composição, produção legislativa e transparência institucional.</p></a><a className="method-item" href="https://pncp.gov.br/" target="_blank" rel="noreferrer"><strong>PNCP ↗</strong><p>Fonte federal complementar para contratações e contratos.</p></a><a className="method-item" href="https://github.com/SamDevlab/transparencia/tree/city/salvador" target="_blank" rel="noreferrer"><strong>Repositório e evidências ↗</strong><p>Coletores, hashes, snapshots, testes e documentação.</p></a></div></div></div></section>
    </>
  );
}
