# Salvador/BA

Primeira implantação do framework `transparencia`.

## Escopo inicial

- receitas e despesas do Executivo municipal;
- licitações e contratos, com reconciliação PNCP;
- Câmara Municipal: composição, atividade legislativa e execução orçamentária;
- Transparência Brasil como referência metodológica/complementar;
- fontes federais apenas quando ajudam a explicar relações com o Município, sem substituir a contabilidade local.

## Fontes

O catálogo auditável está em `sources.csv`. Cada seed em `data/seed/` mantém `source_url` e data de observação. Evidências documentais relevantes são preservadas em `data/evidence/` com SHA-256 no manifesto.

## Coleta

```bash
python -m transparencia --city salvador sources
python -m transparencia --city salvador collect-pncp --start 2026-01-01 --end 2026-01-31 --scope executivo
python -m transparencia --city salvador build-db
```

## Limite editorial

A presença de um nome na página da Câmara não é, sozinha, prova de exercício ininterrupto do mandato em uma data específica. Gastos agregados da Câmara não são rateados entre vereadores sem documentação nominal.
