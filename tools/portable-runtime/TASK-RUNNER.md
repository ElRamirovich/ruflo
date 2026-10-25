# Integrador de tarefa limitada

task_runner.py conecta client.py a action_gate.py. Não depende de Ruflo,
FreeLLMAPI ou SDK de provedor. Requer Python 3.10+ e biblioteca padrão.

Diagnóstico padrão sem rede nem leitura de chave:

```bash
python3 tools/portable-runtime/task_runner.py --a 17 --b 25 --model modelo-local
```

Após revisar um servidor local, definir AGENT_LOCAL_PROCESSING_CONFIRMED=1
no ambiente e fornecer --request para obter e validar a proposta. --execute,
em conjunto com --request, permite somente a soma fixa validada. Sem --execute
o resultado é uma prévia. Chave opcional: AGENT_API_KEY no ambiente.
Não colocar credenciais na linha de comando ou no repositório.

O modelo recebe um esquema explícito com os operandos fornecidos pelo chamador.
O validador exige correspondência exata e rejeita qualquer outra ferramenta.
Há uma única tentativa, sem retry, fallback ou correção silenciosa da resposta.
Erros retornam saída 2 e task_rejected sem repetir chave ou resposta recebida.

O endpoint aceita apenas loopback conforme client.py. Um serviço em loopback
pode encaminhar solicitações à nuvem: a confirmação do operador não é sandbox
nem garantia contra cobranças. Timeout do cliente é por operação de socket,
15 segundos; usar supervisor externo para prazo total em implantação.
Não há daemon, execução de código gerado, memória persistente ou terminal.

## Verificação em 25/10/2026

25 testes passaram: os anteriores e cinco testes novos do integrador.
O teste de composição HTTP executa a CLI em subprocesso, passa por um servidor
local com respostas sintéticas e verifica soma válida e rejeição de shell.
Não comprova inferência real nesta rodada: pesos e arquivos temporários foram
removidos pela manutenção do ambiente. Componentes anteriores foram recuperados
do GitHub. Não foi ativado serviço pago nem enviado dado privado.

## Situação do projeto

| Parte | Evidência e pendência |
|---|---|
| Backup local | Criação/verificação/restauração previamente testadas; backup externo criptografado ainda pendente |
| Inferência independente | Demonstrada anteriormente com modelo local; qualidade geral não aprovada |
| Validação de ações | Esquema fechado para uma soma limitada |
| Integração cliente/ferramenta | Implementada e testada com HTTP sintético |
| Memória independente persistente | Pendente |
| Ferramentas úteis e coordenação | Capacidades existentes preservadas; substituição independente pendente |
| Hospedagem permanente e migração | Pendentes |

Este é um protótipo funcional do núcleo, não um substituto completo do agente.
Não há base para declarar percentual de conclusão ou segurança absoluta.
