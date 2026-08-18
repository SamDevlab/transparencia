import CompareAgencies from "../../components/CompareAgencies";

export const metadata = { title: "Comparar órgãos" };

export default function CompararPage() {
  return (
    <>
      <section className="page-hero"><div className="shell"><span className="eyebrow">Comparação</span><h1>Compare órgãos sem perder o contexto.</h1><p>Coloque duas secretarias lado a lado para comparar quantidade de aquisições, valor declarado, valor médio e proporção de contratação direta no mesmo recorte.</p></div></section>
      <section className="section compacto"><div className="shell"><CompareAgencies /></div></section>
    </>
  );
}
