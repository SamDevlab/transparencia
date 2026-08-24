# Contrato de adaptador de cidade

O núcleo do projeto não conhece portais, campos ou endpoints específicos de uma prefeitura. Cada cidade deve normalizar suas fontes para um conjunto pequeno de contratos comuns e preservar a evidência bruta separadamente.

## 1. Configuração

Cada cidade vive em `cities/<slug>/` e começa por `city.json` + `sources.csv`. O código genérico usa `CityConfig`/`CityWorkspace`; URLs, CNPJs institucionais e detalhes de coleta ficam no adaptador da cidade.

## 2. Cobertura por fonte e filtro

Toda coleta relevante deve produzir uma `CoverageEntry` ou artefato equivalente.

`complete_for_filter` só pode ser usado quando a fonte fornece metadados suficientes para reconciliar o escopo solicitado. Quando `reported_total`/`reported_pages` existem, o núcleo exige a reconciliação exata. Essa marca nunca significa “todos os dados públicos existentes sobre a cidade”.

Datas de atualização permanecem por fonte. Um `latest_source_as_of` pode resumir a fonte mais recente, mas não deve fazer fontes mais antigas parecerem atualizadas.

## 3. Identidades e relações

O adaptador deve mapear identificadores oficiais para o esquema canônico quando existirem:

- `process_number`
- `notice_number`
- `contract_number`
- `management_unit`
- `agency_document`
- `year`

A reconciliação do core remove apenas formatação/pontuação e compara igualdade. Nome de fornecedor, objeto, descrição ou similaridade semântica nunca criam um fato documental.

Se um identificador exato apontar para mais de um registro, o resultado é `multiple_candidates`, não uma escolha automática.

## 4. Contabilidade

Empenho (`committed`), liquidação (`liquidated`) e pagamento (`paid`) são estágios diferentes. Um adaptador não pode preencher um estágio usando o valor de outro.

Aquisição → contrato e contrato → execução financeira também são relações distintas. A primeira não prova a segunda.

## 5. Privacidade de fornecedores

O diretório público de fornecedores usa somente CNPJ empresarial estruturado de 14 dígitos. CPF e nomes de pessoas físicas podem permanecer na evidência necessária à auditoria, mas não entram automaticamente na camada pública.

Relações publicadas que enriquecem um registro com fornecedor devem carregar um método de evidência iniciado por `exact_`.

## 6. Histórico

Mudanças entre snapshots são produzidas apenas quando:

1. ambos os snapshots são `complete_for_filter`;
2. pertencem ao mesmo `source_system`;
3. o snapshot atual é posterior ao anterior;
4. cada registro possui a identidade oficial composta exigida pelo adaptador.

Registros com identidade ausente ou duplicada no mesmo snapshot são excluídos da comparação em vez de serem associados por aproximação.

## 7. Estrutura recomendada

```text
cities/<slug>/
├── city.json
├── sources.csv
├── README.md
└── data/
    ├── raw/
    ├── snapshots/YYYY-MM-DD/<source>/
    └── validation/
```

Coletores reutilizáveis ficam em `src/transparencia/collectors/`. Integrações que existem somente em uma cidade devem ter nome/escopo explícito e não alterar as garantias do core.

## 8. Critério para uma segunda cidade

Uma nova cidade valida a arquitetura quando consegue reutilizar o core acima e implementar apenas:

- descoberta das fontes oficiais;
- tradução dos campos da fonte para o esquema canônico;
- paginação/completude específica daquela fonte;
- regras documentais específicas quando a própria fonte fornece identificadores adicionais.

Se for necessário copiar lógica de Salvador para obter privacidade, completude, reconciliação ou histórico, essa lógica deve ser extraída para o core antes da cópia.
