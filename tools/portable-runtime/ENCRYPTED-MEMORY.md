# Adaptador criptografado experimental

EncryptedMemory oferece a mesma interface append/get/close da TaskMemory e
pode ser usada por run_recorded. Usa Fernet da biblioteca cryptography,
versão instalada/testada 50.0.2. É uma dependência opcional deste adaptador;
os componentes anteriores continuam usando biblioteca padrão. Nenhum pacote
foi instalado nesta rodada e não há download automático ao importar.

A chave é fornecida pelo chamador e nunca é salva pelo adaptador. Os testes
geram chaves descartáveis em memória. Não são chaves de produção nem backups
de chave entregues ao usuário. Não colocar chaves em Git, logs, argumentos de
terminal ou no mesmo backup do banco sem proteção independente.

O payload é criptografado ANTES do INSERT: operandos e resultado não são
enviados em claro ao SQLite. O ID é incluído no conteúdo autenticado e conferido
na leitura. Um marcador criptografado verifica a chave ao abrir o banco.
Não há fallback para banco em claro nem migração automática. Criar somente um
banco novo para ensaios sintéticos, em diretório privado confiável, um escritor.

Fernet fornece criptografia autenticada e inclui timestamp visível; documentação:
https://cryptography.io/en/latest/fernet/
Isso não equivale a criptografia integral do SQLite: IDs, esquema, tamanho,
contagem de registros e timestamps Fernet permanecem visíveis. O conteúdo e
a chave existem em memória durante o uso. Administrador/host comprometido não
estão protegidos. Não há proteção contra restauração de versão antiga do banco,
remoção de registros ou troca de registros entre bancos com a mesma chave/ID.
Não há assinatura de autoria nem garantia de execução exatamente uma vez.

34 testes passaram em 25/10/2026. Três novos testes cobrem reabertura com a
mesma chave, rejeição de chave errada e token adulterado, ausência do campo
result em claro no arquivo de ensaio, vínculo do ID e composição com tarefa
validada usando resposta de modelo simulada. Não provam ausência absoluta de
plaintext em qualquer ambiente, auditoria completa ou inferência real.

Próximas exigências antes de dados privados: guarda e recuperação durável de
chaves, recuperação em processo/dispositivo separado, backup consistente e
restauração testada, revisão das dependências e do ambiente de implantação.
A perda da chave pode tornar os registros irrecuperáveis. Nenhum dado privado
foi migrado e nenhum serviço pago foi ativado. Não há 20 camadas aprovadas;
este é um controle específico com limites declarados.
