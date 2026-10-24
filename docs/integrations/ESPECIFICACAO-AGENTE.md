# Especificação consolidada da versão própria do agente

Data: 24/10/2026. Estado: proposta de implementação e registro de evidências.
Este documento organiza a primeira entrega; não declara funcionalidades futuras como prontas.
Complementa [a avaliação das integrações](ASSESSMENT.md) e
[o adaptador FreeLLMAPI](../../tools/freellmapi/README.md).
Não substitui políticas técnicas já existentes nem autoriza deploy, migração de dados reais,
ampliação de permissões ou contratação de serviços.

## 1. PRD: produto e primeira entrega

Objetivo: permitir que o proprietário solicite pelo navegador, inclusive no celular,
uma alteração pequena de código e receba uma proposta verificável com testes.
Preservar as capacidades existentes do fork; não reimplementar o núcleo por conveniência.

Primeira entrega demonstrável:
1. Receber uma tarefa e explicitar objetivo, arquivos permitidos e critério de conclusão.
2. Trabalhar em branch/worktree isolados, preservando alterações anteriores.
3. Produzir a alteração e executar verificações pertinentes.
4. Apresentar diff, comandos executados, resultados e limitações.
5. Deixar merge e deploy fora desse fluxo inicial.

Fora desta entrega: controle de celular por ADB, pentest ativo, publicação automática,
pagamentos, vendas autônomas, captura de sessões reais e treinamento com dados de terceiros.
Essas capacidades continuam como candidatas futuras, não como recursos removidos.

Restrições: não contratar serviços pagos; não ativar faturamento de modelos;
não tratar crédito promocional como gratuidade permanente; não garantir risco zero.
Recursos do Codespaces continuam sujeitos à cota da conta, inclusive armazenamento.

## 2. TRD: arquitetura e contratos

| Componente | Responsabilidade | Limite |
| --- | --- | --- |
| Interface | Receber pedidos e apresentar estado/resultado | Não executar comandos por texto não confiável |
| Coordenador Ruflo/fork | Registrar tarefas, memória e coordenação | Registro de agente não comprova execução |
| Executor | Editar arquivos e rodar ferramentas autorizadas | Escopo, duração e permissões por tarefa |
| Gateway de modelos | Autenticar e encaminhar chamadas | Provedores/modelos permitidos explicitamente |
| Verificador | Conferir artefatos, testes e critérios de aceitação | Não confundir mocks com inferência real |
| Backup independente | Preservar código e dados selecionados | Restauração isolada e integridade verificadas |

FreeLLMAPI é o candidato já preparado. OmniRoute será comparado isoladamente,
sem encadear dois gateways na primeira entrega. A escolha definitiva exige uma
requisição válida, ferramentas compatíveis, falhas controladas e revisão de custos.

Contrato preparado no adaptador existente:
- origem local do gateway: http://127.0.0.1:3001, sem /v1 no ANTHROPIC_BASE_URL;
- rota de compatibilidade: /v1/messages;
- chave unificada injetada no ambiente do filho, sem argumentos, logs ou Git;
- FREELLM_FREE_ONLY_CONFIRMED é declaração operacional, não auditoria de cobrança;
- nenhum fallback pago ou repetição ilimitada;
- respostas 401/403, 404, 429, 503 e timeout devem ter estados distintos;
- nenhum sucesso deve ser declarado antes de validar a resposta e o artefato.

Uma chave de provedor Google e uma chave unificada do gateway são credenciais diferentes.
Não ler credenciais do banco interno para contornar o login ou a configuração de segredos.

Independência: separar propriedade do código, associação do Codespaces e fornecedores
de inferência. O fork não muda automaticamente o repositório de origem do Codespaces.
Não ampliar acesso de segredos ao upstream como solução automática. A futura mudança
de ambiente requer inventário das alterações locais e plano para os dados do gateway.
Não copiar SQLite ativo nem mudar chaves de criptografia durante a migração.
A migração real permanece sujeita à avaliação específica de risco e cota.

