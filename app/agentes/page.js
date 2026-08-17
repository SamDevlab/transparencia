import Link from "next/link";
import AgentsExplorer from "../../components/AgentsExplorer";
import { integer, loadWebData } from "../../lib/web-data";

export const metadata = { title: "Agentes públicos" };

export default function AgentesPage() {
  const data = loadWebData("agents.json");

  return (
    <>
      <section className="page-hero">
        <div className="shell">
          <span className="eyebrow">Agentes públicos</span>
          <h1>Quem ocupa os principais cargos públicos de Salvador.</h1>
          <p>
            Prefeito, vice-prefeita, secretários com confirmação recente em fonte oficial e vereadores reunidos em uma única consulta. Contatos e funções adicionais só aparecem quando a própria fonte os publica.
          </p>
          <div className="hero-actions">
            <Link className="button" href="/camara">Ver atividade e contas da Câmara</Link>
          </div>
          <div className="kicker-row">
            <span className="badge green">fontes oficiais</span>
            <span className="badge">atualizado em 17/08/2026</span>
          </div>
        </div>
      </section>

      <section className="section compacto">
        <div className="shell">
          <div className="grid grid-3">
            <div className="card stat accent">
              <span className="stat-label">Executivo verificado</span>
              <div><span className="stat-value">{integer(data.summary.executive)}</span><div className="stat-meta">prefeito, vice e secretários com confirmação recente</div></div>
            </div>
            <div className="card stat">
              <span className="stat-label">Vereadores cadastrados</span>
              <div><span className="stat-value">{integer(data.summary.councilors)}</span><div className="stat-meta">20ª Legislatura · 2025–2028</div></div>
            </div>
            <div className="card stat blue">
              <span className="stat-label">Funções com contato direto</span>
              <div><span className="stat-value">{integer(data.summary.leadershipContacts)}</span><div className="stat-meta">Mesa Diretora e funções correlatas publicadas pela Câmara</div></div>
            </div>
          </div>
          <div className="results-line"><span>A relação do Executivo é deliberadamente limitada aos cargos que já possuem confirmação recente preservada no projeto; ausência nesta lista não significa ausência do cargo.</span></div>
        </div>
      </section>

      <section className="section">
        <div className="shell">
          <div className="section-head enxuto">
            <div><span className="eyebrow">Consulta</span><h2>Pesquisar agentes</h2></div>
            <p>Use nome, cargo, órgão, partido ou função. Telefone e e-mail podem ser copiados sem sair da página.</p>
          </div>
          <AgentsExplorer />
        </div>
      </section>
    </>
  );
}
