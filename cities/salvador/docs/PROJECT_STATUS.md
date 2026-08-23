# Status do projeto — Salvador/BA

Data de referência desta revisão: **23/08/2026**

## Estado atual

**STATUS: OPERACIONAL, COM COBERTURA DECLARADA POR FONTE.**

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

## PNCP complementar — situação corrigida

O snapshot de **22/08/2026** comprovou uma coleta de contratos bem-sucedida para o CNPJ municipal configurado e registrou **41 contratos**, mas marcou corretamente `agency_cnpj_discovery_complete=false`. Portanto, aquele resultado é completo apenas para o conjunto de CNPJs fornecido ao coletor, não para todas as entidades municipais.

Em **23/08/2026**, o workflow `.github/workflows/salvador-pncp-complementary.yml` foi corrigido para:

1. coletar primeiro as contratações PNCP de Salvador com `scope=municipal`;
2. extrair os CNPJs dos órgãos encontrados por meio de `agency_cnpjs_from_procurements`;
3. adicionar o CNPJ municipal configurado como fallback/âncora;
4. consultar contratos para todo o conjunto descoberto;
5. declarar separadamente a completude da descoberta de órgãos e a completude das consultas de contratos.

A regra permanece conservadora: uma descoberta PNCP parcial pode fornecer contratos válidos, mas **não** autoriza afirmar cobertura municipal completa.

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

A prioridade imediata é validar a execução ampliada do PNCP e medir quantos CNPJs municipais são descobertos e quantos contratos adicionais aparecem em relação ao run limitado ao CNPJ principal.

Depois disso, a sequência recomendada é:

1. promover a evidência PNCP ampliada para a camada web somente se as invariantes de cobertura e privacidade passarem;
2. revisar os vínculos `aquisição municipal ↔ contrato municipal/PNCP` sem fuzzy matching;
3. consolidar métricas de fornecedores apenas onde houver CNPJ estruturado;
4. continuar reduzindo documentação duplicada, mantendo este arquivo como status canônico.

## Validação local

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
