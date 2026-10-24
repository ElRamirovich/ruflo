# FreeLLMAPI: adaptador opcional para o Ruflo

Este adaptador usa a rota Anthropic já existente no Ruflo:
`ANTHROPIC_BASE_URL` recebe a **origem** do gateway e o Ruflo acrescenta
`/v1/messages`; `ANTHROPIC_AUTH_TOKEN` envia a chave unificada como Bearer.
Não é necessário acrescentar um provider ao núcleo nem alterar configurações
permanentes do Ruflo.

Requer somente Python 3.10+ para o adaptador. O gateway FreeLLMAPI e o executável
escolhido precisam estar disponíveis separadamente. O gateway e suas credenciais
**precisam ser configurados e verificados**. O launcher não instala nem inicia o
servidor; o utilitário separado de preparação é descrito abaixo. Nada depende de
uma instalação no computador pessoal: pode
ser usado no Codespaces ou em outro ambiente de desenvolvimento.

O adaptador não muda o modelo desta conversa. Uma futura ponte MCP configurada
separadamente poderia expor um auxiliar ao chat; essa ponte não está ativa por
causa destes arquivos.

## Diagnóstico sem rede e sem inferência

Na raiz do projeto:

```bash
python3 tools/freellmapi/launcher.py
python3 tools/freellmapi/launcher.py --dry-run -- node bin/cli.js --version
```

O primeiro é o comportamento padrão. Mesmo com chaves no ambiente, ambos apenas
mostram presença de chave, origem validada e situação da trava de lançamento.
Não imprimem chaves, argumentos do comando, arquivos de configuração ou corpos de
respostas. Não carregam `.env`, não gravam credenciais e não fazem inferência.

## Preparação opcional do gateway no Codespaces

O utilitário `setup_gateway.py` usa a imagem oficial do FreeLLMAPI fixada pelo
digest SHA-256 registrado no código. Ela precisa já estar presente no Docker;
o utilitário não baixa nem atualiza imagens automaticamente.

```bash
python3 tools/freellmapi/setup_gateway.py
python3 tools/freellmapi/setup_gateway.py --start
python3 tools/freellmapi/launcher.py --probe
```

O primeiro comando somente informa a preparação local. `--start` é uma ação
explícita: cria uma chave de criptografia privada em `~/.config/ruflo-freellmapi`
(diretório 700 e arquivo 600), um volume Docker próprio e o container
`ruflo-freellmapi`. A porta fica em `127.0.0.1:3001`; o processo usa o usuário
`node`, sem capabilities nem acesso ao socket Docker. Há limites de CPU/memória.
O container não reinicia automaticamente. Containers ou volumes de dados
preexistentes bloqueiam a preparação para evitar a troca acidental da chave de
criptografia. Dados/configurações anteriores não são apagados.

O servidor continua exigindo a configuração administrativa e dos provedores
gratuitos. Nenhuma chave de modelo é adicionada e nenhuma chamada de inferência
é iniciada pelo utilitário. Um servidor iniciado ainda pode levar alguns segundos
para responder ao healthcheck. Não imprima os logs de setup nem chaves no chat.
O diretório/volume privados não fazem parte do backup de código do projeto.
O bind de Docker não controla o encaminhamento de portas do Codespaces: confirme
que a porta 3001 está privada antes da configuração administrativa. A preparação
não altera visibilidade, não cria túneis públicos e não verifica essa configuração.

Variáveis deste adaptador:

| Variável | Uso |
| --- | --- |
| `FREELLM_BASE_URL` | Origem do gateway; padrão `http://127.0.0.1:3001` |
| `FREELLM_API_KEY` | Chave unificada emitida pelo gateway; fornecer como segredo do ambiente |
| `FREELLM_FREE_ONLY_CONFIRMED` | Deve ser exatamente `1` antes de permitir um comando filho |

`FREELLM_API_KEY` é o nome escolhido por **este adaptador**; ferramentas do projeto
upstream também documentam `FREELLMAPI_API_KEY`, que não é importada automaticamente.
Configure o segredo pelo ambiente/Codespaces Secrets. Não passe uma chave como
argumento de linha de comando, não cole valores no chat e não versione um `.env`.

A origem pode ser sobrescrita com `--base-url`. Ela deve conter somente esquema,
host e porta, sem `/v1`, usuário/senha, query ou fragmento. Hosts que não sejam
loopback exigem HTTPS.

## Verificar somente a saúde de um gateway local

```bash
python3 tools/freellmapi/launcher.py --probe
```

Esse modo explícito faz apenas um `GET /api/ping` em loopback. Não usa a chave,
proxies do ambiente, redirecionamentos ou endpoints de modelo; só informa status
HTTP e conectividade, sem ler/imprimir o corpo. Um ping bem-sucedido não confirma
credenciais, modelos disponíveis, funcionamento da inferência ou custo zero.
Uma origem remota não pode ser sondada por este adaptador.

## Comando filho com ambiente temporário

Depois de configurar e verificar no gateway uma cadeia **somente gratuita**, e
fornecer a chave por um segredo do ambiente:

```bash
FREELLM_FREE_ONLY_CONFIRMED=1 python3 tools/freellmapi/launcher.py -- node bin/cli.js --version
```

Esse exemplo apenas consulta a versão. Substitua o comando depois de `--` somente
quando quiser executar uma tarefa explícita com seu cliente instalado. Os
argumentos são passados diretamente ao processo filho, sem expansão por shell.
A presença da chave e a confirmação de gratuidade são exigidas antes de iniciar
qualquer filho. `--dry-run` continua offline e não inicia o comando.

No ambiente **do filho**, o adaptador:

- seleciona `RUFLO_PROVIDER=anthropic`;
- define a origem do gateway em `ANTHROPIC_BASE_URL`;
- injeta a chave unificada em `ANTHROPIC_AUTH_TOKEN`, nunca em argumentos;
- remove a chave Anthropic conflitante, chaves dos outros providers e seletores
  de provedores de nuvem conflitantes;
- mantém o ambiente do processo pai sem alterações e não grava configurações.

O adaptador executa uma única vez e devolve o código de saída do filho. Não tenta
um provider pago, não reinicia o comando com outra chave e não instala pacotes.
O comando filho controla sua própria saída; não peça a ele para imprimir segredos.

**A confirmação é uma declaração sobre a configuração do gateway, não uma
verificação de faturamento.** Free tiers dependem de disponibilidade, conta,
limites e políticas dos fornecedores. A trava não configura nem audita a cadeia
de fallback do servidor. Mantenha apenas rotas gratuitas habilitadas nele e não
habilite fallback pago. Este launcher também não é um sandbox: um comando filho
que sobrescreva provider, endpoint ou credenciais em seu próprio código,
argumentos ou configurações pode sair dessa rota. Revise esses overrides antes
de executar uma tarefa com inferência.

## Testes isolados

```bash
python3 -m unittest discover -s tools/freellmapi -p 'test_*.py' -v
```

Os testes simulam rede e subprocessos. Exercitam validação de URL, probe local
sem corpo/chaves, diagnóstico offline, trava de custo, isolamento do ambiente,
falhas sem fallback, privacidade e passagem de argumentos sem shell. Não iniciam
o gateway e não chamam provedores externos.

A implementação segue o contrato dos documentos upstream
`docs/en/api/01-rest-api.md` (Anthropic/Claude clients) e
`docs/en/clients/01-agent-clients.md` (server root versus `/v1`).
