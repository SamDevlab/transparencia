import Link from "next/link";
import TradeExplorer from "../../../components/TradeExplorer";
import { loadWebData } from "../../../lib/web-data";

export const metadata = { title: "Comércio exterior de Salvador" };

function usd(value) {
  return new Intl.NumberFormat("pt-BR", { style: "currency", currency: "USD", notation: "compact", maximumFractionDigits: 1 }).format(Number(value ?? 0));
}

function pct(value) {
  if (value == null) return "—";
  return new Intl.NumberFormat("pt-BR", { style: "percent", maximumFractionDigits: 1 }).format(Number(value));
}

export default function SalvadorEconomiaPage() {
  const economy = loadWebData("economy.json");
  const data = economy.salvador;
  const s = data?.summary;

  return <>
    <section className="page-hero"><div className="shell"><span className="eyebrow">Salvador · comércio exterior</span><h1>O que empresas domiciliadas em Salvador importam e exportam.</h1><p>O módulo municipal do Comex Stat usa o domicílio fiscal da empresa declarante. Portanto, uma exportação atribuída a Salvador não prova que o produto foi fabricado na capital, e uma importação não prova consumo físico no município.</p><div className="hero-actions"><Link className="button" href="/economia/bahia">Comparar contexto da Bahia →</Link><Link className="button" href="/economia/oportunidades">Ver triagem produtiva</Link></div></div></section>

    <section className="section compacto"><div className="shell"><div className="notice warn"><span>!</span><div><strong>Leitura obrigatória:</strong> esta página descreve o comércio exterior de <strong>empresas domiciliadas em Salvador</strong>. O detalhamento municipal do Comex Stat é publicado em SH4.</div></div></div></section>

    {s ? <>
      <section className="section compacto"><div className="shell grid grid-4">
        <div className="card stat accent"><span className="stat-label">Exportações</span><div><span className="stat-value">{usd(s.exports_fob)}</span><div className="stat-meta">variação interanual {pct(s.exports_yoy)}</div></div></div>
        <div className="card stat"><span className="stat-label">Importações</span><div><span className="stat-value">{usd(s.imports_fob)}</span><div className="stat-meta">variação interanual {pct(s.imports_yoy)}</div></div></div>
        <div className="card stat"><span className="stat-label">Saldo comercial</span><div><span className={`stat-value ${Number(s.balance_fob) < 0 ? "saldo-negativo" : "saldo-positivo"}`}>{usd(s.balance_fob)}</span><div className="stat-meta">somente deste recorte municipal</div></div></div>
        <div className="card stat blue"><span className="stat-label">Corrente de comércio</span><div><span className="stat-value">{usd(s.trade_flow_fob)}</span><div className="stat-meta">exportações + importações</div></div></div>
      </div></section>
      <section className="section"><div className="shell"><div className="section-head enxuto"><div><span className="eyebrow">Explorar</span><h2>Produtos SH4 e países</h2></div><p>Use a busca para descobrir um código, produto ou parceiro sem sair desta página.</p></div><TradeExplorer scope="salvador" /></div></section>
    </> : <section className="section"><div className="shell"><div className="card empty">O snapshot municipal do Comex Stat ainda não está disponível. A ausência de dados não é mostrada como zero comércio.</div></div></section>}
  </>;
}
