# Política do Backup Independente

## Objetivo
Proteger o código, o histórico e o trabalho local sem depender do Ruflo.

## Princípios de segurança
- Nunca apagar arquivos de origem durante o backup.
- Nunca restaurar diretamente sobre a origem na primeira versão.
- Verificar integridade e SHA-256 dos arquivos incluídos.
- Não considerar um backup válido apenas porque o arquivo foi criado.
- Não enviar backups para serviços externos por padrão.
- Não instalar dependências para executar o backup.
- Não incluir segredos, tokens, chaves privadas ou credenciais.
- Não executar comandos Git destrutivos nem criar commits automaticamente.

## Inclusão
- Código-fonte, testes e documentação.
- Configurações versionadas necessárias ao projeto.
- Alterações rastreadas e não rastreadas, inclusive não commitadas.
- Histórico Git, incluindo commits locais.
- Dados locais selecionados explicitamente após avaliação.

## Exclusão inicial
- node_modules e outras dependências regeneráveis.
- Saídas de build, caches e arquivos temporários.
- Credenciais e arquivos .env, exceto modelos .example aprovados.
- Bancos SQLite ativos não verificados: devem receber tratamento específico.
- Backups anteriores, para evitar inclusão recursiva.

## Restauração
- Restaurar primeiro em diretório separado.
- Validar manifesto, hashes e integridade antes de considerar a recuperação concluída.
- Nunca substituir automaticamente arquivos existentes.

## Retenção
- Nenhuma exclusão automática de backups até que a validação e a restauração sejam testadas.

## Limitações
- Um backup armazenado apenas no mesmo Codespace não protege contra perda ou exclusão desse ambiente.
- Cópias externas só poderão ser habilitadas após avaliação de segurança, custo e privacidade.

## Regras adicionais definidas após o inventário

- O inventário não deve percorrer `.git`, `node_modules`, diretórios de build/cache ou a própria pasta de backup.
- A classificação por nome é apenas um indício: palavras como token, password ou credential em arquivos de código não bastam para excluí-los.
- Arquivos `.env`, chaves privadas e credenciais reais devem ser excluídos; modelos `.example` podem ser incluídos após validação.
- Arquivos ignorados pelo Git devem ser avaliados explicitamente, pois podem conter trabalho local importante.
- Arquivos de estado em `.claude-flow`, `.claude` e `.swarm` não devem ser descartados em bloco; cada categoria deve ser avaliada.
- Bancos SQLite ativos, arquivos WAL/SHM e bancos de ferramentas não serão copiados por cópia simples. A inclusão depende de snapshot consistente e validação de integridade.
- Bancos regeneráveis em dependências ou builds podem ser excluídos após confirmação de que não contêm dados exclusivos do usuário.
- O histórico Git será preservado separadamente da árvore de trabalho, para incluir os commits locais sem depender de commits novos.
- O inventário deve registrar caminhos e tamanhos, sem imprimir conteúdo de arquivos potencialmente sensíveis.
- A primeira versão do sistema deve produzir backups locais com manifesto SHA-256 e verificação de integridade, sem exclusão automática nem envio externo.
