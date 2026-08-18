import Link from "next/link";
import { brl, integer, loadWebData } from "../../lib/web-data";

export const metadata = { title: "Órgãos" };

export default function OrgaosPage() {
  const data = loadWebData("agencies.json");
  return (
    <>
      <section className="page-hero"><div className="shell"><span className="eyebrow">Órgãos</span><h1>Veja a atividade de compra por secretaria e órgão.</h1><p>Cada perfil reúne quantidade, valor declarado, formas de contratação e os maiores processos do recorte municipal.</p><div className="kicker-row"><span className="badge green">{integer(data.rows.length)} órgãos com aquisições</span><span className="badge">fonte municipal</span></div></div></section>
      <section className="section compacto"><div className="shell"><div className="orgaos-grid">{data.rows.map((row) => <Link href={`/orgaos/${row.id}`} className="orgao-card" key={row.id}><span className="badge">{row.sigla || "Órgão"}</span><h3>{row.nome}</h3><div className="orgao-metricas"><span><b>{integer(row.quantidade)}</b> aquisições</span><span><b>{brl(row.valorDeclarado, { compact: true })}</b> valor declarado</span></div><small>{Math.round(row.percentualContratacaoDireta * 100)}% dos registros são dispensa/inexigibilidade</small></Link>)}</div></div></section>
    </>
  );
}
