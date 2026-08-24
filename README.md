# Transparência Municipal

Framework aberto e replicável para coletar, preservar e analisar **receitas, despesas, agentes públicos, atividade legislativa, licitações e contratos** de municípios brasileiros com rastreabilidade até a fonte.

## Estrutura por branch

- `main`: engine genérica, sem dados ou integrações de uma cidade específica.
- `city/<slug>`: configuração, fontes, evidências, coletores específicos e camada de publicação daquele município.

A primeira implantação é Salvador/BA na branch `city/salvador`.

## Garantias do núcleo

O core aplica regras que não podem ser enfraquecidas por um adaptador municipal:

- **Sem fonte, sem fato.** Evidência bruta e proveniência são preservadas.
- **Completude é por fonte e filtro.** `complete_for_filter` não significa completude universal.
- **Identidades exatas.** Relações entre sistemas usam identificadores oficiais após normalização apenas de formatação; sem fuzzy matching por nome, objeto ou fornecedor.
- **Contabilidade sem colapsar etapas.** Empenho, liquidação e pagamento permanecem campos distintos.
- **Privacidade empresarial.** Diretório público de fornecedores usa CNPJ empresarial estruturado; CPF não é promovido para essa camada.
- **Histórico conservador.** Mudanças só são calculadas entre snapshots completos, comparáveis e ligados pela mesma identidade oficial.

O contrato completo de um adaptador está em [`docs/city-adapter.md`](docs/city-adapter.md).

## Objetivos

- responder quanto um município arrecada e gasta;
- ligar despesas a órgão, favorecido, contrato e licitação quando a fonte permite;
- acompanhar Legislativo sem confundir gasto institucional com gasto individual;
- reconciliar contratações municipais com fontes complementares quando houver identificadores oficiais;
- preservar evidência bruta e SHA-256;
- tornar cada afirmação reproduzível e citável;
- comparar snapshots ao longo do tempo sem inventar continuidade documental.

## Criando uma nova cidade

```bash
cp -R cities/_template cities/minha-cidade
# edite city.json e sources.csv
python -m transparencia --city minha-cidade sources
```

Para uma implantação oficial, crie uma branch `city/minha-cidade` a partir de `main`. O adaptador deve traduzir campos específicos da fonte para o esquema canônico do core, mantendo detalhes de endpoint e paginação fora da engine genérica.

## PNCP

```bash
python -m transparencia --city minha-cidade collect-pncp \
  --start 2026-01-01 --end 2026-01-31 --scope executivo
```

O coletor usa UF e código IBGE da configuração da cidade, descobre modalidades ativas no domínio oficial do PNCP e preserva os snapshots consultados. O PNCP é uma fonte separada: sua completude nunca torna automaticamente completa uma fonte municipal.

## Banco local

```bash
python -m transparencia --city minha-cidade build-db
```

O SQLite gerado contém `city_slug` em todas as tabelas factuais para impedir mistura silenciosa entre municípios.

## Regra editorial

**Sem fonte, sem fato.** Dados derivados precisam manter ligação explícita com a origem e não podem aumentar artificialmente a precisão do documento publicado.
