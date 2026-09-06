# Contributing to Transparência Municipal

Este projeto trata rastreabilidade e semântica dos dados como parte da correção do software. Uma contribuição não deve apenas produzir um valor: deve preservar o caminho até a fonte que sustenta esse valor.

## Validação local

```bash
python -m pip install -e '.[dev]'
ruff check .
pytest -q
```

## Regras de contribuição

- preserve evidência bruta e metadados de origem quando a fonte permitir;
- não transforme ausência de coleta em remoção factual sem snapshots comparáveis;
- não use fuzzy matching como prova de identidade oficial;
- não misture empenho, liquidação e pagamento em um único fato contábil;
- valores monetários canônicos devem manter precisão exata em centavos;
- dados derivados não podem ganhar precisão ou certeza maior que a fonte;
- mudanças de schema/normalização exigem testes de compatibilidade e proveniência.

## Novo adaptador municipal

Use `cities/_template` como ponto de partida e mantenha detalhes locais fora do core genérico.

Documente:

- fonte oficial;
- filtros/escopo consultados;
- paginação;
- critérios de completude;
- chaves de identidade disponíveis;
- campos ausentes/ambíguos;
- política de snapshots e comparação temporal.

## Mudanças financeiras

Evite `float` como representação canônica de moeda. O projeto mantém valores exatos para cálculos e agregações; qualquer representação de compatibilidade/apresentação não deve virar a fonte da aritmética financeira.

## Pull requests

Explique o problema, a regra semântica afetada, os testes executados e qualquer impacto em proveniência, completude ou comparabilidade histórica.
