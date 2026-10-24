# Backup local independente

Requisitos: Linux (incluindo Codespaces), Python 3.10+ e Git. Nenhum pacote
Python, Ruflo, serviço externo, API ou instalação no computador pessoal.

## Criar e verificar

Execute na raiz do repositório, preferencialmente sem outros processos escrevendo:

```bash
python3 independent-backup/backup.py create --output /workspaces/ruflo-backups
```

O comando inclui arquivos rastreados e não rastreados, alterações não commitadas
e um `history.bundle` separado para todos os refs e HEAD locais. Audita nomes e
conteúdo de objetos históricos, executa `git bundle verify`, calcula SHA-256 de
cada membro, relê os arquivos de origem e verifica o ZIP antes de publicar um
nome final único. Em erro, não declara nenhum backup válido. Temporários privados
de uma tentativa são removidos; backups publicados e arquivos de origem nunca
são removidos. Não executa commits, hooks, restauração, uploads ou chamadas de rede.

A pasta de saída deve ficar **fora do repositório**. O ZIP final recebe permissão
600; temporários e novos diretórios de saída recebem 700. Use uma pasta privada;
permissões de uma pasta de saída preexistente não são alteradas.

```bash
python3 independent-backup/backup.py verify /workspaces/ruflo-backups/backup-ID.zip
python3 independent-backup/backup.py restore /workspaces/ruflo-backups/backup-ID.zip --to /workspaces/ruflo-recuperado-ID
```

A restauração verifica o arquivo antes de criar o destino, exige um diretório
novo fora da origem, rejeita links/caminhos inseguros e nunca sobrescreve arquivos.
Se uma falha de disco interromper a restauração, o destino parcial será mantido;
use outro destino novo na tentativa seguinte. O manifesto fica dentro do ZIP.

O histórico é restaurado como `.backup-history.bundle`. Para inspecioná-lo sem
sobrescrever a árvore recuperada:

```bash
git clone /workspaces/ruflo-recuperado-ID/.backup-history.bundle /workspaces/ruflo-historico-ID
```

## Exclusões e limites

### Diagnosticar um bloqueio do histórico

```bash
python3 independent-backup/backup.py audit-history --limit 20
```

Esse comando somente lê os objetos Git e imprime hashes, caminhos e categorias,
sem valores encontrados nem conteúdo dos arquivos. O código de saída 2 indica
achados, histórico raso ou auditoria incompleta; 0 indica varredura completa sem
achados. O limite evita relatórios grandes; `complete: false` nunca significa
histórico aprovado. A auditoria não altera commits nem libera exceções por pasta.

Um marcador de chave privada isolado dentro de uma string de código não é uma
chave. O detector diferencia esse caso de PEM com quebra de linha real ou escapada;
PEM completo ou truncado continua bloqueado, inclusive dentro de testes. Tokens
de outros formatos e credenciais em nomes sensíveis continuam sujeitos à auditoria.

### Itens que não entram automaticamente

- Credenciais conhecidas por nome, `.env` reais, chaves privadas e conteúdo com
  padrões de segredos são excluídos e registrados com motivo, sem imprimir valores.
  Modelos `.env.example`/`.env.template` passam pela mesma inspeção de conteúdo.
  A detecção é heurística: pode excluir fixtures e não garante ausência de segredos.
  Revise exclusões antes de chamar uma cópia de completa. Não publique o ZIP.
- Bancos SQLite (incluindo arquivos sem extensão reconhecidos pelo cabeçalho),
  WAL/SHM, dependências, caches, temporários e arquivos de backup são excluídos.
  Bancos ativos usam o fluxo explícito de snapshot consistente abaixo.
- Links simbólicos são registrados como excluídos; destinos nunca são copiados.
  Submódulos/arquivos especiais não suportados e erros de leitura bloqueiam a criação.
- Arquivos ignorados pelo Git não entram automaticamente; o manifesto lista esses
  caminhos para revisão. Não presuma que a cópia contém estados locais ignorados.
