# Deploy do frontend na Vercel

O frontend Next.js fica na **raiz do repositório**. Ele foi estruturado assim para que o passo `prebuild` possa ler os snapshots versionados em `cities/salvador/data/` e gerar arquivos compactos em `public/data/` antes do `next build`.

## Deploy pelo painel da Vercel

1. Abra a Vercel e escolha **Add New → Project**.
2. Importe o repositório `SamDevlab/transparencia`.
3. Em **Branch**, selecione `city/salvador` para o projeto de Salvador.
4. Mantenha **Root Directory** vazio / na raiz do repositório.
5. Framework Preset: **Next.js**.
6. Install Command: deixe automático (`npm install`).
7. Build Command: deixe automático (`npm run build`).
8. Output Directory: deixe automático (`.next`).
9. Não é necessária nenhuma variável de ambiente para a versão atual.
10. Clique em **Deploy**.

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
