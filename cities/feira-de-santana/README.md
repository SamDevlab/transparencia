# Feira de Santana / BA

Segunda implantação do framework, criada para validar que as garantias extraídas de `city/salvador` funcionam em outra cidade sem copiar endpoints ou regras municipais.

## Identidade

- Município: Feira de Santana
- UF: BA
- Código IBGE: `2910800`
- CNPJ institucional da Prefeitura: `14.043.574/0001-51`

## Fontes verificadas

### Executivo

- Portal da Transparência Cidadã: `https://transparencia.feiradesantana.ba.gov.br/`
  - o índice oficial apresenta Despesa, Receita, Licitação, Dispensas, Contratos, Servidores, Obras, Diárias e outros conjuntos;
  - neste estágio o portal é apenas uma entrada verificada: paginação, API e completude de cada conjunto ainda precisam ser provadas separadamente.
- Diário Oficial Eletrônico: `https://diariooficial.feiradesantana.ba.gov.br/`
  - contém atos, licitações, contratos/aditivos, decretos e outras publicações;
  - não substitui a execução financeira estruturada.
- Portal institucional: `https://www.feiradesantana.ba.gov.br/`

### Legislativo

- Câmara Municipal: `https://www.feiradesantana.ba.leg.br/`
- Portal de Transparência da Câmara: `https://transparencia.feiradesantana.ba.leg.br/adm/upload/contaspublicas/index.php?view=o-portal`
  - declara cobertura de receitas, despesas, folha, licitações, contratos e execução orçamentária.

### Complementar

- PNCP: complementar; nunca substitui uma grade municipal que venha a ser comprovadamente completa.
- IBGE: referência do código municipal.

## Estado inicial

Nenhum conjunto municipal é marcado como `complete_for_filter` nesta fase. O primeiro workflow usa o coletor genérico `collect-pages` da `main` para preservar os pontos de entrada oficiais e gerar cobertura `partial`/`unavailable`. A próxima etapa é descobrir, fonte por fonte, a estrutura real de dados e só então criar coletores específicos.

## Regras herdadas do core

- sem fonte, sem fato;
- completude por fonte/filtro;
- relações apenas por identificadores oficiais exatos;
- empenho, liquidação e pagamento separados;
- fornecedor público somente com CNPJ empresarial estruturado;
- histórico somente entre snapshots completos e comparáveis.
