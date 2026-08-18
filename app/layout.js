import Link from "next/link";
import QuickSearch from "../components/QuickSearch";
import "./globals.css";
import "./ux.css";
import "./features.css";

export const metadata = {
  title: { default: "Transparência Salvador", template: "%s | Transparência Salvador" },
  description: "Dados públicos de Salvador/BA organizados com fonte, cobertura e metodologia auditável.",
  openGraph: {
    title: "Transparência Salvador",
    description: "Receita, despesa, licitações, contratos, fornecedores e agentes públicos com rastreabilidade de fonte.",
    type: "website",
    locale: "pt_BR",
  },
};

const nav = [
  ["/dinheiro", "Dinheiro"],
  ["/licitacoes", "Licitações"],
  ["/agentes", "Agentes"],
  ["/fornecedores", "Fornecedores"],
  ["/analises", "Análises"],
];

export default function RootLayout({ children }) {
  return (
    <html lang="pt-BR">
      <body>
        <header className="site-header">
          <div className="shell header-inner header-principal">
            <Link href="/" className="brand" aria-label="Transparência Salvador — início">
              <span className="brand-mark" aria-hidden="true">T</span>
              <span><strong>Transparência</strong><small>Salvador / BA</small></span>
            </Link>
            <QuickSearch />
            <nav className="nav" aria-label="Navegação principal">
              {nav.map(([href, label]) => <Link key={href} href={href}>{label}</Link>)}
            </nav>
            <a className="github-link" href="https://github.com/SamDevlab/transparencia/tree/city/salvador" target="_blank" rel="noreferrer">Repositório ↗</a>
          </div>
        </header>

        <main>{children}</main>

        <nav className="mobile-bottom" aria-label="Navegação móvel">
          <Link href="/"><span>⌂</span><small>Início</small></Link>
          <Link href="/buscar"><span>⌕</span><small>Buscar</small></Link>
          <Link href="/dinheiro"><span>R$</span><small>Dinheiro</small></Link>
          <Link href="/agentes"><span>◎</span><small>Agentes</small></Link>
          <Link href="/analises"><span>◇</span><small>Análises</small></Link>
        </nav>

        <footer className="site-footer">
          <div className="shell rodape-enxuto">
            <div><strong>Transparência Salvador</strong><p>Projeto independente de organização de dados públicos. Sem fonte, sem fato.</p></div>
            <div className="rodape-links">
              <Link href="/financas">Finanças</Link>
              <Link href="/contratos">Contratos</Link>
              <Link href="/orgaos">Órgãos</Link>
              <Link href="/comparar">Comparar órgãos</Link>
              <Link href="/metodologia">Metodologia</Link>
              <a href="https://transparencia.salvador.ba.gov.br/" target="_blank" rel="noreferrer">Fonte municipal ↗</a>
            </div>
          </div>
        </footer>
      </body>
    </html>
  );
}
