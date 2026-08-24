import Link from "next/link";
import { brl, integer, loadWebData } from "../../lib/web-data";

export const metadata = { title: "Pontos para análise" };

function relationLabel(row) {
  const methods = new Set([
    ...(row.linkMethods ?? []),
    ...(row.contratos ?? []).flatMap((contract) => contract.linkMethods ?? []),
  ]);
  const direct = methods.has("exact_process_number");
  const pncpControl = methods.has("pncp_procurement_control_chain");
  if (direct && pncpControl) return "duas provas exatas";
  if (pncpControl) return "controle PNCP exato";
  return "processo exato";
}

export default function AnalisesPage() {
  const data = loadWebData("analysis.json");
  const exactSummary = data.exactLinkSummary ?? {};
  return (
    <>
      <section className="page-hero"><div className="shell"><span className="eyebrow">Pontos para análise</span><h1>O sistema aponta onde vale abrir os documentos.</h1><p>Valor elevado, contratação direta, repetição de fornecedor e concentração são apresentados como características descritivas. Nenhum desses sinais, isoladamente, é classificado como irregularidade.</p></div></section>

      <section className="section compacto"><div className="shell"><div className="notice warn"><span>!</span><div><strong>Regra editorial:</strong> esta página não é um ranking de corrupção. Ela ajuda a priorizar leitura documental e comparação.</div></div></div></section>

      <section className="section"><div className="shell"><div className="grid grid-4"><div className="card stat accent"><span className="stat-label">Aquisições acima de R$ 1 mi</span><div><span className="stat-value">{integer(data.highValueAcquisitions.length)}</span><div className="stat-meta">amostra exibida nesta página</div></div></div><div className="card stat"><span className="stat-label">Contratações diretas</span><div><span className="stat-value">{integer(data.directAcquisitions.length)}</span><div className="stat-meta">maiores registros exibidos</div></div></div><div className="card stat blue"><span className="stat-label">Fornecedores repetidos</span><div><span className="stat-value">{integer(data.repeatSuppliers.length)}</span><div className="stat-meta">2 ou mais contratos no recorte PNCP</div></div></div><div className="card stat"><span className="stat-label">Processos com vínculo exato</span><div><span className="stat-value">{integer(data.exactCrossSourceLinks.length)}</span><div className="stat-meta">{integer(exactSummary.processesWithDirectExactContracts ?? 0)} diretos · {integer(exactSummary.processesNewlyLinkedByPncpProcurementControl ?? 0)} novos via controle PNCP</div></div></div></div></div></section>

      <section className="section"><div className="shell"><div className="section-head enxuto"><div><span className="eyebrow">Valores elevados</span><h2>Aquisições acima de R$ 1 milhão</h2></div><Link className="button" href="/licitacoes?filtro=milhao">Abrir filtro completo →</Link></div><div className="card table-card"><div className="table-wrap"><table><thead><tr><th>Processo</th><th>Órgão</th><th>Objeto</th><th>Tipo</th><th>Valor</th><th></th></tr></thead><tbody>{data.highValueAcquisitions.slice(0, 15).map((row) => <tr key={row.id}><td className="mono">{row.processo || row.numero || "—"}</td><td>{row.orgao || "—"}</td><td className="object-cell">{row.objeto || "—"}</td><td>{row.tipo || row.modalidade || "—"}</td><td><strong className="mono">{brl(row.valor)}</strong></td><td><Link className="button" href={`/processos/${encodeURIComponent(row.id)}`}>Abrir →</Link></td></tr>)}</tbody></table></div></div></div></section>

      <section className="section"><div className="shell grid grid-2"><div><div className="section-head enxuto"><div><span className="eyebrow">Repetição</span><h2>Fornecedores com mais de um contrato</h2></div></div><div className="analise-lista">{data.repeatSuppliers.slice(0, 12).map((row) => <Link className="analise-card" href={`/fornecedores/${encodeURIComponent(row.id)}`} key={row.id}><span className="badge">{row.quantidadeContratos} contratos</span><strong>{row.nome}</strong><small>{row.documento || "Documento não informado"}</small><b>{brl(row.valorGlobal)}</b></Link>)}</div></div><div><div className="section-head enxuto"><div><span className="eyebrow">Concentração</span><h2>Participação relevante em uma unidade</h2></div></div><div className="analise-lista">{data.concentratedSuppliers.slice(0, 12).map((row) => <Link className="analise-card" href={`/fornecedores/${encodeURIComponent(row.id)}`} key={row.id}><span className="badge yellow">{Math.round(row.maiorParticipacaoEmUnidade * 100)}% na principal unidade</span><strong>{row.nome}</strong><small>{row.unidades[0]?.nome || "Unidade não informada"}</small><b>{brl(row.valorGlobal)}</b></Link>)}</div></div></div></section>

      <section className="section"><div className="shell"><div className="section-head enxuto"><div><span className="eyebrow">Reconciliação</span><h2>Processos com relações documentais exatas</h2></div><p>O vínculo só nasce de identificadores oficiais: igualdade do número do processo ou cadeia processo municipal → contratação PNCP → controle oficial da contratação → contrato PNCP. Nome, objeto, fornecedor, valor, data e similaridade textual não criam relação.</p></div><div className="analise-lista">{data.exactCrossSourceLinks.slice(0, 20).map((row) => <Link className="analise-card horizontal" href={`/processos/${encodeURIComponent(row.processId ?? row.processoId)}`} key={row.processId ?? row.processoId}><div><span className="badge green">{relationLabel(row)}</span><strong className="mono">{row.processo || "—"}</strong><small>{row.orgao || "—"}</small></div><div><b>{row.contratos.length} contrato(s) documentado(s)</b><small>{row.contratos.map((c) => c.fornecedor).filter(Boolean).join(" · ")}</small></div></Link>)}</div></div></section>
    </>
  );
}
