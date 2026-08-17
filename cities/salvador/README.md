# Salvador/BA

Implantação de referência do framework `transparencia` para auditoria de dados públicos municipais.

O projeto não é um detector de corrupção. Ele coleta, preserva, normaliza, reconcilia e torna pesquisáveis fatos publicados por fontes oficiais. Valor alto, concentração, dispensa ou inexigibilidade são sinais descritivos para investigação documental, nunca conclusão de irregularidade.

## Estado do projeto

O **pipeline técnico está completo**: cada fonte configurada é tentada, cada saída tem proveniência e cada conjunto de dados recebe um status explícito em `project_coverage.json`. A palavra “completo” nunca é usada como sinônimo de “todos os fatos existentes na cidade”. Ela é sempre limitada à fonte, filtro e período que conseguimos provar.

Cobertura consolidada em 17/08/2026:

| Conjunto | Fonte | Estado comprovado |
|---|---|---|
| Receita e execução da despesa do Executivo | Portal da Transparência de Salvador | Coleta oficial do período, com respostas brutas e SHA-256 |
| Aquisições/licitações 01/01–17/08/2026 | API oficial do Portal | **2.306/2.306 registros; 231/231 páginas; completo para o filtro** |
| Despesa por credor | API oficial do Portal | 5.554 agregados de credor; não são pagamentos individualizados |
| Contratos por unidade gestora | API oficial do Portal | Agregados de execução coletados; grade individual depende da disponibilidade da rota detalhada |
| PNCP | Governo Federal | Fonte de reconciliação; cobertura é registrada como completa/parcial conforme o próprio run |
| Câmara – composição | CMS | Cadastro oficial preservado; exercício em data específica exige atos de licença/posse quando aplicável |
| Câmara – empenhos | Sistema financeiro público da CMS | Registros visíveis normalizados; paginação só será promovida a completa após prova técnica |
| Câmara – viagens/documentos/certames | CMS | Coletados separadamente, cada um com cobertura própria |

A matriz machine-readable do run de produção fica em:

```text
cities/salvador/data/snapshots/<DATA>/production/project_coverage.json
```

## Fontes principais

- Portal da Transparência: https://transparencia.salvador.ba.gov.br/
- API usada pelo frontend oficial: https://apitmptransparencia.salvador.ba.gov.br/api
- Portal de Compras: https://compras.salvador.ba.gov.br/
- Câmara Municipal: https://www.cms.ba.gov.br/
- PNCP: https://pncp.gov.br/
- Transparência Brasil: https://www.transparencia.org.br/

O catálogo completo e auditável está em `sources.csv`. Seeds mantêm `source_url` e data de observação. Evidências documentais relevantes ficam em `data/evidence/` com SHA-256 no manifesto.

## Pipeline de produção

```bash
python -m pip install -e '.[dev]'
pytest -q

transparencia --repo-root . --city salvador collect-salvador \
  --start 2026-01-01 \
  --end 2026-08-17 \
  --out cities/salvador/data/snapshots/2026-08-17/production
```

O comando produz, entre outros:

```text
project_report.json
project_coverage.json
prefeitura_finance/
prefeitura_acquisitions/
cms_commitments/
cms_auxiliary/
pncp_executivo/
pncp_legislativo/
reconciliation/
salvador.db   # derivado; pode ser reconstruído e não precisa ser versionado
```

Também existe o workflow `.github/workflows/salvador-production.yml`, que executa testes antes e depois da coleta e versiona o snapshot source-linked.

## Regras de integridade

1. **Sem fonte, sem fato.**
2. Fonte primária tem precedência; notícia oficial é apoio, não substituto da contabilidade quando o documento primário existe.
3. Respostas brutas são preservadas com SHA-256 sempre que o coletor oferece snapshot.
4. Dotação, empenho, liquidação e pagamento são estágios diferentes e nunca são somados ou renomeados como se fossem equivalentes.
5. Gasto institucional/agregado não é atribuído a vereador, secretário ou outra pessoa sem registro nominal.
6. Executivo e Legislativo permanecem separados.
7. Ausência em uma fonte não prova inexistência do fato.
8. Identidade de pessoa exige nome oficial exato ou alias documentado em fonte oficial; similaridade de nomes não basta.
9. Reconciliação PNCP × município usa identificadores normalizados exatos. Ambiguidade permanece `multiple_candidates`; não existe fuzzy match promovido a fato.
10. Valor alto, concentração de fornecedor, dispensa ou inexigibilidade não provam ilícito. Qualquer alegação de irregularidade exige documentação primária e, quando aplicável, conclusão de órgão competente.

## Semântica de cobertura

- `complete_for_filter`: contagem/paginação da **própria fonte e filtro** fechou.
- `partial`: os registros coletados são válidos, mas a fonte interrompeu, limitou ou ainda não permite provar a cobertura total daquele filtro.
- `unavailable`: a tentativa do run falhou e nenhum status de completude é reivindicado.
- `not_run`: a etapa foi explicitamente desabilitada naquele run.

Esses estados existem para impedir que indisponibilidade técnica seja silenciosamente transformada em “zero registros” ou “base completa”.
