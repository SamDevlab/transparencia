import UniversalSearch from "../../components/UniversalSearch";

export const metadata = { title: "Busca geral" };

export default function BuscarPage() {
  return (
    <>
      <section className="page-hero">
        <div className="shell">
          <span className="eyebrow">Busca geral</span>
          <h1>Encontre o dado sem precisar saber onde ele está.</h1>
          <p>Pesquise pessoas, fornecedores, CNPJ, processos, contratos, órgãos, credores e receitas em uma única consulta.</p>
        </div>
      </section>
      <section className="section compacto">
        <div className="shell"><UniversalSearch /></div>
      </section>
    </>
  );
}
