import SupplierExplorer from "../../components/SupplierExplorer";
import { integer, loadWebData } from "../../lib/web-data";

export const metadata = { title: "Fornecedores" };

export default function FornecedoresPage() {
  const data = loadWebData("suppliers.json");
  const contracts = loadWebData("contracts.json");
  return (
    <>
      <section className="page-hero">
        <div className="shell">
          <span className="eyebrow">Fornecedores</span>
          <h1>Empresas vinculadas aos contratos encontrados no PNCP.</h1>
          <p>Consulte fornecedor, documento, contratos, unidades contratantes e valores publicados. Esta base é complementar e não é apresentada como a lista universal de fornecedores do Município.</p>
          <div className="kicker-row"><span className="badge green">{integer(data.rows.length)} fornecedores</span><span className="badge">{integer(contracts.rows.length)} contratos preservados</span></div>
        </div>
      </section>
      <section className="section compacto"><div className="shell"><div className="notice warn" style={{ marginBottom: 18 }}><span>!</span><div><strong>Leitura correta:</strong> volume ou repetição de contratos é um dado descritivo. A existência de concentração não é prova de favorecimento ou irregularidade.</div></div><SupplierExplorer /></div></section>
    </>
  );
}
