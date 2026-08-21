# Transparência estadual da Bahia

Esta camada é separada da transparência municipal de Salvador e usa fontes oficiais estaduais com cobertura explícita.

## Fontes prioritárias

- SEFAZ/AGE — Portal de Dados Abertos da Bahia / FIPLAN: receitas, despesas, pagamentos, contratos e diárias.
- SEFAZ/SAEB — dados de licitações/SIMPAS publicados no mesmo catálogo estadual.
- TCE/BA — fonte complementar de execução detalhada, contratos e procedimentos licitatórios quando os endpoints estiverem disponíveis ao coletor.

## Regra contábil

O projeto nunca trata os seguintes conceitos como equivalentes:

1. dotação/previsão;
2. empenho;
3. liquidação;
4. pagamento.

Quando um arquivo de despesas contém mais de um estágio, cada campo é somado e publicado separadamente pelo nome detectado na fonte. Um campo ausente não é preenchido com zero.

A base específica de `Pagamentos` permanece separada do estágio `pago` encontrado na base de `Despesas`. Diferença entre os dois totais não é classificada como erro, fraude ou irregularidade. Reconciliação só pode ser feita com identificadores oficiais compatíveis e documentação do escopo de cada tabela.

## Tabelas relacionais

Arquivos ZIP podem conter várias views relacionadas. O projeto:

- inspeciona cada tabela sem extraí-la permanentemente;
- identifica ano/data e campos monetários;
- escolhe uma única tabela principal por conjunto para totais anuais;
- não soma tabelas auxiliares, itens, fornecedores ou vínculos como se fossem registros adicionais do conjunto principal;
- não atribui linhas sem referência temporal ao ano corrente.

## Privacidade

Arquivos grandes são baixados temporariamente no runner. Os brutos não são versionados pelo projeto. Os resumos públicos não mantêm amostras de CPF/CNPJ, nomes de credores, favorecidos, fornecedores ou participantes. A presença de colunas sensíveis pode ser registrada apenas no esquema.

## Evidência

Para cada recurso processado são preservados:

- URL oficial;
- ID do recurso CKAN;
- data de atualização publicada;
- tamanho obtido;
- SHA-256 do arquivo baixado;
- esquema detectado;
- cobertura e eventual erro de coleta.

Falha, timeout, mudança de esquema ou ausência de campo nunca é convertida automaticamente em `0 registros` ou `R$ 0`.
