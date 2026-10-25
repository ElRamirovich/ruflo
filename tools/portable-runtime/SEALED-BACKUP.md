# Backup completo protegido — experimental

sealed_backup.seal(source, destination, memory_key, backup_key) cria snapshot
consistente da memória criptografada e cifra o arquivo inteiro com Fernet.
unseal(...) autentica a cópia, restaura em área temporária privada e valida
integridade SQLite e recibos antes de publicar um destino novo.

As duas chaves são fornecidas pelo chamador e precisam ser diferentes. Nenhuma
é gerada ou salva automaticamente. O formato externo é um token Fernet padrão;
não se implementa cifra própria. Dependência opcional já instalada/testada:
cryptography 50.0.2. O modelo não recebe chaves ou acesso a esses métodos.

O arquivo de backup protege inclusive os IDs e o esquema SQLite. Tamanho,
timestamp Fernet e nome externo do arquivo continuam observáveis. O banco em
uso/restaurado ainda expõe os metadados descritos em ENCRYPTED-MEMORY.md.
As chaves e conteúdo decifrado existem na RAM. Não há proteção contra host
comprometido, rollback, apagamento ou posse indevida das duas chaves.

Arquivos temporários têm modo 600 dentro de diretórios privados em POSIX.
Snapshot máximo 16 MiB/1000 recibos; token máximo 24 MiB. Leitura rejeita
symlink final e arquivos especiais. Publicação por hard link não substitui
destinos. Usar filesystem compatível, diretórios/bancos confiáveis e prazo
externo. Não há garantia de eliminação física de temporários, proteção contra
corridas em diretórios hostis ou durabilidade contra queda de energia.

## Evidência em 25/10/2026

38 testes passaram no conjunto portátil. Dois novos testes verificam ida/volta,
recuperação do valor esperado, ausência de marcadores conhecidos de esquema/ID
no backup, rejeição de chaves iguais, chave de arquivo errada, chave de registro
errada, truncamento e preservação de backup existente. Falhas de restauração
não publicam o destino. Essa observação de marcadores não substitui revisão
criptográfica. Os testes usam exclusivamente chaves e registros descartáveis.

Não foram ativados serviços pagos, feitos uploads ou migrados dados privados.
Este recurso cobre o pequeno banco experimental, não todos os dados do projeto.
O ensaio em processo separado permanece documentado em MEMORY-RECOVERY.md;
o novo teste da camada externa ocorre no mesmo processo.

Próximo requisito para liberação: guarda durável e recuperação das DUAS chaves
fora deste ambiente, com acesso controlado e teste de recuperação no destino
real. Não armazenar chaves em Git/logs/chat nem junto do arquivo sem proteção
independente. Dados privados permanecem bloqueados. Não há declaração de 20
camadas implementadas ou de independência completa.
