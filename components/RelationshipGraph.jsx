import Link from "next/link";

export default function RelationshipGraph({ nodes = [] }) {
  if (!nodes.length) return null;
  return (
    <div className="relacao-grafo" aria-label="Mapa de relações">
      {nodes.map((node, index) => (
        <div className="relacao-passo" key={`${node.tipo}-${node.titulo}-${index}`}>
          {node.href ? (
            <Link className="relacao-no" href={node.href}>
              <span>{node.tipo}</span><strong>{node.titulo}</strong>{node.detalhe && <small>{node.detalhe}</small>}
            </Link>
          ) : (
            <div className="relacao-no">
              <span>{node.tipo}</span><strong>{node.titulo}</strong>{node.detalhe && <small>{node.detalhe}</small>}
            </div>
          )}
          {index < nodes.length - 1 && <div className="relacao-seta" aria-hidden="true">→</div>}
        </div>
      ))}
    </div>
  );
}
