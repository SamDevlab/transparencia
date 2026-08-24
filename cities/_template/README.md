# Adaptador de cidade

Copie este diretório para `cities/<slug>`, preencha `city.json`, catalogue somente fontes verificadas em `sources.csv` e mantenha dados específicos da cidade em `data/`.

Antes de implementar coletores, leia [`docs/city-adapter.md`](../../docs/city-adapter.md). O adaptador deve traduzir a fonte municipal para o esquema canônico do core sem enfraquecer as garantias de cobertura, identidade, contabilidade e privacidade.

## Checklist mínimo

- `city.json` identifica município, UF, código IBGE e, quando conhecido, CNPJ institucional.
- `sources.csv` contém apenas fontes oficiais ou explicitamente classificadas quanto ao papel.
- Cada coleta relevante produz cobertura por fonte/filtro.
- `complete_for_filter` só é usado após reconciliação com a própria fonte.
- Relações entre sistemas usam identificadores oficiais exatos; sem fuzzy matching.
- Empenho, liquidação e pagamento permanecem separados.
- Diretório público de fornecedores aceita somente CNPJ empresarial estruturado.
- Histórico só compara snapshots completos da mesma fonte e identidade.
- Evidência bruta fica preservada em `data/raw/` ou `data/snapshots/`.

Nunca altere o núcleo para acomodar uma cidade se a diferença puder ser expressa por configuração ou adaptador local. Se a regra for realmente comum a várias cidades, extraia-a para `src/transparencia/` com testes antes de reutilizá-la.
