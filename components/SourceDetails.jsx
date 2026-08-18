export default function SourceDetails({ title = "Origem deste dado", source, secondary, observedAt, note, method }) {
  if (!source && !secondary && !note && !method) return null;
  return (
    <details className="fonte-detalhes">
      <summary>{title}</summary>
      <div className="fonte-conteudo">
        {method && <p><strong>Como foi relacionado:</strong> {method}</p>}
        {note && <p><strong>Observação:</strong> {note}</p>}
        {observedAt && <p><strong>Verificado em:</strong> {String(observedAt).slice(0, 10).split("-").reverse().join("/")}</p>}
        <div className="fonte-acoes">
          {source && <a className="button" href={source} target="_blank" rel="noreferrer">Abrir fonte oficial ↗</a>}
          {secondary && <a className="button discreto" href={secondary} target="_blank" rel="noreferrer">Abrir fonte complementar ↗</a>}
        </div>
      </div>
    </details>
  );
}
