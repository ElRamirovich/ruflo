# Execução com recibo local experimental

recorded_task.run_recorded(memory, task_id, a, b, model, **options) conecta o
task_runner à TaskMemory. O chamador confiável abre/fecha o banco e fornece
os operandos e ID; o modelo não recebe acesso ao banco.

Use exclusivamente dados sintéticos, diretório privado confiável e um único
escritor. A memória continua sem criptografia. Não há CLI nova, upload,
instalação, daemon ou migração de dados. Os modos padrão continuam offline.

O fluxo rejeita ID já registrado antes de chamar o modelo. Diagnóstico e prévia
não gravam recibos. Propostas rejeitadas não são executadas nem registradas.
Depois da soma validada, salva um recibo. Uma falha de gravação retorna
executed=true, memory_saved=false, memory_status=write_failed_no_retry,
preservando o resultado da soma sem repetir a execução ou imprimir exceções.
O chamador deve tratar esse estado explicitamente; não reenviar automaticamente.

Isso NÃO fornece execução exatamente uma vez: há uma janela entre a execução
e o commit. Uma queda nessa janela pode deixar a tarefa sem recibo; escritores
concorrentes também podem passar pela checagem inicial. Nenhuma ferramenta com
efeitos externos deve usar esse mecanismo como garantia de idempotência.
Recibos não provam autoria ou execução contra alterações externas do banco.

Verificação em 25/10/2026: 31 testes passaram. Três testes novos exercitam o
fluxo cliente/gate/memória com resposta de modelo simulada, reabertura do banco,
rejeição de duplicata antes de nova chamada e falha de persistência sem retry.
Não foi executado modelo real nesta rodada. Nenhum serviço pago foi ativado.

## Criptografia e camadas de proteção

Dados privados permanecem fora deste protótipo. Antes de habilitá-los, exigir
criptografia autenticada reconhecida, gestão e recuperação testada de chaves,
backup/restauração e avaliação das exposições em memória e metadados. Não
inventar uma cifra própria nem empilhar 20 cifras. Os 20 controles desejados
devem ter escopo, estado e evidências individuais; este documento não declara
que esses 20 controles já estejam implementados ou aprovados.
