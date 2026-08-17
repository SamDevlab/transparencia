# Deploy do frontend na Vercel

O frontend Next.js fica na **raiz do repositório**. Ele foi estruturado assim para que o passo `prebuild` possa ler os snapshots versionados em `cities/salvador/data/` e gerar arquivos compactos em `public/data/` antes do `next build`.

## Deploy pelo painel da Vercel

1. Abra a Vercel e escolha **Add New → Project**.
2. Importe o repositório `SamDevlab/transparencia`.
3. Mantenha **Root Directory** vazio / na raiz do repositório.
4. Framework Preset: **Next.js**.
5. Install Command: deixe automático (`npm install`).
6. Build Command: deixe automático (`npm run build`).
7. Output Directory: deixe automático (`.next`).
8. Não é necessária nenhuma variável de ambiente para a versão atual.
9. Crie/conecte o projeto. Como o GitHub usa `main` como branch padrão, a Vercel poderá assumir `main` como produção inicialmente; o frontend de Salvador está em outra branch.
10. No projeto, abra **Settings → Environments → Production → Branch Tracking** e altere a Production Branch para `city/salvador`. Salve.
11. Abra **Deployments → Create Deployment**, informe a branch `city/salvador` e crie o deployment. Depois disso, novos pushes nessa branch poderão gerar deployments de produção automaticamente.

> Não altere o Root Directory para `cities/salvador`: o frontend está na raiz e o `prebuild` precisa acessar os snapshots dentro dessa pasta.

## O que acontece no build

O `package.json` usa o lifecycle padrão do npm:

```text
prebuild -> node scripts/build-web-data.mjs
build    -> next build
```

O gerador lê os dados auditados do Git e cria, apenas durante o build:

```text
public/data/dashboard.json
public/data/acquisitions.json
public/data/finance.json
public/data/camara.json
public/data/meta.json
```

`public/data/` está no `.gitignore`: estes arquivos são derivados e podem ser reconstruídos a qualquer momento a partir dos snapshots versionados.

## Atualização dos dados

Quando os coletores atualizarem e versionarem um novo snapshot, o frontend precisa apontar para a nova data em `scripts/build-web-data.mjs`. A intenção é, numa próxima evolução, resolver automaticamente o snapshot válido mais recente; nesta publicação inicial a data é deliberadamente fixa em `2026-08-17` para não trocar silenciosamente uma base auditada por outra ainda não validada.

## Validação local

```bash
npm install
npm run build
npm run dev
```

O workflow `.github/workflows/web-build.yml` executa o mesmo `npm run build` no GitHub Actions e verifica se os datasets foram gerados corretamente.

## Segurança de interpretação

O deploy do frontend não muda as regras do projeto:

- empenhado, liquidado e pago permanecem separados;
- credor agregado não é exibido como pagamento individual;
- timeout não vira zero registros;
- dispensa, inexigibilidade, valor alto ou concentração não são classificados automaticamente como irregularidade;
- toda página de exploração mantém links para as fontes públicas.
