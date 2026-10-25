# Inferência local real — 25/10/2026

## Resultado

O cliente independente chamou um processo llama-server com modelo GGUF local
e recebeu texto gerado de verdade. Não foram usados Ruflo, FreeLLMAPI, SDK de
provedor ou chave de serviço externo no caminho da inferência. O processo foi
encerrado ao final. Este ensaio ocorreu no ambiente temporário de desenvolvimento,
não no computador Windows do usuário nem no Codespace original.

Uma segunda execução retornou `local_inference_smoke_failed` (saída 2); o erro
genérico não permite atribuir a causa. Portanto a estabilidade ainda não foi
comprovada. A suíte automatizada posterior passou em 14 testes.

Primeira execução: 14,844 segundos incluindo inicialização, prompt público
`What is two plus two? Answer briefly.`. A resposta não deu o resultado correto
e apresentou explicações incorretas sobre funções de programação. Portanto:

- Integração com inferência local: comprovada neste ambiente.
- Qualidade do modelo para agente: reprovada neste ensaio simples.
- Memória, ferramentas e coordenação independentes: ainda não implementadas aqui.

Não promover esse modelo a substituto do agente. O objetivo deste modelo pequeno
é exercitar o caminho técnico com recursos limitados. Nenhum conteúdo pessoal
foi incluído. Nenhuma API paga, GPU alugada ou plano foi ativado. Os downloads
usaram a rede; a inferência foi configurada offline, sem monitoramento de egress
ou sandbox de rede que permita afirmar isolamento absoluto.

## Componentes fixados

- Runtime: ggml-org/llama.cpp, release b11871, versão reportada 0.7.0-dev,
  commit b3fa69955, licença MIT.
- Arquivo oficial: https://github.com/ggml-org/llama.cpp/releases/download/b11871/llama-b11871-bin-ubuntu-x64.tar.gz
- Arquivo: 22.490.492 bytes; SHA-256
  `b0a29cc015275b751c0323875db007583b3bd1cb31e921087dd3cd3d37d5eef9`.
- Executável llama-server extraído: SHA-256
  `e48cc61e37e1ed15649f8c39789df5eb03d2e549df1f2c0b1835a26378a72b41`.
- Modelo original: HuggingFaceTB/SmolLM2-135M-Instruct, Apache-2.0.
- Quantização: unsloth/SmolLM2-135M-Instruct-GGUF, revisão
  `9e6855bc4be717fca1ef21360a1db4b29d5c559a`, Apache-2.0.
- Arquivo: https://huggingface.co/unsloth/SmolLM2-135M-Instruct-GGUF/resolve/9e6855bc4be717fca1ef21360a1db4b29d5c559a/SmolLM2-135M-Instruct-Q4_K_M.gguf
- Modelo: 105.454.144 bytes; SHA-256
  `ed5fa30c487b282ec156c29062f1222e5c20875a944ac98289dbd242e947f747`.

Hashes foram comparados aos metadados dos distribuidores antes da execução.
Isso verifica integridade, não ausência de vulnerabilidades. As bibliotecas
compartilhadas devem vir do mesmo arquivo oficial verificado; o script verifica
o executável e o modelo, não todas as bibliotecas carregadas. Não redistribuímos
os binários ou pesos neste repositório; preservar as licenças ao distribuí-los.

## Reprodução explícita

Requer Linux x86_64 compatível e Python 3.11+ para o ensaio (o cliente continua
Python 3.10+). Baixar e verificar os arquivos acima em uma pasta isolada e
extrair o runtime completo, preservando suas bibliotecas e licenças. O script
não baixa arquivos, instala pacotes ou altera configurações globais.
Executar como CLI isolada, não importar em aplicação multithreaded: o limite
de recursos usa preexec_fn. A saída capturada é limitada pelo cliente revisado,
não pelo mecanismo capture_output do subprocesso. Arquivos não regulares e
maiores que 200 MB são rejeitados antes do hash; não modificar arquivos ou
bibliotecas entre a verificação e a execução.

```bash
python3 tools/portable-runtime/live_smoke.py \
  --server /caminho/revisado/llama-b11871/llama-server \
  --model /caminho/revisado/SmolLM2-135M-Instruct-Q4_K_M.gguf
```

Usa apenas a pergunta sintética fixa; não aceita prompts privados. Configura
duas threads, CPU, contexto 1024, um slot, 256 tokens, loopback, modo offline,
interface web desligada, ambiente mínimo e chave efêmera em arquivo temporário
modo 600. Limites Linux: 2 GiB de espaço virtual e 90 segundos de CPU; prazo de
inicialização de aproximadamente 30 segundos e cliente de 25 segundos. Finalização
termina o servidor, aguarda e força encerramento se necessário. Não é um serviço
contínuo e não é uma sandbox contra executáveis maliciosos. A porta efêmera tem
uma pequena corrida de bind; usar somente em ambiente local confiável.

Sucesso significa resposta textual, não correção: o recibo declara
`agent_quality_validated: false`. Erros não imprimem logs, prompts externos ou
chaves. Testes de falha verificam bloqueio por hash e limpeza após timeout.

Próximo requisito para substituir dependências: selecionar e avaliar um modelo
capaz em tarefas reais de código e ferramentas, depois conectar um executor
com permissões limitadas. Uma demonstração pequena não aprova essa substituição.
