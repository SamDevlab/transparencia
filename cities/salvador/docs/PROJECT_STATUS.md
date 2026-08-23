# Status do projeto — Salvador/BA

Data de referência desta revisão: **23/08/2026**

## Estado atual

**STATUS: OPERACIONAL, COM PNCP MUNICIPAL RECONCILIADO, COBERTURA DECLARADA POR FONTE E DEPLOY FUNCIONAL.**

A engenharia principal está implementada: coletores, preservação de evidência, cobertura explícita, reconciliação determinística, banco reconstruível, frontend derivado, testes e workflows. Com a reconciliação PNCP concluída para o período atual, a principal pendência de cobertura deixou de ser a descoberta de órgãos e passou a ser ampliar fontes ainda explicitamente parciais, principalmente certames da Câmara e vínculos documentais exatos.

Este arquivo é a referência humana de status. Para uma execução específica, prevalecem os `coverage.json`, `summary.json` e relatórios versionados no snapshot correspondente.

## O que está consolidado

- **Prefeitura — finanças:** coleta oficial preservando receita e os estágios da despesa sem tratar empenho, liquidação e pagamento como equivalentes.
- **Prefeitura — aquisições:** paginação oficial com controles de contagem e cobertura do filtro consultado.
- **Prefeitura — contratos:** grade municipal individualizada coletada separadamente; timeout ou intervalo incompleto permanece `partial`.
- **Câmara — empenhos:** navegação ScriptCase real com comparação entre identificadores visíveis e registros normalizados antes de declarar completude.
- **Câmara — fontes auxiliares:** viagens, documentos e certames possuem cobertura própria e não são promovidos silenciosamente a outra categoria contábil.
- **PNCP:** fonte complementar para contratações, contratos e CNPJ estruturado; nunca substitui a grade municipal como fonte primária.
- **Reconciliação PNCP:** descoberta municipal e escopo contratual atual foram reconciliados por conjunto exato de CNPJs, sem fuzzy matching.
- **Reconciliação documental:** relações aquisição ↔ contrato usam identificadores oficiais normalizados e exatos. Ambiguidade permanece explícita.
- **Privacidade:** a camada pública de fornecedores exige CNPJ empresarial estruturado; CPF individual não vira cadastro público de fornecedor.
- **Frontend/deploy:** build derivado e deploy Vercel da branch `city/salvador` estão funcionais, com freshness declarado por fonte.

## PNCP complementar — estado atual

O snapshot canônico de **23/08/2026** está reconciliado e registra:

- **1.052 contratações municipais PNCP** com `complete_for_municipal_filter=true`;
- **25 CNPJs descobertos diretamente** nas contratações, mais o CNPJ municipal principal configurado;
- **26 CNPJs** no escopo contratual reconciliado;
- **396 contratos PNCP** após o filtro municipal;
- **0 erros nas consultas de contratos**;
- `agency_cnpj_discovery_complete=true`;
- `complete_for_supplied_agencies_and_filter=true`;
- `complete_for_discovered_municipal_agencies_and_filter=true`;
- `procurement_and_contract_scope_match=true`;
- método de reconciliação `exact_cnpj_set_and_normalized_row_count_consistency`;
- nenhuma inferência fuzzy de identidade.

Portanto, para o período e filtros declarados no snapshot, a descoberta de CNPJs municipais chegou a um fim comprovado e o conjunto contratual corresponde exatamente ao escopo reconciliado. O PNCP continua sendo **fonte complementar**: essa completude não transforma contrato em pagamento, não substitui a grade municipal como fonte contábil primária e não autoriza somar valores de fontes sobrepostas.

O coletor permanece endurecido para:

1. respeitar `Retry-After` e aplicar backoff em 429/5xx;
2. consultar contratos em janela anual por CNPJ, reduzindo pressão de requisições;
3. dividir adaptativamente janelas de descoberta que falhem por erro de servidor;
4. repetir falhas de transporte como `ReadTimeout`;
5. coletar em staging isolado antes da promoção;
6. validar contagens, escopo e cobertura antes de promover o pacote;
7. preservar tentativas e evidência bruta;
8. impedir que uma execução pior ou inconsistente sobrescreva um snapshot canônico mais forte.

## Camada web e validação derivada

A camada web mantém a grade municipal de contratos como fonte primária e o PNCP como complemento. O overlay atual expõe o nível mais forte de completude apenas quando a descoberta está completa, os contratos estão completos para o conjunto descoberto e a reconciliação de CNPJs é exata.

A validação derivada mais recente passou (`passed=true`) e registra:

