# Encerramento do ensaio de recuperação e controles de segurança

Em 25/10/2026, o conjunto portátil passou em 39 testes. O teste novo inicia
processos Python distintos para recuperar o arquivo Fernet completo. As duas
chaves sintéticas chegam por stdin, sem credenciais herdadas do ambiente.
Cada processo tem prazo de 15 segundos e recebe somente caminhos de backup e
destino. Isso não é sandbox: o processo ainda tem permissões normais do sistema.

Com ambas as chaves corretas, o recibo esperado foi recuperado. Ausência de
cada chave, chave de registros errada, chave de arquivo errada e truncamento
resultaram em saída 2, resultado genérico negativo e nenhum destino publicado.
As chaves originais não apareceram em stdout/stderr. A origem foi preservada.
Não foi usado outro computador ou conta. Não houve upload ou serviço pago.

O ensaio experimental de recuperação local em processo separado está concluído.
Não liberar dados privados ou declarar independência completa com essa evidência.

## Os 20 controles solicitados

São controles complementares, não 20 cifras sobrepostas. "Testado" abaixo
refere-se apenas ao protótipo, dados sintéticos e ambiente desta sessão.

| Nº | Controle | Estado/evidência |
|---|---|---|
| 1 | Execução offline por padrão | Testado no cliente/integrador |
| 2 | Destino restrito a loopback | Testado; não impede servidor de encaminhar dados |
| 3 | Sem redirects automáticos | Testado em HTTP sintético |
| 4 | Sem retries/fallback automáticos | Testado; evita repetição implícita |
| 5 | Limites de entrada e resposta | Testados no cliente/gate |
| 6 | Esquema fechado de ferramenta | Testado para add exclusivamente |
| 7 | Correspondência com intenção do chamador | Testada para dois operandos |
| 8 | Prévia antes de execução explícita | Testada no integrador |
| 9 | Sem interpretação de código gerado | Soma fixa; nenhuma ferramenta geral habilitada |
| 10 | SQL parametrizado | Implementado/testado nas consultas locais |
| 11 | Registros sem sobrescrita | Testado por duplicata |
| 12 | Permissões locais restritas | Modo600 POSIX; diretório confiável é premissa |
| 13 | Criptografia autenticada dos recibos | Fernet testado com chave errada/adulteração |
| 14 | Criptografia do arquivo de backup | Fernet testado; tamanho/timestamp continuam visíveis |
| 15 | Separação de chave do banco e do backup | API exige chaves diferentes; custódia real pendente |
| 16 | Backup consistente e validação antes de publicar | SQLite backup + autenticação dos recibos |
| 17 | Restauração sem sobrescrever destino | Testada em caminhos novos |
| 18 | Recuperação com processo separado | Testada nesta máquina; outro dispositivo pendente |
| 19 | Guarda durável, recuperação e rotação de chaves | Pendente; nenhuma chave de produção criada |
| 20 | Segurança da implantação, dependências e acesso | Revisão de produção, autenticação, isolamento e atualização pendentes |

## Condições restantes para uso privado

Definir custódia das DUAS chaves sob controle do usuário, separada do backup;
confirmar recuperação no ambiente de destino e limitar seus acessos. Esta sessão
temporária e Git não são locais de custódia. Não solicitar segredos no chat.
Não criar uma chave real para depois depender deste ambiente para recuperá-la.

Permanecem também as limitações de SEALED-BACKUP.md: metadados locais, conteúdo
em RAM, temporários sem apagamento seguro, ausência de proteção contra rollback,
host comprometido e queda de energia. O caminho foi testado em Linux; Windows
não foi validado. Os 20 controles não equivalem a auditoria ou risco zero.

Próximas fases do projeto: custódia/recuperação real de chaves, ferramenta útil
com escopo limitado e permissões explícitas, avaliação mais ampla do modelo e
implantação portátil. A base existente permanece preservada até validação.
