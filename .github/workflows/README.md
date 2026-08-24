# Workflows — classificação operacional

Esta pasta contém tanto automações de produção quanto probes preservados durante a descoberta das fontes. A presença de um arquivo aqui **não** significa que ele seja parte do pipeline recorrente atual.

## Pipeline municipal ativo — Salvador

Use estes workflows como referência para manutenção da implantação atual:

- `salvador-finance-snapshot.yml` — receitas/despesas e agregados oficiais da Prefeitura;
- `salvador-acquisitions-snapshot.yml` — aquisições municipais;
- `salvador-municipal-contracts.yml` — grade detalhada de contratos municipais;
- `salvador-pncp-complementary.yml` — PNCP complementar e descoberta/reconciliação de órgãos;
- `salvador-cms-commitments-snapshot.yml` — ledger de empenhos da Câmara;
- `salvador-cms-auxiliary.yml` — viagens, documentos e certames da Câmara;
- `economic-intelligence.yml` — camada econômica;
- `web-build.yml` — build integral da publicação;
- `derived-web-build.yml` — validação das camadas derivadas;
- `salvador-derived-integrity-fast.yml` — integridade rápida de dados derivados;
- `final-validation.yml` — validações de fechamento quando aplicável.

## Pipeline estadual ativo — Bahia

- `bahia-state-transparency.yml`;
- `bahia-sefaz-finance.yml`;
- `bahia-sefaz-contracts.yml`;
- `bahia-sefaz-money-flow.yml`;
- `bahia-procurement-contract-links.yml`;
- `bahia-state-status.yml`.

## Diagnósticos e provas de fonte

Arquivos cujo nome contém `probe`, `context`, `lazy-chunks`, `endpoint`, `table-shape`, `pagination-discovery` ou equivalentes são **evidência técnica/diagnóstico**, não fonte primária da publicação. Eles são mantidos para auditabilidade e para reproduzir descobertas de endpoint.

Exemplo atual: `salvador-contract-finance-link-probe.yml` preserva a prova de disponibilidade dos endpoints oficiais `contrato → empenho/liquidação/pagamento`. Enquanto o backend oficial responder erro, nenhuma relação financeira individual é promovida.

## Legado preservado

`salvador-final-snapshot.yml`, `salvador-full-snapshot.yml` e outros workflows de fechamento/discovery de 2026-08-17 são preservados como histórico técnico. Novas funcionalidades **não devem depender** de datas globais ou artefatos antigos quando uma camada source-scoped atual existir.

## Regras para novos workflows

1. Coleta recorrente deve ter cobertura e data por fonte.
2. Timeout, HTTP 5xx, rate limit ou ausência de metadado não podem virar `0` ou `complete=true`.
3. Evidência raw deve ser preservada quando suportado.
4. Relações entre fontes exigem identificador oficial exato; fuzzy matching não cria vínculo.
5. Empenho, liquidação e pagamento permanecem etapas distintas.
6. Dados públicos de fornecedores ficam restritos a CNPJ empresarial estruturado; informações pessoais não devem ser republicadas em resumos públicos.
7. Probes devem gravar um resumo auditável e nunca promover dados automaticamente sem uma validação explícita.

## Antes de remover um workflow

Não apagar um probe apenas por parecer antigo. Primeiro verifique se ele é a única evidência reproduzível de uma descoberta. Se for obsoleto operacionalmente, prefira mantê-lo como histórico/manual ou registrar a substituição neste arquivo antes da remoção.
