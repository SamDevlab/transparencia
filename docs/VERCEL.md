# Publicação do frontend na Vercel

O frontend Next.js fica na **raiz do repositório** para conseguir ler tanto `cities/salvador/data/` quanto `regions/bahia/data/` durante a construção.

## Configuração

1. Importe `SamDevlab/transparencia` na Vercel.
2. Mantenha o diretório raiz na raiz do repositório.
3. Tecnologia da aplicação: **Next.js**.
4. Instalação: automática (`npm install`).
5. Construção: automática (`npm run build`).
6. Saída: padrão do Next.js (`.next`).
7. Não é necessária variável de ambiente.
8. Em **Settings → Environments → Production → Branch Tracking**, use `city/salvador` como branch de produção.

## Construção dos dados

O `package.json` executa:

```text
prebuild -> node scripts/build-web-data.mjs && node scripts/build-economy-web-data.mjs
build    -> next build
```

A primeira etapa seleciona o snapshot auditado mais recente de Salvador. A segunda seleciona o snapshot econômico mais recente da Bahia/Salvador. Se ainda não houver snapshot econômico válido, `economy.json` é gerado com `available=false` e o site continua compilando sem transformar ausência em zero.

Arquivos derivados principais:

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
public/data/economy.json
public/data/transparency.json
public/data/meta.json
```

Eles são derivados dos dados versionados e podem ser reconstruídos; não são fonte primária.

## Atualização econômica

`.github/workflows/economic-intelligence.yml` roda mensalmente e também pode ser executado manualmente. Ele:

- testa o coletor do Comex Stat;
- descobre a última competência oficial disponível;
- consulta Bahia e Salvador para o ano atual e o mesmo período do ano anterior;
- preserva requisição/resposta com SHA-256;
- gera resumo, produtos, países, série mensal, triagem produtiva e cobertura;
- versiona o snapshot em `regions/bahia/data/snapshots/`.

O commit do snapshot dispara nova construção do frontend porque `.github/workflows/web-build.yml` observa `regions/bahia/**`.

## Rotas econômicas

- `/economia` — visão geral;
- `/economia/bahia` — comércio exterior estadual;
- `/economia/salvador` — empresas domiciliadas em Salvador;
- `/economia/oportunidades` — triagem produtiva explicável;
- `/transparencia` — situação e limitações de todas as fontes.

## Validação

```bash
npm install
npm run build
npm run dev
```

O fluxo `.github/workflows/web-build.yml` exige todos os conjuntos do frontend, verifica a base pública já existente e valida a estrutura de `economy.json` e `transparency.json`. A disponibilidade econômica é tratada separadamente: a construção pode passar com `economy.available=false` quando a fonte externa ainda não produziu um snapshot válido.

## Segurança de interpretação

- empenhado, liquidado e pago permanecem separados;
- credor agregado não vira pagamento individual;
- falha de fonte não vira zero;
- relações Prefeitura ↔ PNCP usam referência exata de processo;
- déficit comercial, concentração e nota produtiva são indicadores descritivos;
- comércio exterior de Salvador é rotulado como comércio de empresas domiciliadas no município;
- dependência de outros estados não é inferida do Comex Stat.
