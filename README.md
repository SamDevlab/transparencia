# Transparência Municipal

Framework aberto e replicável para coletar, preservar e analisar **receitas, despesas, agentes públicos, atividade legislativa, licitações e contratos** de municípios brasileiros com rastreabilidade até a fonte.

## Estrutura por branch

- `main`: núcleo genérico, sem dados de uma cidade específica.
- `city/<slug>`: configuração, fontes, evidências, dados revisados e publicação daquele município.

Esta branch contém a primeira implantação: **Salvador/BA**. O núcleo reutilizável permanece em `main`.

## Frontend público

A branch `city/salvador` contém um frontend **Next.js pronto para Vercel** na raiz do repositório.

```bash
npm install
npm run build
npm run dev
```

Antes da construção, o gerador seleciona automaticamente o **snapshot auditado mais recente** que possui dados financeiros, aquisições e estado final validado na mesma data. A partir dele, cria arquivos compactos em `public/data/`. Nenhuma API Python, banco externo ou variável de ambiente é necessária para publicar a versão atual.

Principais rotas:

- `/` — entrada orientada por perguntas;
- `/buscar` — busca geral por pessoa, empresa, CNPJ, processo, contrato, órgão, credor ou receita;
- `/dinheiro` — navegação do agregado para relações documentadas;
- `/licitacoes` — pesquisa e filtros sobre as aquisições municipais;
- `/processos/[id]` — perfil do processo/aquisição, referências, relações exatas e linha do tempo;
- `/financas` — receita, despesa, funções e credores agregados;
- `/contratos` — totais municipais e contratos individualizados preservados do PNCP;
- `/fornecedores` e `/fornecedores/[id]` — diretório e perfis de fornecedores;
- `/orgaos` e `/orgaos/[id]` — diretório e perfis de órgãos;
- `/agentes` e `/agentes/[id]` — agentes públicos e perfis individuais;
- `/camara` — atividade legislativa e prestação de contas institucional;
- `/comparar` — comparação de órgãos no mesmo recorte;
- `/analises` — pontos descritivos para orientar leitura documental;
- `/metodologia` — regras editoriais, cobertura e fontes.

Guia de publicação: [`docs/VERCEL.md`](docs/VERCEL.md).

## Objetivos

- responder quanto um município arrecada e gasta;
- ligar despesas, processos, contratos e fornecedores somente quando a fonte permite;
- acompanhar agentes públicos e Legislativo sem confundir gasto institucional com gasto individual;
- reconciliar contratações municipais com PNCP usando identificadores exatos;
- preservar evidência bruta e SHA-256;
- tornar cada afirmação reproduzível e citável;
- facilitar a consulta pública sem esconder limitações de cobertura.

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

**Sem fonte, sem fato.** Dados derivados precisam manter ligação explícita com a origem e não podem aumentar artificialmente a precisão do documento publicado. Repetição de fornecedor, concentração, dispensa, inexigibilidade ou valor elevado são características descritivas para orientar consulta; não são conclusões automáticas de irregularidade.
