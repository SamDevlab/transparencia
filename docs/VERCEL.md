# Publicação do frontend na Vercel

O frontend Next.js fica na **raiz do repositório**. Assim, o passo anterior à construção pode ler os dados versionados em `cities/salvador/data/` e gerar os arquivos compactos usados pelo site.

## Publicação pelo painel da Vercel

1. Na Vercel, crie um projeto a partir de `SamDevlab/transparencia`.
2. Mantenha o diretório raiz na raiz do repositório.
3. Selecione **Next.js** como tecnologia da aplicação.
4. Deixe a instalação automática (`npm install`).
5. Deixe a construção automática (`npm run build`).
6. Deixe a saída padrão do Next.js (`.next`).
7. A versão atual não exige variável de ambiente.
8. Em **Settings → Environments → Production → Branch Tracking**, configure `city/salvador` como branch de produção.
9. Crie a primeira publicação dessa branch. Depois disso, novos envios para `city/salvador` podem gerar novas versões de produção automaticamente.

> Não configure `cities/salvador` como diretório raiz. O frontend está na raiz e precisa acessar os dados dentro dessa pasta.

## Como os dados do site são gerados

O `package.json` executa:

```text
prebuild -> node scripts/build-web-data.mjs
build    -> next build
```

O gerador procura automaticamente o **snapshot auditado mais recente**. Uma pasta com data só pode ser escolhida quando contém, ao mesmo tempo:

- resumo financeiro municipal;
- resumo das aquisições municipais;
- `FINAL_STATUS.json` da mesma data.

Isso impede que uma coleta nova, ainda sem validação final, substitua silenciosamente a publicação anterior.

A construção gera arquivos derivados em `public/data/`, entre eles:

```text
public/data/dashboard.json
public/data/acquisitions.json
public/data/processes.json
public/data/contracts.json
public/data/suppliers.json
public/data/agencies.json
public/data/finance.json
public/data/camara.json
public/data/agents.json
public/data/analysis.json
public/data/money.json
public/data/comparisons.json
public/data/search.json
public/data/meta.json
```

Esses arquivos não são fonte primária e não precisam ser versionados: podem ser reconstruídos a partir dos snapshots e seeds auditados do repositório.

## Principais rotas públicas

- `/` — ponto de partida por pergunta;
- `/buscar` — busca geral por pessoa, empresa, CNPJ, processo, contrato, órgão, credor ou receita;
- `/dinheiro` — navegação do agregado para relações documentadas;
- `/licitacoes` — aquisições municipais com filtros e referências copiáveis;
- `/processos/[id]` — perfil de processo/aquisição e linha do tempo;
- `/contratos` — totais municipais + contratos individualizados preservados do PNCP;
- `/fornecedores` e `/fornecedores/[id]` — diretório e perfis de fornecedores;
- `/orgaos` e `/orgaos/[id]` — diretório e perfis de órgãos;
- `/agentes` e `/agentes/[id]` — agentes públicos e perfis individuais;
- `/comparar` — comparação entre órgãos no mesmo recorte;
- `/analises` — pontos descritivos para orientar leitura documental;
- `/metodologia` — regras de interpretação e cobertura.

## Validação

Para testar localmente:

```bash
npm install
npm run build
npm run dev
```

O fluxo `.github/workflows/web-build.yml` executa a mesma construção no GitHub Actions e verifica os conjuntos de dados, o número de aquisições, perfis, contratos, fornecedores, órgãos e índice de busca antes de registrar uma construção bem-sucedida.

## Segurança de interpretação

A publicação não muda as regras do projeto:

- empenhado, liquidado e pago permanecem separados;
- valor contratual não é renomeado como pagamento;
- credor agregado não vira pagamento individual;
- falha da fonte não vira zero;
- relações Prefeitura ↔ PNCP usam referência exata de processo, não aproximação textual;
- repetição de fornecedor, concentração, dispensa, inexigibilidade ou valor elevado são sinais descritivos para consulta, não conclusões de irregularidade;
- páginas de perfil mantêm acesso às fontes públicas utilizadas.
