import Link from "next/link";
import TradeExplorer from "../../../components/TradeExplorer";
import { loadWebData } from "../../../lib/web-data";

export const metadata = { title: "Comércio exterior da Bahia" };

function usd(value) {
  return new Intl.NumberFormat("pt-BR", { style: "currency", currency: "USD", notation: "compact", maximumFractionDigits: 1 }).format(Number(value ?? 0));
}

function pct(value) {
  if (value == null) return "—";
  return new Intl.NumberFormat("pt-BR", { style: "percent", maximumFractionDigits: 1 }).format(Number(value));
}

export default function BahiaEconomiaPage() {
  const economy = loadWebData("economy.json");
  const data = economy.bahia;
  const s = data?.summary;
  const deficits = data?.products?.filter((row) => Number(row.balance_fob) < 0).sort((a, b) => Number(a.balance_fob) - Number(b.balance_fob)).slice(0, 5) ?? [];

  return <>
    <section className="page-hero"><div className="shell"><span className="eyebrow">Bahia · comércio exterior</span><h1>Produtos, parceiros e saldo comercial da Bahia.</h1><p>Nos dados gerais do Comex Stat, a exportação por UF indica a UF produtora. Na importação, a UF é o domicílio fiscal da empresa importadora. A interface preserva essa diferença.</p><div className="hero-actions"><Link className="button" href="/economia/oportunidades">Ver triagem produtiva →</Link><Link className="button" href="/transparencia">Ver cobertura</Link></div></div></section>

    {s ? <>
      <section className="section compacto"><div className="shell grid grid-4">
        <div className="card stat accent"><span className="stat-label">Exportações</span><div><span className="stat-value">{usd(s.exports_fob)}</span><div className="stat-meta">variação interanual {pct(s.exports_yoy)}</div></div></div>
        <div className="card stat"><span className="stat-label">Importações</span><div><span className="stat-value">{usd(s.imports_fob)}</span><div className="stat-meta">variação interanual {pct(s.imports_yoy)}</div></div></div>
        <div className={`card stat ${Number(s.balance_fob) >= 0 ? "accent" : ""}`}><span className="stat-label">Saldo comercial</span><div><span className={`stat-value ${Number(s.balance_fob) < 0 ? "saldo-negativo" : "saldo-positivo"}`}>{usd(s.balance_fob)}</span><div className="stat-meta">exportações menos importações</div></div></div>
        <div className="card stat blue"><span className="stat-label">Corrente de comércio</span><div><span className="stat-value">{usd(s.trade_flow_fob)}</span><div className="stat-meta">exportações + importações</div></div></div>
      </div></section>

      <section className="section"><div className="shell"><div className="section-head enxuto"><div><span className="eyebrow">Explorar</span><h2>Produtos e países</h2></div><p>Pesquise pelo código SH4, descrição do produto ou país parceiro.</p></div><TradeExplorer scope="bahia" /></div></section>

      <section className="section"><div className="shell"><div className="section-head enxuto"><div><span className="eyebrow">Déficits</span><h2>Maiores saldos negativos do recorte</h2></div><p>Saldo negativo é descritivo e não significa que produzir localmente seja economicamente melhor.</p></div><div className="compact-list">{deficits.map((row) => <Link href={`/economia/bahia?busca=${encodeURIComponent(row.sh4 || row.product)}`} className="compact-row" key={row.sh4 || row.product}><div><strong>SH4 {row.sh4 || "—"} · {row.product}</strong><span>Importações {usd(row.imports_fob)} · Exportações {usd(row.exports_fob)}</span></div><strong className="saldo-negativo">{usd(row.balance_fob)}</strong></Link>)}</div></div></section>
    </> : <section className="section"><div className="shell"><div className="card empty">A coleta econômica ainda não publicou um snapshot válido da Bahia. A página de Transparência mostra o estado da fonte.</div></div></section>}
  </>;
}
