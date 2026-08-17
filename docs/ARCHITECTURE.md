# Arquitetura

`main` contém o núcleo agnóstico de município. Cada implantação municipal vive em `city/<slug>` e adiciona `cities/<slug>/`.

## Contrato mínimo de cidade

- `city.json`: slug, nome oficial, UF, código IBGE e CNPJ municipal opcional.
- `sources.csv`: catálogo de fontes com autoridade e escopo.
- `data/seed/`: fatos manualmente revisados e sempre acompanhados de `source_url`.
- `data/evidence/`: documentos brutos que justificam fatos relevantes.
- `data/raw/`: snapshots automatizados; normalmente fora do Git quando volumosos.

## Princípio

Sem fonte, sem fato. Fonte secundária orienta investigação; a fonte primária sustenta a afirmação sempre que disponível.
