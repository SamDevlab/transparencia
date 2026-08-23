# Limitações conhecidas — Salvador/BA

Este documento registra **limitações duráveis do modelo e das fontes**. Estado atual, contagens e próximos passos ficam somente em [`PROJECT_STATUS.md`](PROJECT_STATUS.md); detalhes de cada execução ficam nos respectivos `coverage.json`, `summary.json` e snapshots.

## 1. Cobertura depende da fonte e do filtro

Uma coleta completa significa apenas que a fonte consultada chegou a um fim comprovado para aquele filtro e período. Indisponibilidade, timeout, rate limit ou falha de parsing nunca são convertidos em “zero registros”.

## 2. Portal municipal e contratos

O Portal da Transparência de Salvador usa uma aplicação JavaScript e APIs consumidas pelo frontend oficial. A existência de uma rota no código do frontend não garante disponibilidade operacional.

A grade municipal de contratos pode apresentar alta latência. O coletor usa janelas adaptativas, preserva respostas bem-sucedidas e mantém intervalos falhos como `partial`.

## 3. PNCP é complementar

O PNCP não representa automaticamente 100% do histórico municipal. A cobertura depende da alimentação realizada pelos órgãos e dos CNPJs municipais descobertos.

O CNPJ principal do Município não deve ser tratado como sinônimo de todas as entidades, fundos ou unidades com personalidade própria. Contratos PNCP só podem ser considerados completos para o município quando a descoberta upstream dos órgãos também estiver comprovadamente completa.

## 4. Câmara Municipal

O sistema financeiro público da CMS usa ScriptCase e navegação com sessão. A coleta precisa reproduzir a paginação real do formulário; parâmetros de paginação presumidos não são aceitos como evidência.

Mesmo quando a visão consultada é exaurida, a completude vale somente para aquela visão/filtro. Outros filtros ou sistemas podem conter registros adicionais.

## 5. Semântica contábil

Dotação, empenho, liquidação e pagamento são estágios distintos. Um registro de empenho permanece `stage=commitment` até existir fonte específica que comprove outro estágio.

Valor contratual, valor empenhado e valor efetivamente pago também não são tratados como equivalentes.

## 6. Identidade e privacidade

Credor não é associado a agente político por similaridade de nome. O vínculo exige nome oficial exato normalizado ou alias documentado por fonte oficial.

CPF individual é mascarado na camada normalizada. A camada pública de fornecedores exige CNPJ empresarial estruturado.

A composição política também é temporal: uma lista geral de vereadores não basta para inferir exercício do mandato em uma data sem atos oficiais quando houver licença, suplência ou posse.

## 7. Hierarquia de evidência

Documentos contábeis, leis, empenhos, contratos e registros oficiais têm precedência sobre notícias institucionais quando ambos existem. Notícias podem fornecer contexto, mas não substituem a fonte primária.

Valores publicados de forma arredondada permanecem arredondados; o projeto não cria precisão fictícia.

## 8. Sinais de auditoria não são acusações

Valor alto, concentração de fornecedor, dispensa ou inexigibilidade podem orientar investigação documental, mas não constituem prova de desperdício, favorecimento ou ilícito.
