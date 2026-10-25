# Segundo modelo local: Qwen 1.5B

Em 25/10/2026 foi avaliado o modelo oficial Qwen/Qwen2.5-1.5B-Instruct-GGUF,
revisão 91cad51170dc346986eccefdc2dd33a9da36ead9, quantização Q4_K_M,
licença Apache-2.0. O arquivo de 1.117.320.736 bytes foi comparado ao SHA-256
publicado pelo distribuidor:
`6a1a2eb6d15622bf3c96857206351ba97e1af16c30d7a74ee38970e434e9407e`.

O runtime é o llama.cpp b11871 já identificado em LIVE-INFERENCE.md.
Execução temporária em CPU, duas threads, contexto 1024, um slot, loopback,
modo offline e sem interface web. Limites do servidor: 4 GiB de espaço virtual,
300 segundos de CPU. Quatro chamadas com temperatura zero e máximo 64 tokens;
a quinta usa o client.py existente, seus parâmetros padrão e prazo externo de
25 segundos. Nenhuma chave de provedor ou informação pessoal foi utilizada.
Não foram ativados serviços pagos. Downloads exigiram rede; não houve sandbox
de egress que comprove isolamento absoluto. O servidor foi encerrado ao final.

## Resultados da repetição com validadores revisados

| Caso | Resultado | Tempo |
|---|---|---|
| Soma 17 + 25 | 42, aprovado | 1,962 s |
| JSON puro com ok=true | Markdown envolvendo JSON, reprovado no formato | 6,164 s |
| Função Python em uma linha, sem Markdown | Função correta visualmente, mas com Markdown e múltiplas linhas; reprovado no formato | 6,438 s |
| Instrução em português | pronto, aprovado | 1,846 s |
| Chamada pelo cliente independente existente | 42, aprovado | 1,559 s |

Saídas completas e identidade do avaliador constam em QWEN-EVALUATION.json.
O código produzido pelo modelo não foi executado. A análise de sintaxe não
substitui uma sandbox. A primeira rodada teve os mesmos resultados de aprovação;
a segunda corrigiu a precisão dos validadores e registrou o texto dos erros.

Os erros de JSON e Python são de contrato/formatação neste conjunto, não prova
de incapacidade geral de programação. Uma futura camada pode aceitar um único
bloco Markdown e validar seu conteúdo; isso exige testes próprios e não deve
converter qualquer texto em comando executável. Nenhuma adaptação desse tipo
foi ativada aqui.

## Estado de aprovação

Chat local independente de API paga: demonstrado com este modelo e ambiente.
Execução autônoma de ferramentas: não aprovada. Três acertos em cinco casos
sintéticos não demonstram confiabilidade geral nem segurança de um agente.
Os 14 testes anteriores do cliente passaram novamente.

O risco a resolver antes de promover este candidato é interpretar saídas do
modelo como ações. Manter propostas separadas de execução, validar esquemas,
restringir ferramentas e testar falhas antes de conceder acesso a arquivos ou
credenciais reais. Ruflo continua preservado. Memória, coordenação, hospedagem
contínua, restauração criptografada externa e migração completa permanecem
pendentes; nenhum desses itens é comprovado pela inferência local.
