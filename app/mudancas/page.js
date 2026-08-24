import Link from "next/link";
import { integer, loadWebData } from "../../lib/web-data";

export const metadata = { title: "Mudanças nos contratos" };

function valueText(value, type) {
  if (value == null || value === "") return "—";
  if (type === "currency") return `R$ ${String(value)}`;
  if (type === "percent") return `${String(value)}%`;
  return String(value);
}

export default function MudancasPage() {
  const data = loadWebData("contract-changes.json");
  const finance = data.contractFinance ?? {};
  const events = (data.events ?? []).slice(0, 200);
  const historyReady = data.status === "history_available";

  return (
    <>
      <section className="page-hero">
        <div className="shell">
          <span className="eyebrow">Histórico auditável</span>
          <h1>O que mudou nos contratos entre snapshots oficiais.</h1>
          <p>O histórico compara somente snapshots completos da mesma grade municipal e o mesmo identificador oficial. Ausência, semelhança de nome ou objeto nunca vira alteração por inferência.</p>
          <div className="kicker-row">
            <span className={`badge ${historyReady ? "green" : ""}`}>{integer(data.summary?.comparableSnapshots ?? 0)} snapshots comparáveis</span>
            <span className="badge">{integer(data.summary?.events ?? 0)} mudanças observadas</span>
            <span className="badge">fonte até {data.asOf || "—"}</span>
          </div>
        </div>
      </section>

      <section className="section compacto">
        <div className="shell grid grid-2">
          <div className="notice"><span>✓</span><div><strong>Identidade:</strong> {data.identityRule}</div></div>
          <div className="notice"><span>i</span><div><strong>Comparação:</strong> {data.comparisonRule}</div></div>
        </div>
      </section>

      <section className="section compacto">
        <div className="shell">
          <div className={`notice ${finance.status === "blocked_upstream" ? "warn" : ""}`}>
            <span>{finance.status === "blocked_upstream" ? "!" : "i"}</span>
            <div>
              <strong>Contrato → empenho → liquidação → pagamento:</strong> {finance.detail}
              <div className="muted" style={{ marginTop: 6 }}>{finance.accountingRule}</div>
            </div>
          </div>
        </div>
      </section>

      <section className="section">
        <div className="shell">
          <div className="section-head enxuto">
            <div><span className="eyebrow">Série preservada</span><h2>Snapshots municipais elegíveis</h2></div>
            <p>Somente coletas com cobertura reconciliada entram na comparação.</p>
          </div>
          <div className="grid grid-3">
            {(data.snapshotsCompared ?? []).map((snapshot) => <div className="card stat" key={snapshot.date}><span className="stat-label">{snapshot.date}</span><div><span className="stat-value" style={{ fontSize: 28 }}>{integer(snapshot.records ?? 0)}</span><div className="stat-meta">contratos distintos · filtro até {snapshot.periodEnd || "—"}</div></div></div>)}
          </div>
          {!historyReady && <div className="notice warn" style={{ marginTop: 18 }}><span>!</span><div><strong>Histórico ainda insuficiente.</strong> Existe apenas um snapshot municipal completo comparável nesta série. A página já está preparada para registrar alterações automaticamente quando a próxima coleta completa da mesma fonte entrar.</div></div>}
        </div>
      </section>

      {events.length > 0 && <section className="section">
        <div className="shell">
          <div className="section-head enxuto"><div><span className="eyebrow">Mudanças observadas</span><h2>Eventos produzidos por comparação exata</h2></div><p>Até 200 eventos mais recentes.</p></div>
          <div className="card table-card"><div className="table-wrap"><table><thead><tr><th>Observado em</th><th>Contrato SIGEF</th><th>Processo</th><th>Mudança</th><th>Antes</th><th>Depois</th></tr></thead><tbody>{events.map((event, index) => <tr key={`${event.observedAt}-${event.contractKey}-${event.field || event.type}-${index}`}><td className="mono">{event.observedAt}</td><td className="mono">{event.identity?.nuContratoSigef || "—"}</td><td className="mono">{event.identity?.nuProcesso || "—"}</td><td>{event.type === "first_observed" ? "Primeira observação na série" : event.label}</td><td>{event.type === "field_changed" ? valueText(event.before, event.valueType) : "—"}</td><td>{event.type === "field_changed" ? valueText(event.after, event.valueType) : "—"}</td></tr>)}</tbody></table></div></div>
        </div>
      </section>}

      <section className="section compacto"><div className="shell"><div className="results-line"><span>Histórico descritivo; mudança observada não é, por si só, irregularidade.</span><Link href="/metodologia">Ver metodologia →</Link></div></div></section>
    </>
  );
}
