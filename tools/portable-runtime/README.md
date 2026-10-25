# Cliente portátil opcional

Primeiro componente executável para desacoplar a chamada de chat de Ruflo,
FreeLLMAPI, Codespaces e SDKs de provedor. Python 3.10+ e biblioteca padrão.
Nenhum desses programas precisa estar instalado para executar o diagnóstico
ou os testes. A inferência exige um servidor compatível já instalado e um
modelo disponível; o script não instala ou baixa modelos.

Este módulo não substitui coordenação, memória, ferramentas ou agentes do
projeto. Essas capacidades permanecem na base existente. Não altera o modelo
usado nesta conversa e não transforma armazenamento do Drive em RAM.

## Diagnóstico offline

Na raiz do repositório:

```bash
python3 tools/portable-runtime/client.py --model modelo-local
python3 -m unittest discover -s tools/portable-runtime -p 'test_*.py' -v
```

O diagnóstico não lê stdin, arquivos, .env, chave de API ou conta de nuvem;
não instala dependências, inicia serviços nem realiza chamadas de rede.
Nenhum servidor ou modelo é considerado saudável apenas por esse resultado.

## Chamada explícita após revisão do servidor

O contrato aceito é POST /v1/chat/completions, resposta JSON não streaming,
choices[0].message.content textual, com max_tokens=256. Nem todo servidor ou
modelo suporta esse contrato/parâmetro. Não há negociação de capacidades,
fallback, execução de ferramentas ou novas tentativas.

O endpoint padrão é http://127.0.0.1:11434/v1. --base-url aceita apenas origens
HTTP/HTTPS em IP literal 127.0.0.1 ou ::1, com caminho exato /v1. localhost,
URLs com credenciais, query, fragmentos e destinos externos são rejeitados.
O transporte ignora proxies do ambiente, não segue redirecionamentos e
valida certificados HTTPS normalmente.

Para chamar o servidor é necessário --request, um modelo explícito e
AGENT_LOCAL_PROCESSING_CONFIRMED=1 no ambiente. O prompt vem de stdin, no
máximo 8 KiB UTF-8. Uma chave opcional vem exclusivamente de AGENT_API_KEY;
não é lida de .env nem aceita como argumento. Não colocar senhas em comandos
ou histórico do terminal. A resposta é limitada a 64 KiB, timeout de socket
15 segundos por operação (não um prazo total), retornada em JSON no stdout. Erros retornam 2 sem imprimir
corpo do servidor, chave, prompt ou exceções brutas.

**A confirmação é uma declaração do operador, não uma sandbox.** Um servidor
local pode encaminhar dados para nuvem e consumir cotas ou dinheiro. Antes
de chamar, revisar os modelos, as rotas e a cobrança do servidor. Tokens
do cliente não limitam o que o servidor pode fazer. Este cliente não fornece
criptografia ponta a ponta contra o administrador da máquina, nem garante
ausência de custos ou de processamento externo. Não usar dados privados no
ensaio inicial. Uma inferência real com prompt sintético foi executada; veja LIVE-INFERENCE.md. O modelo pequeno falhou na avaliação de qualidade e não foi promovido a agente.

## Evidência e limites

Quatorze testes verificam o cliente, integração HTTP real com servidor sintético e
rejeição/encerramento do ensaio de inferência. O smoke de inferência é separado
e não é iniciado pela suíte de testes.

Veja [LIVE-INFERENCE.md](LIVE-INFERENCE.md) para as versões, hashes, comando,
resultado real e limitações. O cliente funciona sem Ruflo e FreeLLMAPI; a
coordenação, memória e ferramentas do agente continuam na implementação existente.
Não há hospedagem permanente, migração concluída ou independência integral.
