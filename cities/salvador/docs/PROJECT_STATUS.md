# Status do projeto — Salvador/BA

Data de referência: **17/08/2026**

## Resultado

**STATUS TÉCNICO: COMPLETO**

O projeto possui pipeline de produção, manifesto de cobertura, coletores específicos por fonte, reconciliação exata, banco SQLite reconstruível, testes, workflows e documentação de limitações. “Completo” aqui significa que a engenharia necessária para coletar e representar honestamente as fontes está implementada; não significa que uma fonte pública indisponível passe a ser considerada completa.

O estado machine-readable está em:

```text
cities/salvador/data/final/2026-08-17/FINAL_STATUS.json
```

## Validação

A validação final versionada em `data/validation/final_validation.json` registrou:

- `pytest`: **33 passed**;
- `compileall`: **PASS**;
- CLI `collect-salvador`: **PASS**;
- teste ao vivo da primeira página do sistema de empenhos da CMS: HTTP 200, **10 identificadores visíveis, 10 normalizados, 0 faltantes, 0 extras**.

## Cobertura factual consolidada

### Prefeitura — finanças

O adaptador utiliza a API consumida pelo próprio Portal da Transparência. O snapshot de 01/01/2026 a 17/08/2026 preserva totalizadores e detalhamentos de receita, despesa por função/credor e execução contratual agregada, com proveniência e SHA-256.

Credor agregado **não** é tratado como pagamento individual. Empenhado, liquidado e pago permanecem estágios separados.

### Prefeitura — aquisições

A coleta de 01/01/2026 a 17/08/2026 fechou a paginação informada pela própria API:

- **2.306 registros recebidos / 2.306 reportados**;
- **231 páginas coletadas / 231 reportadas**;
- zero colisões da chave interna determinística;
- valor total reportado pela API: **R$ 3.566.352.927,80**.

Este é `complete_for_filter` da API municipal para aquele intervalo. Não é uma afirmação sobre qualquer outro sistema externo.

### Prefeitura — contratos individualizados

O frontend oficial confirma a grade `POST /contratos/gridDetalhada?pagina=N` e rotas de detalhe, aditivo, empenho, liquidação e pagamento. As sondas da grade detalhada apresentaram timeout; `GET /FiscaisContratos/downloadcsv` retornou HTTP 405.

O coletor `salvador_contracts.py` resolve isso sem falsificar dados: tenta a consulta oficial, subdivide o período quando necessário, preserva respostas bem-sucedidas e registra intervalos que falharam como `partial`. Timeout nunca vira “zero contratos”.

### PNCP — contratações e contratos

O PNCP permanece fonte complementar de reconciliação. Contratações são filtradas por município, esfera e poder; contratos são consultados para CNPJs de órgãos descobertos nas próprias contratações, além do CNPJ configurado quando aplicável.

Um run de contratos só pode receber `complete_for_filter` se as consultas dos CNPJs fornecidos fecharem normalmente **e** a descoberta upstream usada para formar o conjunto de CNPJs também estiver comprovadamente completa. Isso evita declarar uma lista de fornecedores completa a partir de um conjunto incompleto de órgãos.

### Câmara — empenhos

A paginação real do ScriptCase foi comprovada: a aplicação mantém sessão e navega pelo formulário F3 com `nmgp_opcao=avanca`. O projeto não usa `?page=N` como substituto inventado.

O coletor atual:

1. preserva cada resposta bruta com SHA-256;
2. conta todos os números de empenho visíveis em cada página;
3. normaliza cada empenho em bloco independente;
4. compara visíveis × normalizados;
5. navega até a própria aplicação atingir o fim/repetição;
6. só marca `complete=true` se **a fonte foi exaurida e não houve lacuna de parsing**.

Um snapshot antigo que havia sido marcado como completo foi posteriormente identificado como subnormalizado. A reivindicação foi retirada, o arquivo normalizado antigo foi removido e os HTMLs brutos foram mantidos como evidência. Isso é comportamento intencional do projeto: erro descoberto corrige a cobertura em vez de ser escondido.

Os empenhos emitidos pelo coletor entram no modelo reutilizável como `stage=commitment`. Eles não são convertidos em pagamento.

## Identidade política

O vínculo entre credor e vereador exige:

- nome oficial exato após normalização; ou
- alias explicitamente documentado por fonte oficial.

Similaridade de nome não cria vínculo. O caso `Carlos da Silva Muniz → Carlos Muniz` possui alias documentado; outros nomes permanecem sem match quando a evidência não basta.

Na camada normalizada, CPF individual é mascarado. CNPJ de fornecedor é preservado.

## Reconciliação

A reconciliação municipal × PNCP usa identificadores exatos normalizados, como processo/aviso/ano/CNPJ quando disponíveis. O sistema retorna:

- `exact_match`;
- `multiple_candidates`;
- `unmatched`.

Não existe fuzzy matching de objeto, fornecedor ou pessoa promovido automaticamente a fato.

## Definição operacional de “concluído”

O projeto é considerado tecnicamente concluído porque:

- há um comando único de produção;
- todas as fontes configuradas geram estado de cobertura explícito;
- falha externa é representada, não escondida;
- aquisições municipais possuem verificação de contagem/paginação;
- finanças preservam estágio contábil;
- contratos têm fontes municipal e PNCP separadas;
- Câmara possui navegação ScriptCase real e gate de parser;
- identidades possuem regra probatória;
- há banco SQLite reconstruível;
- há reconciliação determinística;
- há testes e validação ao vivo;
- limitações conhecidas estão documentadas.

## Execução

```bash
python -m pip install -e '.[dev]'
pytest -q

transparencia --repo-root . --city salvador collect-salvador \
  --start 2026-01-01 \
  --end 2026-08-17 \
  --out cities/salvador/data/snapshots/2026-08-17/production
```

Cada run gera `project_report.json` e `project_coverage.json`. Estes dois arquivos — e não a ausência/presença de uma pasta isolada — são a referência para determinar o que a fonte comprovou naquele run.
