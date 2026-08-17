import Link from "next/link";
import QuickSearch from "../components/QuickSearch";
import "./globals.css";
import "./ux.css";

export const metadata = {
  title: {
    default: "Transparência Salvador",
    template: "%s | Transparência Salvador",
  },
  description:
    "Dados públicos de Salvador/BA organizados com fonte, cobertura e metodologia auditável.",
  openGraph: {
    title: "Transparência Salvador",
    description: "Receita, despesa, licitações, contratos e agentes públicos com rastreabilidade de fonte.",
    type: "website",
    locale: "pt_BR",
  },
};

const nav = [
  ["/", "Visão geral"],
  ["/financas", "Finanças"],
  ["/licitacoes", "Licitações"],
  ["/contratos", "Contratos"],
  ["/agentes", "Agentes públicos"],
  ["/metodologia", "Metodologia"],
];

export default function RootLayout({ children }) {
  return (
    <html lang="pt-BR">
      <body>
        <header className="site-header">
          <div className="shell header-inner header-principal">
            <Link href="/" className="brand" aria-label="Transparência Salvador — início">
              <span className="brand-mark" aria-hidden="true">T</span>
              <span>
                <strong>Transparência</strong>
                <small>Salvador / BA</small>
              </span>
            </Link>

            <QuickSearch />

            <nav className="nav" aria-label="Navegação principal">
              {nav.map(([href, label]) => (
                <Link key={href} href={href}>{label}</Link>
              ))}
            </nav>

            <a
              className="github-link"
              href="https://github.com/SamDevlab/transparencia/tree/city/salvador"
              target="_blank"
              rel="noreferrer"
            >
              Repositório ↗
            </a>
          </div>
        </header>

        <main>{children}</main>

        <footer className="site-footer">
          <div className="shell rodape-enxuto">
            <div>
              <strong>Transparência Salvador</strong>
              <p>Projeto independente de organização de dados públicos. Sem fonte, sem fato.</p>
            </div>
            <div className="rodape-links">
              <a href="https://transparencia.salvador.ba.gov.br/" target="_blank" rel="noreferrer">Portal da Prefeitura ↗</a>
              <a href="https://www.cms.ba.gov.br/" target="_blank" rel="noreferrer">Câmara Municipal ↗</a>
              <a href="https://pncp.gov.br/" target="_blank" rel="noreferrer">Portal Nacional de Contratações ↗</a>
              <Link href="/metodologia">Como os dados são tratados</Link>
            </div>
          </div>
        </footer>
      </body>
    </html>
  );
}
