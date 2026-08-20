# Transparência Municipal + Inteligência Econômica

Framework aberto e replicável para coletar, preservar e analisar **receitas, despesas, agentes públicos, atividade legislativa, licitações, contratos e indicadores econômicos regionais** com rastreabilidade até a fonte.

## Estrutura por branch

- `main`: núcleo genérico, sem dados de uma cidade específica.
- `city/<slug>`: configuração, fontes, evidências, dados revisados e publicação daquele município.

Esta branch contém a primeira implantação: **Salvador/BA**, integrada a uma camada regional de **Bahia** em `regions/bahia/`.

## Frontend público

A branch `city/salvador` contém um frontend **Next.js pronto para Vercel** na raiz do repositório.

```bash
npm install
npm run build
npm run dev
```

O `prebuild` executa duas etapas:

1. seleciona automaticamente o snapshot auditado mais recente da transparência de Salvador;
2. seleciona o snapshot econômico mais recente da Bahia/Salvador, quando disponível.

Se a fonte econômica estiver indisponível ou ainda não houver snapshot, o site continua compilando e publica a limitação em vez de exibir valores zero.

## Principais rotas

### Transparência pública

- `/` — entrada orientada por perguntas;
- `/buscar` — busca geral por pessoa, empresa, CNPJ, processo, contrato, órgão, credor, receita, produto ou país;
- `/dinheiro` — navegação do agregado para relações documentadas;
- `/licitacoes` — pesquisa e filtros sobre as aquisições municipais;
- `/processos/[id]` — perfil do processo/aquisição, referências, relações exatas e linha do tempo;
- `/financas` — receita, despesa, funções e credores agregados;
- `/contratos` — totais municipais e contratos individualizados preservados do PNCP;
- `/fornecedores` e `/fornecedores/[id]` — diretório e perfis de fornecedores;
- `/orgaos` e `/orgaos/[id]` — diretório e perfis de órgãos;
- `/agentes` e `/agentes/[id]` — agentes públicos e perfis individuais;
- `/camara` — atividade legislativa e prestação de contas institucional;
- `/comparar` — comparação de órgãos;
- `/analises` — pontos descritivos para orientar leitura documental;
- `/transparencia` — cobertura, atualização e limitações de todas as fontes.

### Inteligência econômica

- `/economia` — visão geral Bahia + Salvador;
- `/economia/bahia` — produtos SH4, países, exportações, importações, saldo e concentração;
- `/economia/salvador` — comércio exterior de empresas domiciliadas em Salvador;
- `/economia/oportunidades` — Índice de Triagem Produtiva explicável, de 0 a 100;
- `/metodologia` — regras editoriais e distinções metodológicas.

## Comércio exterior

O coletor `src/transparencia/collectors/comex.py` usa a API oficial do **MDIC / Comex Stat**. O workflow `.github/workflows/economic-intelligence.yml` atualiza a base mensalmente e preserva requisição, resposta e SHA-256.

Execução manual:

```bash
pip install -e '.[dev]'
pytest -q tests/test_comex.py
python scripts/collect-bahia-economy.py
```

### Bahia

Nos dados gerais do Comex Stat:

- exportação por UF = UF produtora da mercadoria;
- importação por UF = domicílio fiscal da empresa importadora.

### Salvador

No módulo por municípios:

- exportação e importação = domicílio fiscal da empresa declarante;
- isso não prova que o produto foi fabricado ou consumido fisicamente em Salvador;
- o detalhamento econômico publicado pelo projeto é tratado em SH4.

### Dependência de outros estados

Comércio exterior não mede compras da Bahia vindas de São Paulo, Minas Gerais, Pernambuco etc. A camada interestadual foi separada e tem como fonte estruturante a **Matriz de Insumo-Produto da Bahia/SEI**. Enquanto essa fonte não estiver normalizada, o portal mostra `fonte mapeada` e não inventa um índice interestadual.

## Índice de Triagem Produtiva

A nota de 0 a 100 prioriza setores para **estudo adicional**, usando:

- escala das importações: até 30 pontos;
- déficit comercial: até 25;
- crescimento interanual das importações: até 15;
- concentração em países fornecedores: até 15;
- presença de exportações relacionadas no mesmo SH4: até 15.

A nota não é recomendação de investimento, protecionismo ou substituição de importações. Um estudo setorial ainda precisa avaliar tecnologia, insumos, infraestrutura, escala, produtividade, capital, regulação e impactos ambientais.

Metodologia completa: [`docs/ECONOMIC_INTELLIGENCE.md`](docs/ECONOMIC_INTELLIGENCE.md).
Guia da Vercel: [`docs/VERCEL.md`](docs/VERCEL.md).

## Objetivos

- responder quanto Salvador arrecada e gasta;
- ligar despesas, processos, contratos e fornecedores somente quando a fonte permite;
- acompanhar agentes públicos e Legislativo sem confundir gasto institucional com gasto individual;
- reconciliar contratações municipais com PNCP usando identificadores exatos;
- mostrar o que Bahia e Salvador importam/exportam e com quais parceiros;
- identificar dependências e cadeias que merecem estudo sem transformar heurística em fato;
- preservar evidência bruta e SHA-256;
- facilitar a consulta pública sem esconder limitações de cobertura.

## Criando uma nova cidade

```bash
cp -R cities/_template cities/minha-cidade
# edite city.json e sources.csv
python -m transparencia --city minha-cidade sources
```

Para uma implantação oficial, crie uma branch `city/minha-cidade` a partir de `main`.

## Regra editorial

**Sem fonte, sem fato.** Dados derivados precisam manter ligação explícita com a origem e não podem aumentar artificialmente a precisão do documento publicado. Repetição de fornecedor, concentração, déficit, contratação direta ou valor elevado são características descritivas para orientar consulta; não são conclusões automáticas de irregularidade ou de viabilidade econômica.
