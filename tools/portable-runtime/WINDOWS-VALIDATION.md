# Validação Windows em andamento — 25/10/2026

Resultados enviados pelo usuário, não execução remota deste agente:
Python 3.14.4; cryptography50.0.2 em venv, cffi2.1.1 e pycparser3.12.
17 testes básicos, 3 de memória criptografada e 2 de snapshot/recuperação
passaram: 22 testes distintos confirmados no Windows.

O snapshot inicialmente falhou em fsync com Bad file descriptor. A correção
15e667d09700ecf919aac17d19831a3f2d7ffb25 usa r+b no arquivo temporário,
mantendo fsync e sem truncar o arquivo. Os dois testes passaram após a correção.

## Adaptação seguinte, ainda aguardando execução no Windows

sealed_backup.bounded_read agora usa O_BINARY quando disponível, mantém
O_NOFOLLOW/O_NONBLOCK nos sistemas que os suportam e rejeita arquivos especiais,
diretórios, tamanho excedente e FILE_ATTRIBUTE_REPARSE_POINT antes de abrir.
Antes de ler compara identidade st_dev/st_ino da inspeção e do descritor aberto.
Identidade zero ou diferente é rejeitada. Isso não substitui confinamento por
handles nativos contra diretórios hostis: continuam obrigatórios pais confiáveis,
arquivos controlados e ausência de alterações concorrentes. O snapshot original
também mantém suas premissas de diretório confiável.

44 testes passaram no ambiente Linux após essa alteração. São quatro os testes
de test_sealed_backup; a checagem reparse usa simulação de atributo e não comprova
todos os tipos reais de reparse point do Windows.

A próxima rodada no computador do usuário testa proteção do arquivo completo,
ida/volta, chaves erradas, corrupção, preservação de destino e leituras limitadas.
Todos os dados/chaves são descartáveis. Não foram geradas chaves permanentes,
habilitados dados privados ou ativados serviços pagos por esta mudança.

## Limites para implantação

key_custody continua POSIX; NÃO executar generate para produção no Windows.
Modo600 não comprova ACL privada no Windows. Falta implementar/revisar os
controles nativos e escolher guarda durável/recuperação independente de chaves.
Os metadados visíveis, temporários, limites e premissas de SEALED-BACKUP.md
continuam aplicáveis. A mudança amplia compatibilidade experimental, não concede
aprovação de produção nem equivale à independência completa.
