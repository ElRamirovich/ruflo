# Memória local experimental

task_memory.py implementa recibos de somas em SQLite, sem dependência de Ruflo,
FreeLLMAPI ou serviço de banco externo. Usa somente Python e biblioteca padrão.
Destina-se exclusivamente a dados sintéticos em diretório privado confiável.
Não está conectado automaticamente ao modelo ou ao task_runner.

TaskMemory(path, create=True) cria um arquivo novo com modo 600 em POSIX e
recusa substituir arquivo existente. Sem create, exige banco existente.
append(id,a,b,result) aceita somente soma consistente com inteiros limitados;
IDs duplicados são rejeitados. get(id) recupera um recibo, e close() fecha
a conexão. Chamadores devem fechar a conexão em finally. SQL usa parâmetros;
nenhuma instrução SQL é recebida do modelo. Não existe API de exclusão.

O banco NÃO é criptografado. Permissões POSIX não equivalem a proteção no
Windows ou contra administradores. Não usar com credenciais, conteúdo pessoal,
bancos recebidos de terceiros ou diretórios alteráveis por outros processos.
A checagem de arquivo não é confinamento resistente a corridas de symlink.
Um administrador pode modificar o banco: não há autenticidade criptográfica
dos recibos, auditoria inviolável ou proteção contra adulteração offline.

Validação em 25/10/2026: 28 testes passaram no conjunto portátil. Três testes
novos verificam persistência após reabertura, preservação do registro original
quando há duplicata, rejeição de recibos inconsistentes, consulta parametrizada
e ausência de criação implícita de banco inexistente. Isso não valida memória
semântica, recuperação de desastre, concorrência intensa ou criptografia.

Próxima integração: registrar recibos pelo chamador confiável após validação e
execução, com falhas de persistência explícitas. Antes de guardar dados privados,
definir criptografia e recuperação de chaves. Não migrar dados atuais ainda.
