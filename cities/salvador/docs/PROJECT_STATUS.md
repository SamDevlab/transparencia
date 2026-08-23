# Status do projeto — Salvador/BA

Data de referência desta revisão: **23/08/2026**

## Estado atual

**STATUS: OPERACIONAL, COM COBERTURA DECLARADA POR FONTE E DEPLOY FUNCIONAL.**

A engenharia principal está implementada: coletores, preservação de evidência, cobertura explícita, reconciliação determinística, banco reconstruível, frontend derivado, testes e workflows. Isso não significa que todas as fontes externas estejam completas em todos os períodos.

Este arquivo é a referência humana de status. Para uma execução específica, prevalecem os `coverage.json`, `summary.json` e relatórios versionados no snapshot correspondente.

## O que está consolidado

- **Prefeitura — finanças:** coleta oficial preservando receita e os estágios da despesa sem tratar empenho, liquidação e pagamento como equivalentes.
- **Prefeitura — aquisições:** paginação oficial com controles de contagem e cobertura do filtro consultado.
- **Prefeitura — contratos:** grade municipal individualizada coletada separadamente; timeout ou intervalo incompleto permanece `partial`.
- **Câmara — empenhos:** navegação ScriptCase real com comparação entre identificadores visíveis e registros normalizados antes de declarar completude.
- **Câmara — fontes auxiliares:** viagens, documentos e certames possuem cobertura própria e não são promovidos silenciosamente a outra categoria contábil.
- **PNCP:** fonte complementar para contratações, contratos e CNPJ estruturado; nunca substitui a grade municipal quando sua cobertura é menor.
- **Reconciliação:** relações entre município e PNCP usam identificadores exatos normalizados. Ambiguidade permanece explícita.
- **Privacidade:** a camada pública de fornecedores exige CNPJ empresarial estruturado; CPF individual não vira cadastro público de fornecedor.
- **Frontend/deploy:** build derivado e deploy Vercel da branch `city/salvador` estão funcionais, com freshness declarado por fonte.

## PNCP complementar — estado atual

O snapshot de **22/08/2026** registrou **41 contratos** para o CNPJ municipal configurado, mas sem descoberta completa de todas as entidades municipais.

Em **23/08/2026**, a coleta foi ampliada e a estratégia de contratos passou a consultar o período anual completo por CNPJ, reduzindo fortemente a quantidade de chamadas. O melhor snapshot canônico do dia atualmente registra:

- **25 CNPJs descobertos** nas contratações PNCP, mais o CNPJ municipal principal;
- **26 CNPJs fornecidos** ao coletor de contratos;
- **739 contratações municipais PNCP observadas** antes da interrupção da descoberta;
- **396 contratos PNCP** após o filtro municipal;
- **0 erros nas consultas de contratos**;
- `complete_for_supplied_agencies_and_filter=true` para os 26 CNPJs fornecidos;
- descoberta de órgãos ainda `partial`, pois o endpoint de contratações retornou HTTP 500 durante paginação profunda.

Portanto, **396 não é uma contagem municipal global comprovada**. É a contagem completa para o conjunto de 26 CNPJs conhecidos e consultados no período, enquanto a descoberta de todos os CNPJs municipais ainda não atingiu um fim normal da fonte.

O coletor foi endurecido para:

1. respeitar `Retry-After` e aplicar backoff em 429/5xx;
2. consultar contratos em janela anual por CNPJ;
3. dividir adaptativamente uma janela de descoberta que falhe por erro de servidor, reduzindo paginação profunda sem mudar o escopo;
4. reter CNPJs municipais já validados em novas tentativas;
5. repetir também falhas de transporte como `ReadTimeout`;
6. manter um relatório separado da última tentativa;
7. impedir que uma tentativa pior sobrescreva um snapshot canônico mais forte do mesmo dia.

A tentativa que sofreu `ReadTimeout` após essas mudanças foi corretamente rejeitada pelo gate anti-regressão: o snapshot de 26 CNPJs/396 contratos permaneceu canônico.

## Camada web e validação derivada

A camada web mantém a grade municipal de contratos como fonte primária e o PNCP como complemento. Um snapshot PNCP parcial não substitui silenciosamente dados melhores já publicados.

O workflow de validação derivada também passou a ser disparado por mudanças em `cities/salvador/data/snapshots/**/pncp_complementary/**`. O relatório final mais recente registrou `passed=true` e refletiu corretamente:

- **396 contratos PNCP complementares no snapshot atual**;
- **26 CNPJs** no conjunto consultado;
- **272 fornecedores empresariais públicos**, todos sujeitos à regra de CNPJ estruturado;
- **247 fornecedores empresariais provenientes da camada PNCP complementar**;
- freshness PNCP em **23/08/2026**.

## Correção de build/deploy

O deploy falhava porque `scripts/fix-municipal-freshness.mjs` reconstruía `meta.dataFreshness` depois do overlay PNCP e removia `pncpComplementary`. A validação final detectava a divergência e encerrava `npm run build`.

A correção passou a preservar freshness produzido por overlays anteriores. Builds e deploys posteriores voltaram ao estado `READY`.

## Cobertura e evidência

Snapshots ficam em:

```text
cities/salvador/data/snapshots/YYYY-MM-DD/
```

Resultados históricos validados continuam preservados; não se apagam respostas brutas apenas para “limpar” o repositório. A limpeza documental remove duplicação e informação obsoleta, mas mantém rastreabilidade e evidência.

Estados de cobertura usados pelo projeto:

- `complete_for_filter` / `complete=true`: a própria fonte e o filtro consultado chegaram a um fim comprovado;
- `partial` / `complete=false`: há registros válidos, porém a fonte ou a execução não permite provar cobertura total;
- `unavailable`: a tentativa falhou sem cobertura suficiente;
- `not_run`: a etapa foi desabilitada explicitamente.

## Próxima prioridade

A pendência PNCP restante é **completar a descoberta dos CNPJs municipais**, não repetir os contratos já fechados para o conjunto conhecido. Novas execuções devem tentar alcançar o fim normal de todas as modalidades/janelas da descoberta, preservando o melhor snapshot quando a fonte falhar.

Enquanto a descoberta permanecer parcial:

1. manter a grade municipal de contratos como fonte primária;
2. tratar os 396 contratos PNCP como completos somente para os 26 CNPJs fornecidos;
3. manter o PNCP como complemento com cobertura explicitamente declarada;
4. revisar vínculos `aquisição municipal ↔ contrato municipal/PNCP` somente por identificadores exatos;
5. consolidar métricas públicas de fornecedores apenas com CNPJ empresarial estruturado.

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

O projeto pode estar operacional mesmo quando uma fonte está parcial. O que não é aceitável é transformar falta de evidência em completude, inferir pagamentos a partir de contratos, inferir identidade por similaridade ou esconder falhas de coleta.
