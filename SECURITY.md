# Security Policy

Transparência Municipal processa dados públicos e integra fontes externas. Mesmo sem armazenar credenciais de usuários finais, uma implantação pode manipular tokens de API, endpoints, evidência bruta e dados potencialmente sensíveis por contexto.

## Reporte

Não publique tokens, credenciais, dumps privados, documentos não públicos ou detalhes de infraestrutura sensíveis em issues públicas.

Para reporte privado, utilize o contato disponível no perfil do mantenedor e informe componente, reprodução, impacto e evidência sanitizada.

## Princípios de segurança

- segredos ficam em variáveis de ambiente e não no repositório;
- artefatos brutos coletados devem preservar proveniência sem promover dados pessoais desnecessários;
- entradas externas são tratadas como não confiáveis até validação/normalização;
- coletores devem ter limites de paginação/tempo e falhar de forma explícita;
- integridade de evidência pode ser registrada com SHA-256;
- identidades entre sistemas não devem ser inferidas de maneira agressiva;
- arquivos locais de banco e `.env` permanecem ignorados pelo Git.

## Dados pessoais

O fato de um dado estar disponível em fonte pública não implica que ele deva ser republicado indiscriminadamente. Contribuições devem preservar o princípio de minimização e o escopo editorial do projeto.

## Deploy

Uma implantação pública deve revisar autenticação de eventuais superfícies administrativas, rate limiting, cache/proxy de fontes externas, logs, retenção de evidências e proteção de credenciais de provedores.

## Licenciamento

Este arquivo não define licença de uso do código nem dos dados externos. Dados, documentos e APIs de terceiros continuam sujeitos aos respectivos termos e requisitos de atribuição.
