# Status do projeto — Salvador/BA

Data desta revisão: **24/08/2026**  
Dados públicos mais recentes usados nesta revisão: **21–23/08/2026**, conforme freshness de cada fonte.

## Estado atual

**STATUS: OPERACIONAL, COM COBERTURA PRINCIPAL AUDITÁVEL, RECONCILIAÇÃO DOCUMENTAL EXATA E DEPLOY FUNCIONAL.**

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

## Reconciliação documental — baseline validado

A auditoria rápida e a validação derivada completa passaram e concordam no mesmo baseline:

- **912 de 2.401 processos** com pelo menos um contrato ligado por identificadores oficiais exatos;
- **904 processos** já eram alcançados pelo vínculo direto por número oficial do processo;
- **8 processos adicionais** foram ligados exclusivamente pela cadeia documental PNCP;
- **1.152 pares exatos** processo ↔ contrato;
- **1.137 pares** já existiam no caminho direto;
- **15 pares líquidos adicionais** foram acrescentados pela cadeia PNCP;
- **1.078 pares municipais primários**;
- **74 pares PNCP complementares**;
- **1.131 observações contratuais únicas vinculadas**;
- **1.052 contratações PNCP** participaram do índice intermediário de controle oficial.

A segunda rota PNCP é estritamente documental:

1. número oficial do processo municipal = `process_number` da contratação PNCP;
2. `numeroControlePNCP` da contratação = `numeroControlePncpCompra` do contrato PNCP.

Essa cadeia não usa objeto, fornecedor, órgão, valor, data ou similaridade textual. Os contratos encontrados pelos dois caminhos são deduplicados como observação, mas preservam os métodos de prova (`linkMethods`).

A página `/analises` agora é reconstruída depois da reconciliação e deve permanecer sincronizada com `municipal-links.json`. O build falha se as contagens ou a regra documental da página divergirem do índice oficial derivado.

## Relação contrato → execução financeira

Foi executado um probe dedicado sobre endpoints oficiais de relação contratual:

- `/contratos/detalhamentoContrato`;
- `/contratos/empenhoRelacionado?pagina=1`;
- `/contratos/liquidacaoRelacionado?pagina=1`;
- `/contratos/pagamentoRelacionado?pagina=1`.

Nas amostras preservadas, os endpoints responderam **HTTP 500**. O estado publicado permanece:

- `can_build_exact_contract_finance_collector=false`;
- `commitment_relation_proven=false`;
- `liquidation_relation_proven=false`;
- `payment_relation_proven=false`;
- blocker: `official_contract_finance_endpoints_http_500`.

Portanto, o projeto **não** infere empenho, liquidação ou pagamento a partir do contrato enquanto a fonte oficial não fornecer uma relação estruturada acessível.

## Privacidade e interpretação

- Diretório público de fornecedores exige **CNPJ empresarial estruturado**; CPF individual não vira identidade pública de fornecedor.
- Relação aquisição → contrato é documental e não implica pagamento.
- Observações Prefeitura/PNCP permanecem fontes distintas e não são fundidas por semelhança.
- Sinais de concentração, mudança ou anomalia são evidência para revisão, não acusações automáticas.

## Análises públicas

A aplicação já possui camada de análise descritiva para:

- aquisições de valor elevado;
- contratações diretas;
- fornecedores repetidos;
- concentração por unidade;
- relações documentais exatas;
- histórico temporal de contratos quando existem snapshots comparáveis.

A interface deve sempre explicar o método documental de cada vínculo e não apresentar sinais estatísticos como prova de irregularidade.

## Resiliência e validação

PNCP usa retry/backoff, `Retry-After`, divisão adaptativa de janelas, retry de `ReadTimeout`, staging e promoção atômica com gate anti-regressão.

A validação derivada exige, entre outros gates:

1. contratos e aquisições completos para seus filtros declarados;
2. fornecedores públicos somente com CNPJ empresarial estruturado e evidência exata;
3. `analysis.json` sincronizado com `municipal-links.json`;
4. regra PNCP de dois saltos explicitamente publicada na análise;
5. certames completos somente quando `records == serverReportedTotal` e `reachedServerEnd == true`;
6. histórico contratual sem inventar eventos quando não existem dois snapshots comparáveis;
7. execução financeira contratual bloqueada quando os endpoints oficiais não comprovam relação.

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

1. **Manter a relação contrato → execução financeira bloqueada** até os endpoints oficiais deixarem de responder 500 ou surgir outra fonte estruturada oficial com identificador exato.
2. **Evoluir análises públicas e comparação temporal** somente a partir de snapshots comparáveis e métricas descritivas auditáveis.
3. **Manter atualização contínua** com freshness por fonte, evidência bruta, coverage e gates anti-regressão.
4. **Expandir o modelo para outras cidades** pelo núcleo reutilizável, sem mover lógica específica de Salvador para o core.

## Critério de qualidade

O projeto pode estar operacional mesmo quando uma fonte futura estiver parcial. O que não é aceitável é transformar falta de evidência em completude, inferir pagamento a partir de contrato, inferir identidade/relação por similaridade, somar fontes sobrepostas sem prova ou esconder falhas de coleta.
