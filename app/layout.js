import Link from "next/link";
import QuickSearch from "../components/QuickSearch";
import "./globals.css";
import "./ux.css";
import "./features.css";
import "./economy.css";

export const metadata = {
  title: { default: "Transparência Salvador", template: "%s | Transparência Salvador" },
  description: "Transparência pública e inteligência econômica de Salvador e Bahia com fontes auditáveis.",
  openGraph: {
    title: "Transparência Salvador",
    description: "Gastos públicos, licitações, agentes, fornecedores e economia da Bahia e Salvador com rastreabilidade de fonte.",
    type: "website",
    locale: "pt_BR",
  },
};

const nav = [
  ["/dinheiro", "Dinheiro"],
  ["/licitacoes", "Licitações"],
  ["/economia", "Economia"],
  ["/agentes", "Agentes"],
  ["/bahia", "Bahia"],
];

export default function RootLayout({ children }) {
  return (
    <html lang="pt-BR">
      <body>
        <header className="site-header">
          <div className="shell header-inner header-principal">
            <Link href="/" className="brand" aria-label="Transparência Salvador — início">
              <span className="brand-mark" aria-hidden="true">T</span>
              <span><strong>Transparência</strong><small>Salvador / Bahia</small></span>
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
          <Link href="/economia"><span>↗</span><small>Economia</small></Link>
          <Link href="/bahia"><span>BA</span><small>Bahia</small></Link>
        </nav>

        <footer className="site-footer">
          <div className="shell rodape-enxuto">
            <div><strong>Transparência Salvador</strong><p>Projeto independente de organização de dados públicos e inteligência econômica. Sem fonte, sem fato.</p></div>
            <div className="rodape-links">
              <Link href="/financas">Finanças</Link>
              <Link href="/contratos">Contratos</Link>
              <Link href="/fornecedores">Fornecedores</Link>
              <Link href="/orgaos">Órgãos</Link>
              <Link href="/analises">Análises</Link>
              <Link href="/bahia/transparencia">Transparência Bahia</Link>
              <Link href="/transparencia">Cobertura dos dados</Link>
              <Link href="/metodologia">Metodologia</Link>
            </div>
          </div>
        </footer>
      </body>
    </html>
  );
}
