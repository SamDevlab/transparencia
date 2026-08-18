import { dateBR } from "../lib/web-data";

export default function Timeline({ items = [], empty = "Nenhum marco temporal adicional foi publicado para este registro." }) {
  if (!items.length) return <div className="card empty">{empty}</div>;
  return (
    <ol className="linha-tempo">
      {items.map((item, index) => (
        <li key={`${item.data}-${item.titulo}-${index}`}>
          <span className="linha-ponto" aria-hidden="true" />
          <div className="linha-data mono">{dateBR(item.data)}</div>
          <div className="linha-corpo">
            <span className="badge">{item.tipo || "Marco"}</span>
            <strong>{item.titulo}</strong>
            {item.descricao && <p>{item.descricao}</p>}
            {item.fonte && <a href={item.fonte} target="_blank" rel="noreferrer">Fonte ↗</a>}
          </div>
        </li>
      ))}
    </ol>
  );
}
