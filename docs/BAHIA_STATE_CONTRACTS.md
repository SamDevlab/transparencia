# Contratos estaduais da Bahia

Esta camada usa o conjunto oficial **Contratos** publicado pela SEFAZ/AGE no Portal de Dados Abertos da Bahia, com origem declarada no FIPLAN.

## Regras de publicação

1. O arquivo bruto grande é temporário e não é versionado no Git.
2. O SHA-256, tamanho, URL, recurso CKAN e data de atualização ficam preservados.
3. A contagem anual vem somente da tabela principal identificada por esquema e por um identificador oficial de contrato/instrumento.
4. Aditivos, apostilamentos e tabelas relacionadas não são contados como novos contratos.
5. O valor mostrado conserva o nome do campo detectado na fonte. Ele não é reinterpretado como empenhado, liquidado ou pago.
6. CNPJ empresarial pode aparecer em agregações de fornecedores. CPF e documentos com 11 dígitos não são republicados nesta camada.
7. Valor alto, recorrência e concentração são sinais descritivos para consulta e não evidência de irregularidade.

## Regra de identidade

Vínculos entre fontes só podem usar identificadores oficiais. A normalização permitida remove pontuação e espaços e padroniza letras maiúsculas. Exemplo: `001/2026` e `001-2026` podem compartilhar a chave normalizada `0012026` quando representam o mesmo campo oficial.

Não são permitidos vínculos por similaridade de nome, objeto, fornecedor, órgão ou valor.

## Cadeia pretendida

Quando as chaves existirem nos dois lados, a plataforma poderá construir:

`órgão → processo/licitação → contrato/instrumento → fornecedor → empenho → liquidação → pagamento`

Cada aresta deve registrar qual identificador produziu o vínculo e de qual fonte ele veio.

## Diferenças financeiras

A base de contratos não substitui a base de despesas nem a base de pagamentos. Da mesma forma:

- valor contratual ≠ empenho;
- empenho ≠ liquidação;
- liquidação ≠ pagamento;
- `VAL_PAGO` da visão de despesas não é automaticamente igual ao `Valor do Pagamento` da base específica de pagamentos.

Reconciliações futuras devem ser feitas por chaves oficiais e manter eventuais diferenças visíveis.
