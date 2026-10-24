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

- Credenciais conhecidas por nome, `.env` reais, chaves privadas e conteúdo com
  padrões de segredos são excluídos e registrados com motivo, sem imprimir valores.
  Modelos `.env.example`/`.env.template` passam pela mesma inspeção de conteúdo.
  A detecção é heurística: pode excluir fixtures e não garante ausência de segredos.
  Revise exclusões antes de chamar uma cópia de completa. Não publique o ZIP.
- Bancos SQLite (incluindo arquivos sem extensão reconhecidos pelo cabeçalho),
  WAL/SHM, dependências, caches, temporários e arquivos de backup são excluídos.
  Bancos ativos exigem um futuro fluxo próprio de snapshot consistente.
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

## Testes isolados

```bash
python3 -m unittest discover -s independent-backup -p 'test_*.py' -v
```

Os testes criam repositórios temporários, recuperam histórico Git e arquivos
modificados/não rastreados, e exercitam corrupção, caminhos maliciosos, links,
colisões, exclusões, alterações concorrentes e proibição de sobrescrita.
