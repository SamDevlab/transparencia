# Status do projeto — Salvador/BA

Data de referência: **23/08/2026**

## Estado atual

**STATUS: OPERACIONAL, COM COBERTURA PRINCIPAL AUDITÁVEL E DEPLOY FUNCIONAL.**

A engenharia principal está implementada: coletores, evidência bruta, hashes/proveniência, cobertura explícita, reconciliação determinística, banco reconstruível, camada web, testes e workflows. Para uma execução específica, os `coverage.json`, `summary.json` e relatórios versionados prevalecem sobre este resumo humano.

## Cobertura consolidada

### Prefeitura de Salvador

- **Finanças:** receita e estágios da despesa permanecem separados; empenho, liquidação e pagamento não são tratados como equivalentes.
- **Aquisições:** **2.401** registros na camada derivada atual, com cobertura completa para o filtro publicado.
- **Contratos:** **4.807** linhas na fonte municipal atual e **3.199** linhas publicadas após normalização/gates, com cobertura completa para o filtro.
- A grade municipal continua sendo a fonte primária para contratos; contrato nunca é promovido a pagamento.

### PNCP complementar

Snapshot canônico de **23/08/2026**:

- **1.052 contratações municipais PNCP**;
- **25 CNPJs descobertos diretamente**, mais o CNPJ municipal principal;
- **26 CNPJs** no escopo contratual reconciliado;
- **396 contratos PNCP**;
- **0 erros** nas consultas de contratos;
- `agency_cnpj_discovery_complete=true`;
- `complete_for_discovered_municipal_agencies_and_filter=true`;
- `procurement_and_contract_scope_match=true`;
- reconciliação por conjunto exato de CNPJs, sem fuzzy matching.

A completude vale para o período/filtros declarados. O PNCP continua complementar e seus valores não são somados automaticamente à grade municipal.

### Câmara Municipal de Salvador

- **1.414 empenhos**: cobertura completa para a visão pública padrão.
- **159 viagens**: fonte auxiliar, com publicação pública apenas agregada.
- **1.994 documentos**: seções auxiliares coletadas com cobertura declarada por seção.
- **188 certames de 188 informados pelo servidor**: cobertura completa do catálogo observado em 23/08/2026.
- A paginação de certames percorreu **19 páginas**, alcançou a janela final **181–188**, terminou sem erro e só recebeu `complete=true` porque o número de linhas distintas coincidiu exatamente com o total declarado pela própria fonte.

O coletor de certames usa a sessão ScriptCase e o opcode oficial da própria interface (`nmgp_opcao=avanca`). Falha HTTP, sessão quebrada, parser incompleto ou divergência de contagem rebaixa a cobertura para `partial`; nunca vira zero.

## Reconciliação documental

A última validação derivada versionada antes da nova cadeia PNCP registrou:

- **904 de 2.401 processos** com pelo menos um contrato ligado por identificador oficial exato;
- **1.137 pares exatos** processo ↔ contrato;
- **1.078 pares municipais primários**;
- **59 pares PNCP complementares**, distribuídos por 55 processos.

A implementação atual também suporta uma segunda rota PNCP estritamente documental:

1. número oficial do processo municipal = `process_number` da contratação PNCP;
2. `numeroControlePNCP` da contratação = `numeroControlePncpCompra` do contrato PNCP.

Essa cadeia não usa objeto, fornecedor, órgão, valor, data ou similaridade textual. Os contratos encontrados pelos dois caminhos são deduplicados como observação, mas preservam os métodos de prova (`linkMethods`). Os números incrementais dessa nova rota só devem substituir o baseline acima após nova validação derivada versionada.

## Privacidade e interpretação

- Diretório público de fornecedores exige **CNPJ empresarial estruturado**; CPF individual não vira identidade pública de fornecedor.
- Relação aquisição → contrato é documental e não implica pagamento.
- Observações Prefeitura/PNCP permanecem fontes distintas e não são fundidas por semelhança.
- Sinais de concentração, mudança ou anomalia são evidência para revisão, não acusações automáticas.

## Resiliência e validação

PNCP usa retry/backoff, `Retry-After`, divisão adaptativa de janelas, retry de `ReadTimeout`, staging e promoção atômica com gate anti-regressão.

A validação derivada é acionada por mudanças relevantes de código e pelos snapshots de `pncp_complementary` e `cms_auxiliary`. Quando certames são marcados completos, o build exige simultaneamente:

1. `records == serverReportedTotal`;
2. `reachedServerEnd == true`.

Comandos principais:

```bash
python -m pip install -e '.[dev]'
pytest -q
npm run build
```

PNCP especificamente:

```bash
pytest -q tests/test_pncp.py tests/test_pncp_contracts.py
```

## Próximas prioridades

1. **Aumentar vínculos documentais exatos** somente onde existirem outros identificadores oficiais estruturados; nunca usar fuzzy matching para criar vínculo oficial.
2. **Evoluir análises públicas** de gastos, órgãos, fornecedores, séries históricas, comparação temporal e sinais auditáveis.
3. **Manter atualização contínua** com freshness por fonte, evidência bruta, coverage e gates anti-regressão.
4. **Expandir o modelo para outras cidades** sem misturar lógica específica de Salvador ao núcleo reutilizável.

## Critério de qualidade

O projeto pode estar operacional mesmo quando uma fonte futura estiver parcial. O que não é aceitável é transformar falta de evidência em completude, inferir pagamento a partir de contrato, inferir identidade/relação por similaridade, somar fontes sobrepostas sem prova ou esconder falhas de coleta.
