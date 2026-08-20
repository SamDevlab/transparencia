# Inteligência econômica — Bahia e Salvador

## Objetivo

Adicionar ao projeto uma camada pública de inteligência econômica que responda, com dados verificáveis:

- o que a Bahia mais exporta e importa;
- quais países concentram o fornecimento ou a demanda;
- quais posições SH4 apresentam saldo comercial negativo ou positivo;
- quais produtos apresentam crescimento relevante de importação;
- quais cadeias merecem estudo de desenvolvimento local;
- o que empresas domiciliadas em Salvador importam e exportam;
- como Salvador se compara com a Bahia sem misturar metodologias;
- quais relações podem futuramente ser estudadas para dependência de outros estados.

## Regra metodológica central

### Bahia — dados gerais do Comex Stat

Nas exportações por UF, a SECEX considera a **UF produtora da mercadoria**. Nas importações, a UF corresponde ao **domicílio fiscal da empresa importadora**. O sistema mantém essa diferença visível.

### Salvador — dados por município

O município representa o **domicílio fiscal da empresa exportadora/importadora**. Portanto:

- exportação registrada para Salvador não prova que o bem foi produzido em Salvador;
- importação registrada para Salvador não prova que o bem foi consumido em Salvador;
- os números são chamados no frontend de `comércio exterior de empresas domiciliadas em Salvador`.

O detalhamento municipal é limitado oficialmente a SH4 para proteger sigilo fiscal.

### Dependência de outros estados

Comex Stat mede comércio exterior, não compras interestaduais. A camada de dependência de outros estados será construída separadamente com a Matriz de Insumo-Produto da Bahia/SEI e outras fontes inter-regionais adequadas. O projeto não usa importação internacional como substituto de dependência interestadual.

## Camadas implementadas

### 1. Balança e fluxo

Para Bahia e Salvador:

- exportações FOB;
- importações FOB;
- corrente de comércio;
- saldo comercial;
- série mensal;
- comparação com o mesmo período do ano anterior.

### 2. Produtos SH4

Para cada posição:

- exportações;
- importações;
- saldo;
- peso líquido;
- participação nas importações/exportações;
- variação interanual;
- principal país de origem/destino;
- concentração por país.

### 3. Países

- principais origens das importações;
- principais destinos das exportações;
- participação do maior parceiro;
- concentração dos parceiros por produto.

### 4. Triagem produtiva

O projeto calcula um **Índice de Triagem Produtiva (0–100)**. Ele é uma heurística explicável para priorizar estudos, não uma recomendação de investimento ou política industrial.

Componentes atuais:

- 30 pontos: escala das importações;
- 25 pontos: déficit comercial do produto;
- 15 pontos: crescimento interanual das importações;
- 15 pontos: concentração da origem em poucos países;
- 15 pontos: evidência de capacidade relacionada, aproximada pela presença simultânea de exportações do mesmo SH4.

Cada resultado guarda os componentes que formaram sua nota. O índice não considera sozinho custos, tecnologia, disponibilidade de insumos, licenciamento, produtividade, infraestrutura, capital, escala mínima eficiente ou viabilidade ambiental.

### 5. Encadeamentos da Bahia

A Matriz de Insumo-Produto da SEI é registrada como fonte estruturante para uma segunda fase. A tela informa o estado de cobertura e não inventa uma nota de dependência interestadual enquanto a matriz não estiver normalizada.

## Integração com transparência pública

A camada econômica é ligada à transparência de forma conservadora:

- órgãos, processos, contratos e fornecedores públicos continuam baseados em identificadores/documentos oficiais;
- demanda pública não é automaticamente associada a um SH4 por similaridade textual;
- futuras relações `compra pública -> cadeia produtiva` precisarão de uma tabela de correspondência revisada;
- o portal passa a ter um painel de cobertura/fonte para mostrar o que está atualizado, parcial ou ainda não implementado.

## Atualização

O workflow `economic-intelligence.yml` consulta mensalmente a API oficial do Comex Stat, preserva a resposta bruta com hash SHA-256 e publica apenas agregados adequados ao frontend.

O coletor tenta descobrir o último mês consolidado na API. Em falha dessa descoberta, usa o último mês calendário completo e registra a decisão no manifesto.

## Princípios

1. Saldo negativo não significa automaticamente problema econômico.
2. Importação pode representar insumo essencial, ganho de produtividade ou ausência racional de produção local.
3. Substituição de importações não é tratada como objetivo universal.
4. Concentração em um país é um indicador de exposição, não prova de vulnerabilidade crítica.
5. O índice produtivo serve para triagem; qualquer decisão exige estudo setorial específico.
6. Bahia e Salvador nunca são comparados sem exibir a diferença metodológica do Comex Stat.
