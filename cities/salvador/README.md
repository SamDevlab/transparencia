# Salvador/BA

Implantação de referência do framework `transparencia` para auditoria de dados públicos municipais.

O projeto não é um detector de corrupção. Ele coleta, preserva, normaliza, reconcilia e torna pesquisáveis fatos publicados por fontes oficiais. Valor alto, concentração, dispensa ou inexigibilidade são sinais descritivos para investigação documental, nunca conclusão de irregularidade.

## Estado do projeto

**Status técnico: COMPLETO.**

O pipeline de produção, os coletores, o manifesto de cobertura, a reconciliação, o banco reconstruível, os testes e a documentação estão implementados. “Completo” nunca significa “todos os fatos existentes na cidade”: cada conjunto de dados tem cobertura limitada à fonte, filtro e período que conseguimos provar.

Referências de estado:

```text
cities/salvador/docs/PROJECT_STATUS.md
cities/salvador/data/final/2026-08-17/FINAL_STATUS.json
cities/salvador/data/validation/final_validation.json
```

A validação final registrada em 17/08/2026 passou com **33 testes**, `compileall`, CLI de produção e teste ao vivo da CMS com **10 empenhos visíveis / 10 normalizados / 0 faltantes / 0 extras**.

Cobertura consolidada:

| Conjunto | Fonte | Estado comprovado |
|---|---|---|
| Receita e execução da despesa do Executivo | Portal da Transparência de Salvador | Coleta oficial do período, com respostas brutas e SHA-256 |
| Aquisições/licitações 01/01–17/08/2026 | API oficial do Portal | **2.306/2.306 registros; 231/231 páginas; completo para o filtro** |
| Despesa por credor | API oficial do Portal | 5.554 agregados de credor; não são pagamentos individualizados |
| Execução contratual agregada | API oficial do Portal | Coletada por unidade gestora |
| Grade municipal de contratos individualizados | API oficial do Portal | Coletor adaptativo implementado; timeout/falha de intervalo permanece `partial`, nunca zero inventado |
| Contratações e contratos PNCP | PNCP | Fonte complementar; cobertura limitada às consultas/CNPJs comprovados em cada run |
| Câmara – composição | CMS | Cadastro oficial preservado; exercício em data específica exige atos de licença/posse quando aplicável |
| Câmara – empenhos | Sistema financeiro público da CMS | Paginação ScriptCase real implementada; `complete` exige exaustão da fonte + 100% dos identificadores visíveis normalizados |
| Câmara – viagens/documentos/certames | CMS | Coletados separadamente, cada um com cobertura própria |

Um snapshot antigo de empenhos da CMS foi explicitamente invalidado após a descoberta de subcaptura do parser; o arquivo normalizado antigo foi removido e os snapshots brutos foram mantidos como evidência. O projeto prefere retirar uma reivindicação de completude a preservar um resultado enganoso.

## Fontes principais

- Portal da Transparência: https://transparencia.salvador.ba.gov.br/
- API usada pelo frontend oficial: https://apitmptransparencia.salvador.ba.gov.br/api
- Portal de Compras: https://compras.salvador.ba.gov.br/
- Câmara Municipal: https://www.cms.ba.gov.br/
- PNCP: https://pncp.gov.br/
- Transparência Brasil: https://www.transparencia.org.br/

O catálogo auditável está em `sources.csv`. Seeds mantêm `source_url` e data de observação. Evidências documentais relevantes ficam em `data/evidence/` com SHA-256 no manifesto.

## Pipeline de produção

```bash
python -m pip install -e '.[dev]'
pytest -q

transparencia --repo-root . --city salvador collect-salvador \
  --start 2026-01-01 \
  --end 2026-08-17 \
  --out cities/salvador/data/snapshots/2026-08-17/production
```

O comando produz, conforme a disponibilidade de cada fonte:

```text
project_report.json
project_coverage.json
prefeitura_finance/
prefeitura_acquisitions/
prefeitura_contracts/
cms_commitments/
cms_auxiliary/
pncp_executivo/
pncp_legislativo/
pncp_contracts_executivo/
pncp_contracts_legislativo/
reconciliation/
salvador.db   # derivado; reconstruível e não precisa ser versionado
```

O workflow `.github/workflows/salvador-production.yml` executa testes antes/depois da coleta e versiona os snapshots source-linked, mantendo o SQLite como artefato derivado.

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
10. Falha, timeout ou rate limit da fonte nunca é convertido em zero registros.
11. Valor alto, concentração de fornecedor, dispensa ou inexigibilidade não provam ilícito. Qualquer alegação de irregularidade exige documentação primária e, quando aplicável, conclusão de órgão competente.

## Semântica de cobertura

- `complete_for_filter`: contagem/paginação da **própria fonte e filtro** fechou.
- `partial`: os registros coletados são válidos, mas a fonte interrompeu, limitou ou ainda não permite provar a cobertura total daquele filtro.
- `unavailable`: a tentativa do run falhou e nenhum status de completude é reivindicado.
- `not_run`: a etapa foi explicitamente desabilitada naquele run.

Esses estados impedem que indisponibilidade técnica seja silenciosamente transformada em “base completa”.
