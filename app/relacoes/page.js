import Link from "next/link";
import { brl, integer, loadWebData } from "../../lib/web-data";

export const metadata = { title: "Relações documentais" };

function contractSource(contract) {
  return contract.sourceLayer === "pncp_complementary" || contract.sourceSystem === "PNCP"
    ? "PNCP"
    : "Transparência Salvador";
}

export default function RelacoesPage() {
  const data = loadWebData("municipal-links.json");
  const summary = data.summary ?? {};
  const top = (data.links ?? []).slice(0, 100);

  return (
    <>
      <section className="page-hero">
        <div className="shell">
          <span className="eyebrow">Relações documentais</span>
          <h1>Aquisições e registros contratuais ligados pelo mesmo número oficial de processo.</h1>
          <p>Esta página publica apenas relações exatas entre a base municipal de aquisições, a grade municipal de contratos e o PNCP complementar. Não usa semelhança de nomes, objetos ou fornecedores e não transforma contrato em pagamento.</p>
          <div className="kicker-row">
            <span className="badge green">{integer(summary.processesWithExactContracts ?? 0)} processos vinculados</span>
            <span className="badge">{integer(summary.uniqueContractsLinked ?? 0)} observações contratuais vinculadas</span>
            <span className="badge">{integer(summary.exactPairs ?? 0)} pares documentais</span>
            {Number(summary.pncpComplementaryExactPairs ?? 0) > 0 && <span className="badge green">{integer(summary.pncpComplementaryExactPairs)} pares PNCP</span>}
          </div>
        </div>
      </section>

      <section className="section compacto">
        <div className="shell grid grid-2">
          <div className="notice"><span>✓</span><div><strong>Regra de identidade:</strong> {data.identityRule}</div></div>
          <div className="notice"><span>i</span><div><strong>Limite contábil:</strong> {data.accountingRule}</div></div>
        </div>
      </section>

      {data.sourceObservationRule && <section className="section compacto"><div className="shell"><div className="notice"><span>i</span><div><strong>Fontes:</strong> {data.sourceObservationRule}</div></div></div></section>}

      <section className="section">
        <div className="shell">
          <div className="section-head enxuto"><div><span className="eyebrow">Maiores aquisições com relação exata</span><h2>Do processo para as observações contratuais documentadas</h2></div><p>Exibindo até 100 relações, ordenadas pelo valor declarado da aquisição.</p></div>
          <div className="card table-card"><div className="table-wrap"><table><thead><tr><th>Processo</th><th>Órgão</th><th>Objeto</th><th>Valor da aquisição</th><th>Contrato(s)</th></tr></thead><tbody>{top.map((item) => <tr key={item.processId}><td><Link href={`/processos/${encodeURIComponent(item.processId)}`}><strong className="mono">{item.processo || item.aquisicao || "—"}</strong></Link></td><td>{item.orgao || item.unidade || "—"}</td><td className="object-cell">{item.objeto || "—"}</td><td><strong className="mono">{item.valorAquisicao != null ? brl(item.valorAquisicao) : "—"}</strong></td><td>{item.contratos.map((contract) => <div key={`${contract.sourceLayer || contract.sourceSystem}:${contract.id}`}><Link href={`/contratos/${encodeURIComponent(contract.id)}`}><strong>{contract.numero || contract.numeroSigef || "Contrato"}</strong></Link><span className="muted"> · {contractSource(contract)}</span>{contract.valorGlobal != null && <span className="muted"> · {brl(contract.valorGlobal)}</span>}</div>)}</td></tr>)}</tbody></table></div></div>
          <div className="results-line"><span>Aquisições até {summary.acquisitionsAsOf || "—"} · contratos municipais até {summary.contractsAsOf || "—"} · PNCP até {summary.pncpComplementaryAsOf || "—"}</span><Link href="/metodologia">Ver metodologia →</Link></div>
        </div>
      </section>

      <section className="section compacto"><div className="shell"><div className="notice"><span>i</span><div><strong>Privacidade:</strong> {data.privacyRule}</div></div></div></section>
    </>
  );
}