## 3. Fluxos e estados

Fluxo principal: pedido → plano com escopo → verificação das permissões →
execução isolada → testes → revisão da evidência → resultado.

Estados do produto a implementar/validar:
recebida, planejada, aguardando usuário, executando, verificando, concluída,
falhou, cancelada e interrompida.

Uma tarefa só termina como concluída se todos os critérios aplicáveis forem satisfeitos.
Reabertura após desconexão deve consultar o estado persistido, sem reenviar efeitos
automaticamente. Cancelamento deve impedir novas etapas; efeitos já realizados devem
ser registrados. Não prometer desfazer automaticamente qualquer ação.

Fluxo de autenticação: GitHub protege o ambiente/porta privada; a conta administrativa
do FreeLLMAPI protege seu painel; a chave unificada autentica o cliente de API.
Sessões em navegadores diferentes não são automaticamente compartilhadas.

Fluxo de erro de modelo:
- 404: conferir modelo disponível e catálogo; não repetir indefinidamente.
- Sem chave utilizável: conferir escopo, ativação e cooldown; não criar chave duplicada.
- 429/cooldown: respeitar o prazo informado e manter limite de tentativas.
- 503/timeout: registrar a falha; não concluir que a chave ou o código estão corretos
  apenas pela conectividade HTTPS; fallback só para opção previamente autorizada.

## 4. Design e uso no celular

Requisitos propostos:
- controles de modelo, chave e estado acessíveis por toque, sem depender de hover;
- layout que exponha ações sem rolagem horizontal obrigatória;
- mensagens distinguindo erro de login, porta privada, cota e falha do provedor;
- campos de senha/chave ocultos por padrão, sem eco em registros;
- alternativa textual para diagnóstico quando capturas não forem utilizáveis;
- indicação de tarefa ativa e horário da última atualização, sem sugerir trabalho
  em segundo plano quando nenhum executor estiver ativo.

Ocorrência observada: o formulário carregou na guia anônima após tela preta na guia normal.
Isso não comprova a causa. Tratamento de armazenamento bloqueado e renderização móvel
são candidatos a reprodução controlada; não corrigir por hipótese sem evidência.

## 5. Backend, dados e permissões

Modelo conceitual proposto; nenhuma tabela ou migração é criada por este documento:
- tarefas: identificador, autor, objetivo, estado, escopo e critérios;
- execuções: tarefa, revisão do código, ferramentas, duração e resultado;
- permissões: recurso, ações permitidas, validade e revogação;
- evidências: referências a diff, testes e hashes, com retenção definida;
- decisões: contexto, alternativas, escolha e motivo;
- credenciais: referência ao segredo, nunca valor em tabelas de tarefas/logs.

Autorização deve ser validada no servidor, incluindo acesso entre usuários e recursos.
Se houver banco com RLS, verificar também políticas efetivas, privilégios e isolamento;
um exemplo de SQL não comprova segurança.

Documentos, páginas, repositórios e saídas de ferramentas são dados não confiáveis.
Não podem ampliar escopo, conceder permissões nem autorizar envio de segredos.
Aprendizado/memória não significa treinamento do modelo nem autorização para compartilhar
conteúdo. Qualquer participação coletiva requer definição separada de consentimento,
minimização, revogação e finalidade antes da implementação.

## 6. Plano de implementação e critérios de aceitação

| Prioridade | Entrega | Evidência exigida |
| --- | --- | --- |
| P0 | Preservar trabalho e preparar ambiente próprio | Inventário, backup validado e plano de migração; sem mover dados reais nesta etapa |
| P1 | Gateway com segredo disponível e modelo permitido | Presença do segredo sem valor; resposta curta válida; provedor/modelo e duração registrados |
| P2 | Contrato executor/gateway | Teste isolado de autenticação, mensagens e ferramentas; bloqueios de erro/fallback |
| P3 | Primeira tarefa completa do agente | Branch isolada, diff pertinente, testes e revisão; sem merge/deploy |
| P4 | Interface móvel e retomada | Controles acessíveis e reprodução dos fluxos de erro/desconexão |
| P5 | Integrações adicionais | Revisão individual, limites, teste e decisão registrada |

