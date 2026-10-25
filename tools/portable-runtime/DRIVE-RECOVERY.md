# Ensaio de recuperação via Drive — 25/10/2026

Concluído com dados e chaves descartáveis. Não é cópia do projeto real nem
aprovação para dados privados. 45 testes passaram no conjunto Linux após
introdução do pacote de recuperação. No Windows, 27 testes distintos e permissões/DPAPI foram confirmados por
saídas enviadas pelo usuário, incluindo o pacote 7z (1 teste em 1,127 s).
Um teste adicional Linux integrou pacote de senha e backup em processo novo:
recuperação correta, senha errada e truncamento de cada arquivo. Todos passaram.
Esse teste integrado ainda precisa de execução no Windows; não testa DPAPI
nem recuperação em outro computador.

## Evidência do ciclo externo

Dois arquivos novos foram enviados para a pasta existente "03 — Testes sem
dados pessoais" do Drive conectado. Metadados consultados indicam shared=false
e permissão somente de proprietário. Nenhum compartilhamento foi habilitado.

1. Backup cifrado do banco sintético, 21.944 bytes:
   https://drive.google.com/file/d/1UtErzMEYUTyCRZ5lEXTJiILasljfr4T2/view
   SHA256 1de200456c2279f781d68ad5fca693bd8b99a80624e2f3dcc8e9b846ca22fbb9
2. Pacote 7z de recuperação, 330 bytes:
   https://drive.google.com/file/d/1S84NSANqg-zy6Khrh4GbID3M8XvrfE1L/view
   SHA256 ba10c98b09cb3dc266ba9634f143d0355349a8d05c8cbbb0990a5b1a8c6ea1f7

Ambos foram baixados pela integração autenticada, comparados byte a byte aos
originais e verificados pelos hashes. O pacote devolveu as duas chaves sintéticas
e elas restauraram o backup; a leitura do recibo retornou 42. A senha do ensaio
é fixa, pública no teste e deliberadamente inadequada para produção. Nenhum
segredo real foi usado. Os arquivos permanecem no Drive como fixtures de teste.
Não são backups úteis de trabalho do usuário.

## Implementação

recovery_package.pack/unpack usa formato 7z padrão com senha e cabeçalho
criptografado, por py7zr1.1.4 em venv separado. Essa versão contém correções
recentes, conferidas no changelog oficial:
https://github.com/miurahr/py7zr/blob/master/docs/Changelog.rst
Dependência opcional, não carregada pelo núcleo básico.

As chaves só são serializadas em memória. A leitura extrai para BytesIOFactory,
sem escrever caminhos de membros no disco. Aceita somente recovery.json regular,
sem symlink/junction, pequeno, com duas chaves Fernet distintas e JSON sem
duplicatas. Testes rejeitam senha errada, truncamento, senha curta e chaves iguais.
O formato7z não deve ser descrito como cifra autenticada AEAD: CRC não é MAC.
A validação posterior do banco/recibos também permanece obrigatória.

Limites de aceitação: entrada64KiB e conteúdo4KiB. Não são limites absolutos
de RAM/CPU do parser/KDF/descompressor. Não aceitar arquivos hostis, não executar
com python -O, e aplicar prazo/limites externos antes de disponibilizar a terceiros.
Mínimo20 caracteres de senha não comprova entropia. Senha forte precisa ser
definida pelo usuário, localmente, sem argumento de terminal/log/chat.

## Condições ainda pendentes

Não há gerador/CLI de chaves reais, migração, automação de upload ou serviço
permanente ativado. Não houve contratação de plano/API nem serviço pago ativado.
A cota e o plano do Drive não foram auditados. Nenhum arquivo privado foi enviado.

Antes de uso real, validar o fluxo integrado no Windows, implementar entrada local de
senha sem eco, guarda local protegida e recuperação em ambiente independente.
Não depender só de DPAPI para recuperação portátil. Não guardar a senha de
recuperação no mesmo Drive. Usar somente uma conta deixa disponibilidade sujeita
a perda/bloqueio/remoção nessa conta: uma segunda cópia independente continua útil.
Esses controles não impedem host comprometido, captura de senha ou perda dela.
