# Integração HTTP local — 2026-10-25

## Escopo

Validação do cliente portátil em processo separado contra servidor HTTP efêmero
no IP literal 127.0.0.1. Conteúdo, modelo e chave exclusivamente fictícios.
A resposta é programada pelo teste; nenhum modelo de IA foi executado.

## Execução

python3 -m unittest discover -s tools/portable-runtime -p 'test_*.py' -v

Resultado observado no ambiente do assistente: 11 testes passaram (8 unitários e
3 métodos de integração HTTP; o método de redirecionamento também testa 429).
O teste requer autorização do ambiente para abrir uma porta de loopback.
Não instala dependências nem altera serviços já existentes.

## Verificações da integração

- Cliente iniciado por subprocesso Python usando seu próprio arquivo.
- Nenhum ambiente de autenticação do pai é repassado: somente confirmação local,
  chave fictícia e proxies locais deliberadamente indisponíveis. SYSTEMROOT é
  preservado no Windows quando presente; execução Windows ainda não foi testada.
- Contrato POST /v1/chat/completions e JSON de resposta confirmados.
- Proxy de ambiente não desvia a chamada do cliente.
- HTTP 302 e 429 retornam erro, sem seguir redirecionamento ou tentar novamente.
- Resposta acima de 64 KiB é rejeitada sem publicar seu corpo.
- Servidores efêmeros são encerrados ao final de cada ensaio.

## Dependências ainda existentes

Este caminho não importa Ruflo ou FreeLLMAPI e não depende de Codespaces.
Entretanto precisa de Python e, para inferência real, de um servidor/modelo.
Não substitui ferramentas, memória, coordenação, gestão de permissões ou backup.

O ambiente do assistente inspecionado não contém Ollama, llama-server, Docker,
PyTorch, Transformers, llama_cpp ou huggingface_hub. Não foi instalado ou
baixado modelo, ativado serviço, contratado recurso ou consumida cota Colab/API.

## Próximo marco

Validar uma solicitação fictícia em um modelo real com licença e recursos
compatíveis, num destino de execução autorizado com condições de custo conhecidas.
A migração ao computador pessoal continua pausada por decisão do usuário.
Não declarar inferência funcional, operação permanente, independência completa,
criptografia ponta a ponta implantada ou ausência absoluta de risco com base
nesta prova de transporte HTTP.