Antes de criar ou reativar infraestrutura adicional, verificar cota; não manter dois
ambientes simultâneos sem avaliar consumo. Antes de mover dados reais, obter nova
avaliação e autorização aplicável. Não remover o ambiente de origem.

Aceitação de P1: healthcheck 200 não basta. Confirmar resposta de geração, autenticação
da chave unificada, seleção de modelo e ausência de fallback não autorizado.
Aceitação de P3: o agente deve realmente executar a tarefa, não apenas registrá-la.
Métricas sugeridas: tarefas verificadas/concluídas, duração, falhas por causa,
tentativas por tarefa e consumo reportado quando disponível. Consumo ausente não é zero.

## 7. Matriz de capacidades e evidências conhecidas

Registro das verificações desta conversa; não é monitoramento contínuo nem suíte completa.

| Capacidade | Evidência | Estado |
| --- | --- | --- |
| Adaptador FreeLLMAPI | 18 testes Python passaram no Codespaces; healthcheck HTTP 200 | Testado isoladamente |
| Gemini no gateway | 404 para modelo antigo; depois timeout/503 para 3.8 | Geração bem-sucedida pendente |
| Segredo unificado | Usuário informou salvar; sessão consultada sem variável; Codespaces associado a ruvnet/ruflo | Disponibilidade no ambiente pendente |
| Backup de código sem histórico | ZIP verificado e restauração em diretório separado | Parcial validado |
| Histórico Git completo | Auditoria encontrou possíveis segredos/fixtures | Bloqueado para revisão |
| Bancos SQLite selecionados | Dois snapshots e restaurações isoladas verificados | Parcial validado |
| Demais bancos locais | Três arquivos não reconhecidos como SQLite | Snapshot nativo pendente |
| Claude SEO | 170 testes de HTML/URLs/sitemaps passaram em ambiente isolado, sem proxies herdados | Componentes testados; site não auditado |
| find-skills | Instalação confirmada no usuário do Codespaces para Codex | Disponível nesse ambiente; não altera esta conversa |
| OmniRoute | README consultado; sem prova de instalação/execução | Avaliação isolada pendente |
| Strix/Cloudflare | Avaliação registrada; sem scanner/agenda ativa | Pendente de escopo, executor e custos |
| Reverse API Engineer | Prompt examinado orienta embutir credenciais | Bloqueado até adaptação e teste sanitizado |
| Google ARTEMIS | Nenhum telefone pareado | Pendente |
| Execução completa pelo celular | Pedidos e acesso ao painel ocorreram; tarefa de código pelo agente não comprovada | Pendente |

O número de testes de componentes não deve ser somado e anunciado como cobertura
do projeto inteiro. Nenhuma dessas evidências autoriza declarar o agente pronto.

## 8. Decisões e atualização

D-01: manter o fork e suas capacidades; não reduzir funcionalidades para facilitar migração.
D-02: evitar dependência de instalação no computador pessoal; execução em ambiente controlado.
D-03: um gateway principal por fluxo inicial; comparar alternativas antes da adoção.
D-04: segredos fora do código; não publicar portas/ADB nem ampliar permissões silenciosamente.
D-05: registrar planejado, implementado, testado isoladamente e validado de ponta a ponta
como estados diferentes.
D-06: documentação e testes offline primeiro; nenhuma migração, deploy ou compra autorizada
por este documento.

Cada nova alteração deve citar o requisito, a evidência, as limitações e a decisão afetada.
Revisar a matriz após um teste real ou uma mudança relevante, sem substituir evidência
por contagem de agentes, catálogo de modelos ou promessa de terceiros.
