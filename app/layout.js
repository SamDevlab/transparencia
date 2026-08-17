import Link from "next/link";
import "./globals.css";

export const metadata = {
  title: {
    default: "Transparência Salvador",
    template: "%s | Transparência Salvador",
  },
  description:
    "Dados públicos de Salvador/BA organizados com fonte, cobertura e metodologia auditável.",
  openGraph: {
    title: "Transparência Salvador",
    description: "Receita, despesa, licitações, contratos e Câmara com rastreabilidade de fonte.",
    type: "website",
    locale: "pt_BR",
  },
};

const nav = [
  ["/", "Visão geral"],
  ["/licitacoes", "Licitações"],
  ["/financas", "Finanças"],
  ["/contratos", "Contratos"],
  ["/camara", "Câmara"],
  ["/metodologia", "Metodologia"],
];

export default function RootLayout({ children }) {
  return (
    <html lang="pt-BR">
      <body>
        <header className="site-header">
          <div className="shell header-inner">
            <Link href="/" className="brand" aria-label="Transparência Salvador — início">
              <span className="brand-mark" aria-hidden="true">T</span>
              <span>
                <strong>Transparência</strong>
                <small>Salvador / BA</small>
              </span>
            </Link>
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
              GitHub ↗
            </a>
          </div>
        </header>
        <main>{children}</main>
        <footer className="site-footer">
          <div className="shell footer-grid">
            <div>
              <div className="brand footer-brand">
                <span className="brand-mark" aria-hidden="true">T</span>
                <span><strong>Transparência</strong><small>dados públicos rastreáveis</small></span>
              </div>
              <p>Projeto independente de organização de dados públicos. Não é um detector de corrupção e não substitui as fontes oficiais.</p>
            </div>
            <div>
              <strong>Princípio central</strong>
              <p>Sem fonte, sem fato. Falha de fonte não vira zero; agregado não vira gasto individual.</p>
            </div>
            <div>
              <strong>Fontes</strong>
              <p>
                <a href="https://transparencia.salvador.ba.gov.br/" target="_blank" rel="noreferrer">Prefeitura ↗</a><br />
                <a href="https://www.cms.ba.gov.br/" target="_blank" rel="noreferrer">Câmara ↗</a><br />
                <a href="https://pncp.gov.br/" target="_blank" rel="noreferrer">PNCP ↗</a>
              </p>
            </div>
          </div>
        </footer>
      </body>
    </html>
  );
}
