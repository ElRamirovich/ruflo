# Guarda local de chaves e recuperação — Windows

Esta implementação integra DPAPI CurrentUser, verificação de ACL, entrada de
senha sem eco e os módulos existentes de memória/backup. É específica para o
banco de recibos do protótipo (até 16 MiB e 1.000 recibos), não para copiar o
repositório Ruflo ou outros arquivos do computador. Não é um agente completo.

## Estado da validação

O usuário confirmou 28 testes anteriores no Windows, incluindo a recuperação
do banco em processo separado a partir do pacote e senha. Os novos módulos
windows_dpapi e windows_vault ainda aguardam teste nativo nesse Windows.
Os testes de composição Linux usam um protetor simulado explicitamente;
isso não comprova DPAPI, ACL ou execução do PowerShell no Windows.

## Controles implementados

- API nativa CryptProtectData/CryptUnprotectData, CurrentUser, UI_FORBIDDEN,
  entropia de domínio fixa, limites de entrada/saída, readback antes/depois de gravar.
- DLLs pesquisadas em SYSTEM32; PowerShell localizado via GetSystemDirectoryW,
  com script fixo, ambiente mínimo, módulos do sistema e sem perfil.
- Diretório existente deve pertencer ao usuário e ter exatamente duas regras
  Allow FullControl: usuário e SYSTEM, herdáveis por arquivos/subdiretórios.
  Nenhuma permissão de pasta existente é alterada automaticamente.
- Apenas discos fixos locais, sem UNC/reparse points nos caminhos examinados.
  Isso não é confinamento por handles contra alteração concorrente de caminhos.
- Senha local via getpass; terminal obrigatório; falha se eco não puder ser
  desabilitado. Sem senha em argumento, variável de ambiente, log ou saída.
  Mínimo de 20 caracteres não garante força: use senha longa, única e imprevisível.
- Inicialização e restauração exigem pasta nova. READY só é escrito ao final.
  Falha pode deixar pasta parcial: é preservada, nunca reutilizada automaticamente.
- Origem e destinos existentes não são substituídos. Temporários próprios são
  removidos; isso não constitui apagamento seguro de mídia.
- Nenhuma API/modelo, Drive, serviço de rede ou tarefa agendada é acionada.
  Não se promete ausência de tráfego interno do Windows/antivírus/domínio.

## Arquivos

`keys.dpapi` guarda as duas chaves protegidas para o usuário Windows. Não é o
mecanismo portátil de recuperação. `recovery.7z` guarda as mesmas chaves sob a
senha de recuperação; o formato e suas limitações estão em DRIVE-RECOVERY.md.
`memory.db` contém a memória local; seus metadados locais permanecem visíveis.
`initial.fernet` é a cópia cifrada da memória inicialmente vazia. READY indica
conclusão do fluxo, não é assinatura nem prova contra rollback.

Para nuvem, somente o pacote `recovery.7z` e o backup `.fernet` correspondente.
Não enviar keys.dpapi, memory.db, senha ou a pasta inteira. A senha precisa de
guarda independente do Drive; uma única conta não protege contra perda da conta.

## Teste nativo, somente dados fictícios

Com o venv e arquivos já verificados, definir TEST_CUSTODY para a pasta privada
preparada anteriormente e executar:

```powershell
$env:TEST_CUSTODY = $custodia
& $pythonTeste -m unittest test_windows_dpapi test_windows_vault -v
```

O teste integrado cria um subdiretório temporário próprio, gera chaves fictícias,
protege com DPAPI, grava um recibo 17+25=42, cria backup, recupera em nova pasta e
verifica senha errada/corrupção/não sobrescrita. Remove apenas suas próprias
fixtures ao terminar. Não utiliza uma senha real. Esses testes não demonstram
recuperação em outro computador ou outra conta Windows.

## Operações disponíveis após validação nativa

Todos os comandos são executados na pasta de código confiável, com o Python do
venv. `--directory` na inicialização/recuperação deve ser uma pasta NOVA abaixo
da custódia privada. Não use a própria pasta de custódia existente como destino.

```text
windows_vault.py init --directory NOVA_PASTA
windows_vault.py check --directory PASTA_CRIADA
windows_vault.py backup --directory PASTA_CRIADA --output NOVO_BACKUP.fernet
windows_vault.py recover --package recovery.7z --archive BACKUP.fernet --directory NOVA_PASTA
```

init pede senha duas vezes; recover uma vez. Não informe senha no comando.
backup exige pasta de destino com ACL privada. Para usar cópias baixadas do
Drive, baixe os dois arquivos cifrados para disco local primeiro. Use apenas
pacotes criados por este programa: o parser 7z não é um sandbox para arquivos
hostis, e seus limites não são limites absolutos de memória/CPU.

Criação da memória vazia não migra trabalho existente, não ativa uso de modelos,
não envia backup ao Drive e não comprova cópia de todo o projeto.

## Limites de custódia

DPAPI depende do contexto de usuário/perfil Windows. Administrador, malware no
mesmo usuário ou captura da senha podem comprometer dados. Strings e bytes do
Python não têm apagamento garantido; limpar buffers nativos não muda isso.
Não há rotação automática, proteção contra rollback nem garantia de durabilidade
em queda de energia. Não guardar a única cópia recuperável neste computador.

Referências nativas:
https://learn.microsoft.com/en-us/windows/win32/api/dpapi/nf-dpapi-cryptprotectdata
https://learn.microsoft.com/en-us/windows/win32/api/dpapi/nf-dpapi-cryptunprotectdata
https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.security/get-acl