- **3.199 contratos municipais publicados** a partir de 4.807 linhas de fonte, com cobertura municipal declarada completa para o filtro;
- **2.401 aquisições municipais** com cobertura completa para o filtro;
- **396 contratos PNCP complementares**;
- **26 CNPJs** no escopo PNCP reconciliado;
- `agency_discovery_complete=true`;
- status PNCP `complete_for_discovered_municipal_agencies_and_filter`;
- **272 fornecedores empresariais públicos**, todos sujeitos à regra de CNPJ estruturado;
- **247 fornecedores empresariais provenientes da camada PNCP complementar**;
- **904 processos** com pelo menos um vínculo contratual exato;
- **1.137 pares exatos** aquisição/processo ↔ contrato;
- **1.078 pares municipais primários**;
- **59 pares PNCP complementares exatos**, distribuídos por 55 processos;
- freshness PNCP em **23/08/2026**.

Os vínculos entre fontes não usam similaridade textual. Contratos PNCP ligados ao mesmo processo são identificados como camada complementar e não são somados automaticamente aos valores da grade municipal.

## Câmara Municipal — estado atual

A camada atual registra:

- **1.414 empenhos** com cobertura completa para a visão pública padrão;
- **159 viagens** na fonte auxiliar, publicadas apenas em métricas agregadas;
- **1.994 documentos** nas seções auxiliares coletadas, com cobertura declarada por seção;
- **certames ainda `partial`**: apenas a página atualmente visível no servidor foi normalizada, com **10 registros visíveis** no relatório atual.

A ausência de um certame nessa lista não é interpretada como inexistência no catálogo da Câmara.

## Correções de build/deploy

A cadeia de build já foi corrigida para preservar `dataFreshness.pncpComplementary` depois dos overlays. O workflow de validação derivada também é disparado por mudanças em `cities/salvador/data/snapshots/**/pncp_complementary/**`.

Em 23/08/2026, o overlay PNCP foi atualizado para publicar o status `complete_for_discovered_municipal_agencies_and_filter` somente quando os três gates são verdadeiros:

1. descoberta de órgãos completa;
2. contratos completos para os órgãos descobertos;
3. escopo de CNPJs de contratações e contratos reconciliado exatamente.

O build derivado passou após essa alteração e o deploy correspondente no Vercel ficou `READY`.

## Cobertura e evidência

Snapshots ficam em:

```text
cities/salvador/data/snapshots/YYYY-MM-DD/
```

Resultados históricos validados continuam preservados; não se apagam respostas brutas apenas para “limpar” o repositório. A limpeza documental remove duplicação e informação obsoleta, mas mantém rastreabilidade e evidência.

Estados de cobertura usados pelo projeto:

- `complete_for_filter` / `complete=true`: a própria fonte e o filtro consultado chegaram a um fim comprovado;
- `complete_for_discovered_municipal_agencies_and_filter`: descoberta municipal concluída e contratos completos para o conjunto exato de CNPJs descobertos/reconciliados;
- `partial` / `complete=false`: há registros válidos, porém a fonte ou a execução não permite provar cobertura total;
- `unavailable`: a tentativa falhou sem cobertura suficiente;
- `not_run`: a etapa foi desabilitada explicitamente.

## Próximas prioridades

### 1. Ampliar certames da Câmara

A principal cobertura externa ainda explicitamente parcial é o catálogo de certames da Câmara. O próximo trabalho deve identificar a paginação/consulta real do servidor e coletar todas as páginas ou filtros comprovadamente acessíveis, mantendo `partial` caso a fonte não permita demonstrar o fim do catálogo.

### 2. Aumentar vínculos documentais exatos

Dos 2.401 processos de aquisição atuais, 904 possuem pelo menos um contrato ligado por identificador oficial exato. O objetivo é aumentar essa cobertura procurando outros identificadores oficiais estruturados disponíveis nas fontes, sem fuzzy matching e sem inferir relação por nome, objeto, fornecedor ou semelhança textual.

### 3. Evoluir análises públicas

Com a base principal estabilizada, evoluir os painéis de gastos, órgãos, fornecedores, séries históricas, comparação temporal e sinais de auditoria. Qualquer sinal de concentração, mudança ou anomalia deve ser apresentado como evidência para revisão, nunca como acusação automática.

### 4. Manter atualização contínua

Executar as coletas recorrentes preservando freshness por fonte, evidência bruta, hashes, coverage e gates anti-regressão. Uma fonte parcial em uma nova execução não deve rebaixar silenciosamente uma evidência histórica mais forte.

## Validação

```bash
python -m pip install -e '.[dev]'
pytest -q
npm run build
```

Para validar especificamente PNCP:

```bash
pytest -q tests/test_pncp.py tests/test_pncp_contracts.py
```

## Critério de qualidade

O projeto pode estar operacional mesmo quando uma fonte está parcial. O que não é aceitável é transformar falta de evidência em completude, inferir pagamentos a partir de contratos, inferir identidade por similaridade, somar fontes sobrepostas sem prova ou esconder falhas de coleta.
