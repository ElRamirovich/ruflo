# Integrações opcionais: avaliação e limites

Avaliação em 24/10/2026. Os componentes abaixo são ferramentas de desenvolvimento
independentes; o Ruflo não depende de instalações no computador pessoal.
Não confundir código preparado, serviço saudável e inferência comprovada.

## FreeLLMAPI

Fonte oficial: <https://github.com/tashfeenahmed/freellmapi>.
Fonte revisada: `26484157fd15f5fb66f54d3a86f568997ea304de`.

É um gateway para provedores configurados pelo operador, com cotas e credenciais
próprias. A compatibilidade Anthropic `/v1/messages` permite aproveitar o suporte
existente a `ANTHROPIC_BASE_URL` e `ANTHROPIC_AUTH_TOKEN` do Ruflo; não é necessário
alterar o provedor padrão do projeto nem adicionar uma dependência ao aplicativo.

`tools/freellmapi/launcher.py` oferece diagnóstico offline, um healthcheck local
opcional e execução com variáveis restritas ao processo filho. Credenciais ficam
no ambiente, nunca no Git ou nos argumentos. A confirmação de provedores gratuitos
é uma declaração operacional, não uma auditoria da conta de cobrança. O operador
deve manter apenas provedores gratuitos habilitados e revisar fallback e cotas.

O gateway deve ficar em loopback, com volume e chave de criptografia privados;
não usar o perfil de autoatualização com acesso ao socket Docker. O token unificado
e a conta administrativa são configurados separadamente. Um servidor saudável
sem credenciais não comprova que a IA está ajudando no projeto.

Uma conexão com esta conversa exigiria expor uma ferramenta MCP por uma conexão
autorizada. A documentação oficial descreve Secure MCP Tunnel; não foi criada
uma conexão nem houve troca do modelo da conversa:
<https://developers.openai.com/api/docs/guides/secure-mcp-tunnels>.

## claude-seo

Fonte oficial: <https://github.com/AgriciDaniel/claude-seo>.
Fonte revisada: `6be93f45064ffbadced572b5d5c95f55fd263af0`.

O plugin completo destina-se ao Claude Code. Seu instalador altera configurações
sob `~/.claude`, pode sobrescrever skills/agentes existentes e instala o conjunto
completo de dependências e Chromium. Não executar esse instalador sobre a
configuração atual do Ruflo. Preferir checkout fixado e ambiente Python separado.

Scripts determinísticos úteis, sem inferência: `fetch_page.py`, `parse_html.py`,
`sitemap_discovery.py`, `metadata_template.py`, `render_page.py` e
`pagespeed_check.py`. Extensões comerciais devem permanecer desligadas até
verificação de preço. Search Console exige credenciais do proprietário e
verificação de propriedade; um script não substitui essa verificação.

O pacote não resolve sozinho toda a lista de SEO: a extração de headings não
comprova a ordem H1–H6; extrair links não testa destinos quebrados; responsividade,
compressão de imagens e correções no código precisam de validação específica.
A URL de homologação/produção do site precisa ser definida antes da auditoria.

## Strix e Cloudflare

Fonte oficial: <https://github.com/usestrix/strix>.
Strix executa testes ativos com Docker e um modelo configurado. Fonte aberta não
garante inferência gratuita. Só executar contra o repositório/ambiente autorizado,
com escopo definido e dados de teste. Nenhum pentest ou agenda foi ativado.

A Cloudflare pode disparar um job por Cron Trigger. O executor do Strix precisa
de um ambiente compatível com seu Docker; um Worker comum pode coordenar a
execução, mas não substitui esse executor. Cloudflare Containers exige Workers
Paid e tem cobrança própria de recursos. Não provisionar esse serviço sem
aprovação de custo. A alternativa a avaliar é um runner externo com Docker e
agendamento do próprio CI, ou Cloudflare apenas como disparador autenticado.

Conexões precisam de permissões limitadas ao projeto. Não expor o scanner ou um
webhook de execução sem autenticação. Faltam: conexão Cloudflare, alvo de
homologação, periodicidade e verificação dos custos do modelo/executor. Nenhuma
automação foi registrada com uma conexão que ainda não existe.

Referências:
- <https://developers.cloudflare.com/workers/configuration/cron-triggers/>
- <https://developers.cloudflare.com/containers/platform/pricing/>
- <https://developers.cloudflare.com/agents/model-context-protocol/cloudflare/servers-for-cloudflare/>

## Reverse API Engineer

Fonte oficial: <https://github.com/kalil0321/reverse-api-engineer>.
Fonte revisada: `ab9919b652eca1c7b323c3f7c7b37ded3cef12a0`.

Captura tráfego HAR e usa um modelo para gerar clientes de API, incluindo
TypeScript. É útil para integrações web autorizadas e fluxos sem documentação;
para Drive, Gemini e Cloudflare, priorizar os contratos oficiais disponíveis.

Bloqueio concreto: `src/reverse_api/prompts/partials/_language_typescript.md`
orienta incluir cookies e tokens diretamente no código gerado. A captura HAR
também contém cabeçalhos e corpos, e pode ser lida por um modelo externo.
Não usar sessões reais nessa configuração. Antes de aplicar: sanitizar capturas,
usar contas de teste, substituir essa orientação por credenciais externas,
impedir commits de HAR/sessões e revisar o cliente gerado antes de executar.
Nenhum tráfego do usuário foi capturado ou enviado a esse projeto.

## Celular e Google ARTEMIS

Fonte oficial: <https://github.com/google/artemis>.
ARTEMIS automatiza Android por instruções em linguagem natural e usa ADB para
operar dispositivos/emuladores. Pode apoiar testes de apps; o envio de pedidos
pelo celular pode continuar pela conversa e pelo acesso autenticado ao projeto.
Nenhum aparelho foi pareado nem controlado nesta avaliação.

Se houver necessidade de controlar um Android: primeiro definir modelo/versão,
usar aparelho/perfil de testes, confirmar o pareamento no próprio telefone e
manter o acesso na rede privada. Não publicar ADB na internet. O Codespaces
precisará de conectividade privada até o dispositivo; um link github.dev não
fornece essa conectividade. Validar essa rota antes de habilitar automação.

TLS, VPN e MCP privado protegem trechos de comunicação, mas uma IA em nuvem
precisa receber conteúdo legível para processá-lo. Portanto esse caminho não
é uma promessa de criptografia ponta a ponta que exclua o provedor de IA.
Uma configuração totalmente local muda os endpoints de confiança e requer
recursos/modelo locais. Não criar um protocolo criptográfico próprio.

Referências de transporte e pareamento:
- <https://developer.android.com/tools/adb>
- <https://developers.openai.com/api/docs/guides/secure-mcp-tunnels>

## RTK CLI

Fonte oficial: <https://github.com/rtk-ai/rtk>.
RTK OSS 1.0.1 foi instalado no ambiente de trabalho do assistente a partir do
artefato oficial, com SHA-256 conferido contra o digest publicado pelo GitHub.
Usa-se explicitamente como prefixo de comandos de leitura, sem modificar hooks
globais, sem daemon de proxy de IA e sem colocar o projeto na dependência dele.

Em uma comparação local de `git log -5` numa cópia rasa contendo um commit,
a saída caiu de 496 para 384 bytes (22,6%), preservando o identificador do commit.
Essa é uma medição de bytes nesse comando, não uma garantia de redução de tokens,
custo ou latência de uma conversa. Para revisão de segurança, correções e falhas,
conservar a saída integral quando o resumo não trouxer a evidência necessária.
