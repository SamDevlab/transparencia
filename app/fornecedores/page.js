import SupplierExplorer from "../../components/SupplierExplorer";
import { integer, loadWebData } from "../../lib/web-data";

export const metadata = { title: "Fornecedores" };

export default function FornecedoresPage() {
  const data = loadWebData("suppliers.json");
  const contracts = loadWebData("contracts.json");
  const structuredLinks = contracts.structuredSupplierLinks ?? 0;
  return (
    <>
      <section className="page-hero">
        <div className="shell">
          <span className="eyebrow">Fornecedores empresariais</span>
          <h1>Empresas com CNPJ estruturado e evidência contratual publicada.</h1>
          <p>O diretório não republica CPF nem credor em texto livre. Um fornecedor pode aparecer porque o próprio PNCP contém o CNPJ ou porque um contrato municipal foi reconciliado com registro PNCP por identificadores documentais exatos.</p>
          <div className="kicker-row"><span className="badge green">{integer(data.rows.length)} empresas com CNPJ</span><span className="badge">{integer(structuredLinks)} contrato(s) municipal(is) enriquecido(s)</span><span className="badge">{integer(contracts.rows.length)} contratos municipais no recorte</span></div>
        </div>
      </section>
      <section className="section compacto"><div className="shell"><div className="notice" style={{ marginBottom: 12 }}><span>✓</span><div><strong>Regra de identidade:</strong> fornecedor municipal só é publicado com CNPJ empresarial estruturado e evidência exata de processo/contrato ou relação documental 1:1 inequívoca entre Prefeitura e PNCP.</div></div><div className="notice warn" style={{ marginBottom: 18 }}><span>!</span><div><strong>Leitura correta:</strong> volume ou repetição de contratos é um dado descritivo. Concentração não é prova de favorecimento, sobrepreço ou irregularidade.</div></div><SupplierExplorer /></div></section>
    </>
  );
}
