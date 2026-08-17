# Transparência Municipal

Framework aberto e replicável para coletar, preservar e analisar **receitas, despesas, agentes públicos, atividade legislativa, licitações e contratos** de municípios brasileiros com rastreabilidade até a fonte.

## Estrutura por branch

- `main`: engine genérica, sem dados de uma cidade específica.
- `city/<slug>`: configuração, fontes, evidências e seeds daquele município.

A primeira implantação é Salvador/BA na branch `city/salvador`.

## Objetivos

- responder quanto um município arrecada e gasta;
- ligar despesas a órgão, favorecido, contrato e licitação quando a fonte permite;
- acompanhar Legislativo sem confundir gasto institucional com gasto individual;
- reconciliar contratações municipais com PNCP;
- preservar evidência bruta e SHA-256;
- tornar cada afirmação reproduzível e citável.

## Criando uma nova cidade

```bash
cp -R cities/_template cities/minha-cidade
# edite city.json e sources.csv
python -m transparencia --city minha-cidade sources
```

Para uma implantação oficial, crie uma branch `city/minha-cidade` a partir de `main`.

## PNCP

```bash
python -m transparencia --city minha-cidade collect-pncp \
  --start 2026-01-01 --end 2026-01-31 --scope executivo
```

O coletor usa UF e código IBGE da configuração da cidade, descobre modalidades ativas no próprio domínio oficial do PNCP e preserva os snapshots consultados.

## Banco local

```bash
python -m transparencia --city minha-cidade build-db
```

O SQLite gerado contém `city_slug` em todas as tabelas factuais para impedir mistura silenciosa entre municípios.

## Regra editorial

**Sem fonte, sem fato.** Dados derivados precisam manter ligação explícita com a origem e não podem aumentar artificialmente a precisão do documento publicado.
