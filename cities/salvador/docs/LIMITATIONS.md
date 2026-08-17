# Limitações conhecidas

1. **Portal atual de Salvador é uma aplicação JavaScript.** A página inicial não expõe o conteúdo completo em HTML simples; o coletor precisa ser adaptado às chamadas de rede/API observadas no navegador ou aos downloads oficiais disponibilizados.
2. **Portal legado usa formulários ASP.NET.** A página descreve os campos e resultados, mas consultas interativas podem exigir POST com estado (`__VIEWSTATE` etc.). Nesta primeira versão preservamos a página e tratamos a automação completa como etapa específica de engenharia reversa documentada.
3. **PNCP não é sinônimo de 100% do histórico municipal.** Ele é essencial para a Lei 14.133/2021 e a consulta é pública, mas a completude depende do envio correto pelos órgãos/entidades; deve ser reconciliado com o Portal de Compras e Diário Oficial.
4. **CNPJ matriz não basta.** O Município de Salvador usa CNPJ 13.927.801/0001-49 em vários contextos, mas fundos/entidades podem possuir identificadores próprios. O coletor PNCP filtra por município/esfera/poder, não apenas pelo CNPJ matriz.
5. **Gastos individuais de vereadores ainda não estão completos.** A prestação de contas da Câmara fornece totais e documentos mensais; só serão atribuídos a pessoas quando houver fonte nominal confiável.
6. **Notícias oficiais são evidência secundária dentro do próprio órgão.** São úteis para contexto e valores reportados, mas demonstrativos contábeis/leis têm precedência.
7. **Valores arredondados.** Notícias que usam “R$ 14,96 bilhões” são guardadas como arredondadas; não se convertem em precisão falsa.
8. **Instabilidade de fontes.** Sites públicos podem retornar 5xx/timeout. O manifesto registra coletas bem-sucedidas; falhas devem ser registradas no log e tentadas novamente sem apagar snapshots anteriores.
9. **Lista de vereadores e licenças.** A página geral da Câmara lista 43 nomes no snapshot, mas páginas biográficas podem registrar licenças/substituições (por exemplo, Beca informa retorno em 24/02/2025 devido à licença de Luiz Carlos). O snapshot nominal representa o que a página geral exibia; situação de exercício deve ser validada por atos de licença/posse antes de análises individuais.
