# Salvador/BA

Implantação de referência do framework `transparencia` para coleta e consulta auditável de dados públicos municipais.

O projeto **não é um detector de corrupção**. Ele preserva fatos publicados por fontes oficiais, explicita a cobertura de cada coleta e só cria relações quando há identificadores documentais suficientes.

## Onde ver o estado atual

O status canônico da implantação fica em:

- [`docs/PROJECT_STATUS.md`](docs/PROJECT_STATUS.md) — estado atual, cobertura comprovada, limitações e próximo passo;
- [`sources.csv`](sources.csv) — catálogo das fontes;
- [`data/snapshots/`](data/snapshots/) — evidências e resultados versionados por data;
- [`data/validation/`](data/validation/) — validações versionadas.

Evite copiar números de cobertura para outros documentos: contagens mudam conforme as fontes são atualizadas. O `PROJECT_STATUS.md` deve ser a referência humana e os arquivos de `coverage.json`/`summary.json` dos snapshots são a referência machine-readable de cada execução.

## Fontes principais

- Portal da Transparência de Salvador e API usada pelo frontend oficial;
- Portal de Compras de Salvador;
- Câmara Municipal de Salvador;
- PNCP, como fonte complementar;
- Transparência Brasil, quando aplicável à pesquisa/documentação.

## Regras que não podem ser relaxadas

1. **Sem fonte, sem fato.**
2. Empenho, liquidação e pagamento são estágios distintos.
3. Falha, timeout ou rate limit nunca vira zero nem alegação de completude.
4. A cobertura é declarada por fonte, filtro e período.
5. Reconciliação entre bases exige identificadores documentais exatos; similaridade não vira vínculo factual.
6. CPF e credor individual em texto livre não são republicados como cadastro público de fornecedor.
7. Valor alto, concentração, dispensa ou inexigibilidade são sinais descritivos, não prova de irregularidade.

## Execução

```bash
python -m pip install -e '.[dev]'
pytest -q

transparencia --repo-root . --city salvador collect-salvador \
  --start 2026-01-01 \
  --end YYYY-MM-DD \
  --out cities/salvador/data/snapshots/YYYY-MM-DD/production
```

O pipeline mantém Prefeitura, Câmara e PNCP em camadas separadas. O SQLite e `public/data/` são derivados e reconstruíveis; a evidência bruta/source-linked permanece nos snapshots.
