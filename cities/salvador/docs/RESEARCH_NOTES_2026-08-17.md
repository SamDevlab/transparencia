# Notas de pesquisa — 17/08/2026

Este arquivo registra achados usados para desenhar a coleta, sem transformar automaticamente todo texto em indicador.

## Prefeitura / transparência

O portal legado de Despesas informa que permite consultar despesas executadas do Município e apresenta fases de empenho, liquidação e pagamento, filtros por favorecido e entidade executora, gastos diretos e gastos com diárias. O detalhamento prevê credor, valor, função/subfunção/programa/ação, natureza da despesa, processo, referência a dispensa/inexigibilidade e contrato/convênio.

Fonte: https://antigotransparencia.salvador.ba.gov.br/Modulos/Despesas.aspx

O módulo de Licitações e Contratos declara cobrir licitações, modalidades licitatórias, contratos e obras, e direciona o acompanhamento dos processos para o Portal de Compras de Salvador.

Fonte: https://antigotransparencia.salvador.ba.gov.br/Modulos/LicitacaoContratos.aspx

## PNCP

A documentação oficial informa que a consulta é pública e que o PNCP centraliza contratações públicas cobertas pela Lei 14.133/2021. O manual documenta endpoints REST para contratação, itens, documentos, histórico e contratos/empenhos.

Fontes:
- https://www.gov.br/pncp/pt-br/acesso-a-informacao/dados-abertos
- https://pncp.gov.br/manual/pt-br/latest/singlehtml/

## Câmara

A página oficial lista os vereadores da 20ª Legislatura (2025-2028). A Câmara também publica prestação de contas, execução orçamentária, Ordem do Dia e processos licitatórios em trilhas próprias.

Fontes:
- https://www.cms.ba.gov.br/vereadores
- https://www.cms.ba.gov.br/transparencia/prestacao-de-contas
- https://www.cms.ba.gov.br/transparencia/exec-orcamentaria-financeira
- https://www.cms.ba.gov.br/transparencia/ordem-do-dia
- https://www.cms.ba.gov.br/processos-licitatorios

O balanço oficial de 2025 registra 155 sessões (86 ordinárias, 34 solenes, 32 especiais, 1 extraordinária e 2 itinerantes) e 580 projetos de lei apresentados por vereadores/Mesa, com 121 matérias de 2025 aprovadas e 20 de exercícios anteriores. Esse é um indicador agregado; não substitui a coleta individual de proposições.

Fonte: https://www.cms.ba.gov.br/noticias/06-01-2026-camara-divulga-balanco-da-producao-legislativa-de-2025

## Transparência Brasil

A Transparência Brasil mantém projetos e análises sobre gasto público, orçamento, emendas e contratos. Nesta pesquisa ela é tratada como fonte metodológica/complementar; não foi encontrada evidência de que opere atualmente um banco completo de receitas/despesas/licitações da Prefeitura de Salvador que substitua os portais oficiais.

Fontes:
- https://www.transparencia.org.br/projetos/
- https://www.transparencia.org.br/areas-tematicas/qualidade-do-gasto-publico


### Divergência interna identificada

A página do projeto Achados e Pedidos informa período de vigência de jul/2016 a dez/2023, mas notícia institucional da própria Transparência Brasil de 02/02/2026 afirma que o projeto encerrou suas atividades em 31/01/2026. O dataset registra `date_conflict` e preserva as duas URLs em vez de resolver a divergência por inferência.

Fontes:
- https://www.transparencia.org.br/projetos/achados-e-pedidos/
- https://www.transparencia.org.br/noticias/tb-e-abraji-encerram-o-maior-repositorio-de-dados-da-lei-de-acesso-a-informacao
