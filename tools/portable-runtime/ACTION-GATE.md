# Primeira ferramenta limitada

action_gate.py recebe uma proposta textual não confiável e só aceita a operação
fixa add com inteiros entre -1.000.000 e 1.000.000. Os valores esperados vêm do
chamador confiável, separados da resposta do modelo. O modelo não escolhe suas
próprias permissões. A execução padrão apenas valida; --execute permite a soma.

```bash
printf '%s' '{"tool":"add","arguments":{"a":17,"b":25}}' |
  python3 tools/portable-runtime/action_gate.py --a 17 --b 25 --execute
```

O resultado é 42. Remover --execute produz somente a proposta validada.
O módulo aceita JSON puro ou exatamente um bloco Markdown marcado json;
rejeita texto adicional, blocos múltiplos, campos extras, chaves duplicadas,
booleanos usados como inteiros, floats, NaN, números fora do limite e argumentos
diferentes dos esperados. Entrada máxima de 4 KiB. Erros não repetem a entrada.

Esta ferramenta usa código fixo de adição. Não interpreta código gerado, não
abre arquivos do usuário, não executa comandos, não acessa rede e não carrega
plugins escolhidos pelo modelo. Importar o módulo não executa a CLI. A leitura
de stdin pode aguardar EOF; chamadores devem aplicar prazo ao subprocesso.

Não é sandbox para ferramentas futuras. Uma proposta estruturalmente válida
não autoriza operações externas. Novas ferramentas exigem permissões e testes
próprios. Nunca preencher --a/--b com valores extraídos da mesma proposta que
está sendo validada: isso removeria a verificação de intenção.

A suíte de 20 testes inclui seis novos testes de validação, execução explícita,
Markdown, injeções, tipos, limites e erro da CLI sem repetição de conteúdo.
Não há substituição de Ruflo, migração de memória ou ativação de serviço
permanente nesta mudança. Requer Python 3.10+ e biblioteca padrão.

## Ensaio real em 25/10/2026

Com o Qwen local e as versões identificadas em QWEN-EVALUATION.md, uma proposta
real retornou apenas um objeto com a=17 e b=25, dentro de Markdown, omitindo
tool e arguments. A validação rejeitou a resposta e não realizou a operação.
O caso levou 12,074 segundos. A chamada de chat de controle respondeu 42 em
2,460 segundos. O servidor foi encerrado. Nenhum código gerado foi executado,
nenhuma chave de provedor foi usada e nenhum serviço pago foi ativado.

Esse ensaio comprova rejeição de uma proposta real inválida. O sucesso da soma
válida foi verificado por testes determinísticos, não por decisão autônoma do
modelo. Não alterar os requisitos do esquema para acomodar silenciosamente
essa resposta incompleta.
