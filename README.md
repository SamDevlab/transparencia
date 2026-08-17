# Transparência Municipal

Framework aberto e replicável para coletar, preservar e analisar **receitas, despesas, agentes públicos, atividade legislativa, licitações e contratos** de municípios brasileiros com rastreabilidade até a fonte.

## Estrutura por branch

- `main`: engine genérica, sem dados de uma cidade específica.
- `city/<slug>`: configuração, fontes, evidências, seeds e publicação daquele município.

Esta branch contém a primeira implantação: **Salvador/BA**. O núcleo reutilizável permanece em `main`.

## Frontend público

A branch `city/salvador` contém um frontend **Next.js pronto para Vercel** na raiz do repositório.

```bash
npm install
npm run build
npm run dev
```

O `prebuild` lê os snapshots auditados em `cities/salvador/data/` e gera datasets compactos em `public/data/`. Nenhuma API Python, banco externo ou variável de ambiente é necessária para publicar a versão atual.

Rotas:

- `/` — visão geral;
- `/licitacoes` — pesquisa e filtros sobre as 2.306 aquisições do recorte publicado;
- `/financas` — receita, despesa, funções e credores agregados;
- `/contratos` — totalizadores e execução por unidade, com cobertura da grade detalhada explicitada;
- `/camara` — composição observada, produção legislativa e prestação de contas institucional;
- `/metodologia` — regras editoriais, cobertura e fontes.

Guia de deploy: [`docs/VERCEL.md`](docs/VERCEL.md).

## Objetivos

- responder quanto um município arrecada e gasta;
- ligar despesas a órgão, favorecido, contrato e licitação quando a fonte permite;
- acompanhar Legislativo sem confundir gasto institucional com gasto individual;
- reconciliar contratações municipais com PNCP;
- preservar evidência bruta e SHA-256;
- tornar cada afirmação reproduzível e citável;
- publicar uma interface acessível sem esconder as limitações de cobertura.

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
