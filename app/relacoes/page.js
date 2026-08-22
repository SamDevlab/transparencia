import Link from "next/link";
import { brl, integer, loadWebData } from "../../lib/web-data";

export const metadata = { title: "Relações documentais" };

export default function RelacoesPage() {
  const data = loadWebData("municipal-links.json");
  const summary = data.summary ?? {};
  const top = (data.links ?? []).slice(0, 100);

  return (
    <>
      <section className="page-hero">
        <div className="shell">
          <span className="eyebrow">Relações documentais</span>
          <h1>Aquisições e contratos ligados pelo mesmo número oficial de processo.</h1>
          <p>Esta página publica apenas relações exatas encontradas entre as bases municipais. Não usa semelhança de nomes, objetos ou fornecedores e não transforma contrato em pagamento.</p>
          <div className="kicker-row">
            <span className="badge green">{integer(summary.processesWithExactContracts ?? 0)} processos vinculados</span>
            <span className="badge">{integer(summary.uniqueContractsLinked ?? 0)} contratos únicos vinculados</span>
            <span className="badge">{integer(summary.exactPairs ?? 0)} pares documentais</span>
          </div>
        </div>
      </section>

      <section className="section compacto">
        <div className="shell grid grid-2">
          <div className="notice"><span>✓</span><div><strong>Regra de identidade:</strong> {data.identityRule}</div></div>
          <div className="notice"><span>i</span><div><strong>Limite contábil:</strong> {data.accountingRule}</div></div>
        </div>
      </section>

      <section className="section">
        <div className="shell">
          <div className="section-head enxuto"><div><span className="eyebrow">Maiores aquisições com contrato exato</span><h2>Do processo para os contratos documentados</h2></div><p>Exibindo até 100 relações, ordenadas pelo valor declarado da aquisição.</p></div>
          <div className="card table-card"><div className="table-wrap"><table><thead><tr><th>Processo</th><th>Órgão</th><th>Objeto</th><th>Valor da aquisição</th><th>Contrato(s)</th></tr></thead><tbody>{top.map((item) => <tr key={item.processId}><td><Link href={`/processos/${encodeURIComponent(item.processId)}`}><strong className="mono">{item.processo || item.aquisicao || "—"}</strong></Link></td><td>{item.orgao || item.unidade || "—"}</td><td className="object-cell">{item.objeto || "—"}</td><td><strong className="mono">{item.valorAquisicao != null ? brl(item.valorAquisicao) : "—"}</strong></td><td>{item.contratos.map((contract) => <div key={contract.id}><Link href={`/contratos/${encodeURIComponent(contract.id)}`}><strong>{contract.numero || contract.numeroSigef || "Contrato"}</strong></Link>{contract.valorGlobal != null && <span className="muted"> · {brl(contract.valorGlobal)}</span>}</div>)}</td></tr>)}</tbody></table></div></div>
          <div className="results-line"><span>Aquisições até {summary.acquisitionsAsOf || "—"} · contratos até {summary.contractsAsOf || "—"}</span><Link href="/metodologia">Ver metodologia →</Link></div>
        </div>
      </section>

      <section className="section compacto"><div className="shell"><div className="notice"><span>i</span><div><strong>Privacidade:</strong> {data.privacyRule}</div></div></div></section>
    </>
  );
}
