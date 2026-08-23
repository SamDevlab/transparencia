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
- **Frontend/deploy:** o build derivado voltou a passar e o deploy Vercel da branch `city/salvador` está funcional após correção do modelo de freshness por fonte.

## PNCP complementar — estado atual

O snapshot de **22/08/2026** registrou **41 contratos** para o CNPJ municipal configurado, mas sem descoberta completa de todas as entidades municipais.

A execução ampliada de **23/08/2026** descobriu **18 CNPJs em contratações PNCP**, além do CNPJ municipal principal, totalizando **19 CNPJs consultados**. A execução permaneceu corretamente marcada como `partial`:

- contratações municipais PNCP observadas: **249**;
- descoberta de órgãos: **incompleta**, interrompida por HTTP 500 da fonte;
- contratos observados na execução ampliada: **22**;
- consultas de contratos com erro: **133**, majoritariamente por HTTP 429 e alguns HTTP 500;
- cobertura municipal completa: **não declarada**.

O coletor e o workflow foram endurecidos em 23/08/2026 para reduzir pressão sobre a API: pacing entre requisições, respeito a `Retry-After`, mais tentativas e cadência menor no workflow.

A camada web também foi corrigida para que um snapshot PNCP parcial **não substitua silenciosamente** um conjunto publicado anterior. O snapshot parcial continua visível como evidência e freshness, mas promoção de novas linhas exige que as consultas do conjunto fornecido terminem normalmente.

## Correção de build/deploy

O deploy falhava porque `scripts/fix-municipal-freshness.mjs` reconstruía `meta.dataFreshness` depois do overlay PNCP e removia `pncpComplementary`. A validação final detectava a divergência e encerrava `npm run build`.

A correção passou a preservar freshness produzido por overlays anteriores. O workflow de validação da camada derivada registrou `passed=true` para o commit corrigido, com `latest_source_as_of=2026-08-23`, e os deploys posteriores voltaram ao estado `READY`.

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

A principal pendência técnica interna foi resolvida. A pendência atual depende da estabilidade do PNCP: novas execuções devem tentar completar a descoberta e as consultas dos 19 CNPJs sem transformar HTTP 429/500 em ausência de dados.

Enquanto o PNCP permanecer parcial:

1. manter a grade municipal de contratos como fonte primária;
2. manter o PNCP apenas como complemento explicitamente parcial;
3. revisar vínculos `aquisição municipal ↔ contrato municipal/PNCP` somente por identificadores exatos;
4. consolidar métricas públicas de fornecedores apenas com CNPJ empresarial estruturado;
5. promover novas linhas PNCP apenas quando os gates de cobertura e privacidade passarem.

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