- Saídas `dist`/`build` rastreadas entram; saídas não rastreadas ficam excluídas.
  O relatório de inventário gerado é excluído; os scripts de backup são incluídos.
- O histórico não pode ser parcialmente filtrado sem perder sua identidade. Se a
  auditoria encontrar possíveis segredos, a criação com histórico é bloqueada.
  Repositórios rasos também bloqueiam esse modo. Não baixa histórico automaticamente.
  Para uma cópia **explicitamente parcial, sem histórico**, use:

  ```bash
  python3 independent-backup/backup.py create --output /workspaces/ruflo-backups --without-history
  ```

  Nesse modo o manifesto marca `history: false`. Não substitui o backup completo.
- Limites: 256 MiB por arquivo/objeto Git/bundle, 50 GiB descompactados por ZIP,
  200 mil membros. A criação falha se os limites forem excedidos.
- SHA-256 detecta corrupção acidental; o manifesto não é uma assinatura contra
  adulteração intencional. Não restaure arquivos recebidos de origem não confiável.
- As verificações detectam mudanças comuns durante a cópia, mas não são um snapshot
  atômico do sistema de arquivos. Pare tarefas que escrevem antes de executar.
  O modelo de uso não inclui um processo hostil do mesmo usuário trocando diretórios
  simultaneamente. A pasta de restauração deve permanecer privada durante a operação.
- Backup no mesmo Codespace não protege contra exclusão/perda do ambiente.
  Agendamento, retenção automática e cópias externas não estão habilitados.

## Snapshots explícitos de bancos SQLite

Depois de avaliar quais bancos contêm estado único, selecione cada um pelo
caminho relativo ao repositório. Exemplo para o banco de memória do projeto:

```bash
python3 independent-backup/sqlite-snapshot.py --output /workspaces/ruflo-backups --database .swarm/agentdb-memory.db
```

Repita `--database` para incluir outros bancos avaliados na mesma cópia. O comando
abre a origem em modo SQL somente leitura e usa a API online de backup do SQLite
para incluir páginas WAL confirmadas sem incluir transações não commitadas.
Não copia WAL/SHM separadamente. O SQLite pode coordenar leitores pelos arquivos
auxiliares de memória compartilhada; não altera registros SQL da origem.

Cada banco é consistente individualmente; não há transação conjunta entre bancos.
A cópia é bloqueada se houver erro, tempo excedido, banco substituído, padrão de
credencial detectado ou falha em `PRAGMA integrity_check`. A detecção de segredos
continua heurística. Bancos cifrados ou que exigem extensões podem não ser suportados.
Dependências, links e backups antigos não são elegíveis para esse fluxo.

O ZIP `sqlite-snapshot-ID.zip` é privado, contém manifesto SHA-256 e só recebe
nome final depois da verificação de todos os membros. Nenhum backup anterior é
excluído. Pode ser verificado e restaurado pelo mesmo `backup.py`, sempre em
diretório novo; os bancos recuperados mantêm seus caminhos relativos. O histórico
Git não faz parte desse ZIP, e ele não substitui a cópia dos arquivos do projeto.

## Testes isolados

### Verificar a preparação do agente sem chamar uma API

```bash
python3 independent-backup/agent-check.py
```

O diagnóstico somente lê arquivos e conta processos candidatos. Mostra presença
de suporte Google no código e no build, configuração/chave presentes (sem valores),
contagens de registros de agentes e versão do Node. Não carrega `.env`, inicia
agentes, escreve estado, instala dependências ou envia requisições de inferência.
`live_agent_confirmed: false` é intencional: configuração, processos e registros
não comprovam uma execução real. A disponibilidade do modelo e o plano de cobrança
não são verificados. Um teste real com API exige confirmar antes que não terá custo.

### Executar testes do backup e diagnóstico

```bash
python3 -m unittest discover -s independent-backup -p 'test_*.py' -v
```

Os testes criam repositórios temporários, recuperam histórico Git e arquivos
modificados/não rastreados, e exercitam corrupção, caminhos maliciosos, links,
colisões, exclusões, alterações concorrentes e proibição de sobrescrita.
