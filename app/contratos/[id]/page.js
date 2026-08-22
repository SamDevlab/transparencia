import { notFound } from "next/navigation";
import Link from "next/link";
import SourceDetails from "../../../components/SourceDetails";
import { brl, dateBR, loadWebData } from "../../../lib/web-data";

function contractRows(data) {
  const primary = (data.rows ?? []).map((row) => ({ ...row, _layer: "primary", _sourceName: data.source || "Fonte principal" }));
  const complementary = (data.complementary?.rows ?? []).map((row) => ({ ...row, _layer: "complementary", _sourceName: data.complementary?.source || "PNCP" }));
  return [...primary, ...complementary];
}

export async function generateMetadata({ params }) {
  const { id } = await params;
  const data = loadWebData("contracts.json");
  const row = contractRows(data).find((item) => item.id === id);
  return { title: row ? `Contrato ${row.numero || row.numeroSigef || "municipal"}` : "Contrato" };
}

export default async function ContratoPage({ params }) {
  const { id } = await params;
  const contracts = loadWebData("contracts.json");
  const processes = loadWebData("processes.json");
  const row = contractRows(contracts).find((item) => item.id === id);
  if (!row) notFound();

  const relatedProcesses = (processes.rows ?? []).filter((process) =>
    (process.contratosExatos ?? []).some((contract) => contract.id === row.id),
  );
  const municipal = row.sourceSystem === "SALVADOR_TRANSPARENCIA_API_CONTRATOS" || row._layer === "primary" && contracts.sourceSystem === "SALVADOR_TRANSPARENCIA_API_CONTRATOS";
  const sourceName = municipal ? "Transparência Salvador" : row._sourceName;

  return (
    <>
      <section className="page-hero">
        <div className="shell">
          <span className="eyebrow">Contrato</span>
          <h1>{row.numero || row.numeroSigef || "Registro contratual"}</h1>
          <p>{row.objeto || "Objeto não informado na camada publicada."}</p>
          <div className="kicker-row">
            <span className="badge green">{sourceName}</span>
            {row.situacao && <span className="badge">{row.situacao}</span>}
            {row.valorGlobal != null && <span className="badge">{brl(row.valorGlobal)}</span>}
            {relatedProcesses.length > 0 && <span className="badge green">{relatedProcesses.length} vínculo(s) exato(s) com aquisição</span>}
          </div>
        </div>
      </section>

      <section className="section compacto">
        <div className="shell perfil-duas-colunas">
          <div className="card panel">
            <div className="panel-title"><h3>Identificadores</h3><span>referências administrativas</span></div>
            <dl className="perfil-dados">
              <div><dt>Contrato</dt><dd className="mono">{row.numero || "—"}</dd></div>
              {row.numeroSigef && <div><dt>Contrato SIGEF</dt><dd className="mono">{row.numeroSigef}</dd></div>}
              <div><dt>Processo</dt><dd className="mono">{row.processo || "—"}</dd></div>
              <div><dt>Órgão</dt><dd>{row.orgao || "—"}</dd></div>
              <div><dt>Unidade</dt><dd>{row.unidade || "—"}</dd></div>
              {row.codigoUnidade && <div><dt>Código da unidade</dt><dd className="mono">{row.codigoUnidade}</dd></div>}
            </dl>
          </div>
          <div className="card panel">
            <div className="panel-title"><h3>Valores e vigência</h3><span>sem confundir com execução financeira</span></div>
            <dl className="perfil-dados">
              <div><dt>Valor original/inicial</dt><dd className="mono">{row.valorInicial != null ? brl(row.valorInicial) : "—"}</dd></div>
              <div><dt>Valor atualizado/global</dt><dd className="mono">{row.valorGlobal != null ? brl(row.valorGlobal) : "—"}</dd></div>
              <div><dt>Assinatura</dt><dd>{dateBR(row.assinadoEm)}</dd></div>
              <div><dt>Início da vigência</dt><dd>{dateBR(row.vigenciaInicio)}</dd></div>
              <div><dt>Fim da vigência</dt><dd>{dateBR(row.vigenciaFim)}</dd></div>
              {row.percentualExecutado != null && <div><dt>Percentual executado</dt><dd>{String(row.percentualExecutado)}</dd></div>}
            </dl>
            <p className="muted">Valor contratual não é tratado como valor empenhado, liquidado ou pago. Esses estágios permanecem separados nas páginas financeiras.</p>
          </div>
        </div>
      </section>

      {row.fornecedor && <section className="section compacto"><div className="shell"><div className="card panel"><div className="panel-title"><h3>Fornecedor estruturado</h3><span>somente quando a fonte permite identificação segura</span></div><p><strong>{row.fornecedor}</strong></p>{row.documentoFornecedor && <p className="mono">{row.documentoFornecedor}</p>}{row.documentoFornecedor && <Link className="button" href={`/fornecedores/${encodeURIComponent(row.documentoFornecedor)}`}>Abrir perfil do fornecedor →</Link>}</div></div></section>}

      {municipal && contracts.privacyRule && <section className="section compacto"><div className="shell"><div className="notice"><span>i</span><div><strong>Privacidade da grade municipal:</strong> {contracts.privacyRule}</div></div></div></section>}

      {relatedProcesses.length > 0 && <section className="section">
        <div className="shell">
          <div className="section-head enxuto"><div><span className="eyebrow">Vínculos exatos</span><h2>Aquisições com o mesmo número oficial de processo</h2></div><p>Nenhum vínculo é criado por semelhança de objeto, fornecedor ou nome.</p></div>
          <div className="grid grid-2">{relatedProcesses.map((process) => <Link key={process.id} href={`/processos/${encodeURIComponent(process.id)}`} className="card panel"><div className="panel-title"><h3>{process.processo || process.numero || "Processo"}</h3><span>abrir processo →</span></div><p>{process.objeto || "Objeto não informado"}</p><div className="kicker-row"><span className="badge">{process.tipo || process.modalidade || "Aquisição"}</span>{process.valor != null && <span className="badge">{brl(process.valor)}</span>}</div></Link>)}</div>
        </div>
      </section>}

      <section className="section">
        <div className="shell">
          <SourceDetails source={row.fonte} title={`Fonte do contrato · ${sourceName}`} method="O perfil preserva os identificadores e campos publicados pela fonte. Relações com aquisições usam somente igualdade do número de processo após normalização documental." note="Diferenças entre Prefeitura e PNCP permanecem como diferenças de cobertura; uma fonte não é usada para preencher silenciosamente a outra." />
        </div>
      </section>

      <section className="section compacto"><div className="shell"><Link className="button" href="/contratos">← Voltar aos contratos</Link></div></section>
    </>
  );
}
