# Portabilidade: inventário offline

Esta ferramenta prepara a independência do ambiente. Não migra dados, não instala
dependências e não altera os serviços existentes. Requer apenas Python 3.10+.

Na raiz do checkout:
```bash
python3 tools/portability/check.py
python3 -m unittest discover -s tools/portability -p 'test_*.py' -v
```
Para examinar outro checkout, use `--root /caminho/do/projeto`.
A saída JSON vai apenas para stdout. Código de saída 0 significa inventário
concluído, não prontidão para migração.

O relatório verifica disponibilidade de executáveis no PATH e presença de três
componentes conhecidos. Não abre esses arquivos, não examina credenciais, não
resolve destinos de links simbólicos, não percorre a árvore e não chama Git,
Docker, registries ou modelos. Não inclui caminhos absolutos ou remotes.
Um marcador .git não comprova histórico completo ou associação do Codespaces.

## Próximas etapas, sem remover capacidades

1. Consolidar código e alterações locais no repositório próprio, preservando
   licenças/avisos. Auditar o histórico antes de qualquer nova distribuição.
2. Fixar versões e registrar configuração necessária, sem segredos.
3. Verificar backup e restauração de código e snapshots de dados selecionados.
   Os backups atuais são parciais; não afirmar preservação completa.
4. Preparar ambiente alternativo sob controle do proprietário. Pode ser local
   ou outro host; verificar recursos/cota antes de contratar ou iniciar serviços.
5. Provisionar segredos pelo canal privado do ambiente de destino, sem conceder
   acesso ao repositório upstream como atalho.
6. Validar gateway e uma tarefa de código completa em branch isolada.
7. Comparar capacidades e resultados com a origem antes de qualquer corte.

Manter o ambiente original até validação e autorização da migração real.
Não copiar banco ativo de forma simples nem mudar chaves de criptografia.
Não mover dados reais ou fazer deploy com base somente neste inventário.

## Independência verificável

- O núcleo deve continuar funcionando sem RTK, find-skills ou ferramentas SEO.
- Um gateway deve poder ser substituído por outro por um contrato documentado.
- Modelos externos continuam dependências externas. A alternativa local exige
  hardware, modelo adequado e validação; presença do Ollama não comprova isso.
- Não tornar uma conta específica de nuvem obrigatória para construir o código.
- A ferramenta é diagnóstico, não um sandbox nem uma política de bloqueio.
- Nenhuma rotina em segundo plano é iniciada por ela.

A especificação de produto e critérios de aceitação está em
[ESPECIFICACAO-AGENTE.md](../../docs/integrations/ESPECIFICACAO-AGENTE.md).
