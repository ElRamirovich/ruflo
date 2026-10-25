# Backup e recuperação experimental da memória criptografada

memory_backup.snapshot(source, destination, key) usa a API backup do SQLite
para criar um snapshot consistente do banco experimental. A mesma função serve
para restaurar uma cópia em caminho NOVO. Não substitui arquivos nem salva a
chave. Requer encrypted_memory e cryptography; não instala dependências.

O snapshot é criado em diretório temporário privado ao lado do destino, arquivo
modo 600 em POSIX. Antes da publicação, verifica chave, integridade SQLite e
autenticação/conteúdo de cada recibo. Os payloads já chegam criptografados ao
SQLite. A publicação usa hard link para recusar um destino que já exista,
inclusive se for criado durante a operação. O arquivo temporário é removido
ao terminar. A origem nunca é apagada ou substituída.

Limites deste protótipo: 16 MiB e 1000 recibos; checagem de prazo de 10 segundos
no callback da cópia. Isso não é um deadline total para validação ou I/O:
chamadores devem impor um prazo externo. Hard links precisam ser suportados no
filesystem; falha não autoriza substituir destino. Não há garantia de durabilidade
contra queda de energia (o diretório final não recebe fsync). Usar somente bancos
confiáveis em diretórios privados, sem alterações de caminhos por outro processo.
Não é parser seguro para bancos hostis, nem proteção contra rollback de backups.

## Evidência de 25/10/2026

36 testes passaram no conjunto portátil. Dois novos testes verificam:

- criação de banco sintético, backup, restauração e leitura por outro processo;
- chave de teste enviada ao processo por stdin, sem chave no argumento ou log;
- recuperação do resultado esperado, sem campo result em claro no arquivo;
- chave errada rejeitada, sem destino publicado e sem alteração da origem;
- conteúdo criptografado adulterado rejeitado antes de publicar;
- arquivo existente no destino preservado.

O subprocesso tem prazo de 15 segundos. Os bancos e a chave são descartáveis,
criados apenas para o ensaio. Não houve inferência real, upload para Drive,
migração de dados privados ou ativação de serviço pago nesta rodada.

## Estado e próximo limite

Concluído: caminho experimental de backup/restauração de recibos criptografados,
com recuperação em processo separado. Não equivale a backup completo do projeto,
recuperação em outro computador, serviço automático ou gestão de chaves pronta.
Perder a chave continua podendo tornar os dados irrecuperáveis. Identificadores,
esquema e timestamp dos tokens permanecem visíveis conforme ENCRYPTED-MEMORY.md.

Antes de dados privados, definir guarda durável de chave separada do banco,
recuperação fora deste ambiente, política de acesso e revisão da implantação.
Não há 20 controles aprovados nem promessa de risco zero.
