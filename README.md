# Transparência Municipal + Inteligência Econômica

Framework aberto e replicável para coletar, preservar e consultar **receitas, despesas, licitações, contratos, atividade legislativa e indicadores econômicos** com rastreabilidade até a fonte.

Esta branch é a implantação de **Salvador/BA**, integrada à camada estadual da **Bahia** em `regions/bahia/`. O núcleo reutilizável permanece em `main`; novas cidades usam `city/<slug>`.

## Princípios

- **Sem fonte, sem fato.**
- Empenho, liquidação e pagamento permanecem etapas contábeis distintas.
- Relações entre bases exigem identificadores documentais exatos; similaridade de nome, objeto ou fornecedor nunca cria vínculo.
- Cobertura é declarada por **fonte e filtro**, não por uma data global artificial.
- Falha, timeout ou rate limit nunca vira valor zero nem alegação de completude.
- A camada pública de fornecedores é restrita a empresas com **CNPJ estruturado**; CPF e credor em texto livre não são republicados.
- Valor alto, concentração, dispensa ou inexigibilidade são sinais descritivos para consulta, não prova de irregularidade.

## Frontend

```bash
npm install
npm run build
npm run dev
```

O `prebuild` monta a publicação em camadas:

1. gera a base web a partir dos snapshots auditados;
2. promove finanças, aquisições e contratos municipais mais recentes quando cada fonte satisfaz seus próprios controles de cobertura;
3. aplica privacidade e reconciliações exatas;
4. gera o índice `aquisição → contrato` sem inferir pagamento;
5. integra Câmara, economia e transparência estadual da Bahia;
6. reconcilia a página pública de cobertura por fonte;
7. o `build` executa `validate-current-web-data.mjs` depois do Next.js e falha se as invariantes de cobertura, contabilidade ou privacidade forem violadas.

## Rotas principais

### Salvador

- `/buscar` — consulta geral;
- `/dinheiro` — totais contábeis e fio documental disponível;
- `/licitacoes` — aquisições municipais;
- `/processos/[id]` — processo/aquisição e contratos ligados por identificador exato;
- `/contratos` e `/contratos/[id]` — grade oficial municipal, perfis e PNCP complementar;
- `/relacoes` — índice explícito `processo/aquisição ↔ contrato`;
- `/financas` — receitas, estágios da despesa e agregados por função/credor;
- `/fornecedores` — somente fornecedores empresariais com CNPJ estruturado;
- `/orgaos`, `/agentes`, `/camara` — órgãos, agentes públicos e fontes institucionais do Legislativo;
- `/transparencia` — cobertura, datas e limitações por fonte.

### Bahia e economia

- `/bahia/transparencia` — transparência estadual;
- `/bahia/contratos` e `/bahia/contratos/[id]` — contratos e fio exato estadual;
- `/economia`, `/economia/bahia`, `/economia/salvador` — comércio exterior e indicadores;
- `/economia/oportunidades` — triagem produtiva explicável;
- `/metodologia` — regras editoriais e metodológicas.

## Fontes municipais atuais

A Prefeitura de Salvador é a fonte principal para finanças, aquisições e a grade detalhada de contratos. O PNCP é complementar: ajuda na reconciliação e pode fornecer CNPJ empresarial estruturado, mas não substitui silenciosamente a cobertura municipal.

A Câmara Municipal é tratada em fontes separadas:

- ledger público de **empenhos**, sem reclassificação como liquidação/pagamento;
- despesas de viagem publicadas apenas como agregado na camada web;
- catálogo de documentos de transparência;
- certames mantidos como parciais enquanto a paginação integral não estiver comprovada.

## Bahia

A camada estadual usa dados oficiais da SEFAZ/AGE e preserva o vínculo documental `licitação → contrato → pagamento` apenas quando o mesmo identificador oficial permite a ligação. Valor contratual e pagamento anual não são tratados como equivalentes.

## Inteligência econômica

O coletor `src/transparencia/collectors/comex.py` usa a API oficial do **MDIC / Comex Stat**. Exportações/importações municipais representam o domicílio fiscal da empresa declarante; isso não prova local físico de produção ou consumo.

O Índice de Triagem Produtiva é uma heurística para priorizar **estudo adicional**, não recomendação de investimento ou conclusão de viabilidade. Metodologia: [`docs/ECONOMIC_INTELLIGENCE.md`](docs/ECONOMIC_INTELLIGENCE.md).

## Evidência e atualização

Snapshots ficam em `cities/salvador/data/snapshots/YYYY-MM-DD/` e `regions/bahia/data/`. Coletores preservam resposta de origem e SHA-256 quando suportado. Workflows recorrentes atualizam cada fonte independentemente; `public/data/` é sempre derivado e reconstruível.

Validação principal:

```bash
pip install -e '.[dev]'
pytest -q
npm run build
```

## Nova cidade

```bash
cp -R cities/_template cities/minha-cidade
# edite city.json e sources.csv
python -m transparencia --city minha-cidade sources
```

Depois, crie `city/minha-cidade` a partir de `main` e mantenha as mesmas regras de cobertura, identidade documental e privacidade.
