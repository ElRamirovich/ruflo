# Preparação de backup externo criptografado

Estado em 2026-10-24: planejamento operacional; envio externo e agendamento DESATIVADOS.
O usuário pretende contratar Google One de 200 GB. Compra, ativação e espaço livre não foram verificados.
Google One fornece armazenamento compartilhado com Gmail/Fotos, não processamento do agente.

## Escopo

Manter o backup local independente. Adicionar posteriormente uma etapa opcional de criptografia e transporte para uma pasta privada do Google Drive. Nenhuma dependência de Drive ou criptografia deve ser necessária para criar/verificar/restaurar o backup local existente.
Não copiar banco ativo por cópia simples, não enviar credenciais em claro, não apagar originais e não alterar a retenção automaticamente.

## Fluxo e critérios de aprovação

1. Criar o ZIP local com backup.py e verificar seu manifesto SHA-256. Registrar explicitamente se o histórico Git está ausente. Bancos exigem snapshots consistentes e revisão individual.
2. Validar a ferramenta de criptografia com dados fictícios: criptografar, descriptografar, comparar hashes, rejeitar conteúdo adulterado e chave incorreta/ausente. Saída parcial de descriptografia nunca deve ser publicada ou usada após erro.
3. Definir uma chave de recuperação sob controle do usuário. Preferir criptografia assimétrica: o executor recebe somente a chave pública; a chave privada fica fora do repositório, fora do Codespace e fora da pasta de backups. Validar a impressão digital por canal confiável. Não gerar a única chave real em ambiente temporário do assistente.
4. O usuário deve manter uma cópia recuperável da chave privada em local seguro independente. Não pedir senha ou chave privada pelo chat. A validação com chave fictícia não prova recuperação da chave real.
5. Confirmar conta, pasta privada, permissões e espaço livre real no Drive. Usar o menor escopo de autorização suficiente. Não ampliar credenciais existentes sem revisar seus escopos. Não incluir IDs de conta/pasta ou credenciais neste documento público.
6. Após revisão do escopo do arquivo, enviar somente o pacote criptografado. Usar nome opaco; não enviar manifesto de caminhos em claro. Tamanho, horário e metadados da transferência continuam visíveis ao provedor.
7. Baixar a cópia enviada e comparar SHA-256 do pacote cifrado. Isso comprova igualdade dos bytes, não recuperabilidade.
8. Em ambiente autorizado separado, descriptografar com a chave real, verificar o ZIP com backup.py e restaurar em diretório novo. Só então registrar recuperação externa validada.

## Retenção e capacidade

200 GB é uma intenção de plano, não capacidade livre confirmada. Medir o tamanho de cada pacote e a cota restante antes de qualquer envio. Reservar margem para Gmail/Fotos e novas versões. Nenhuma exclusão automática ou compra de espaço. Falta de espaço interrompe o envio sem apagar cópias locais.
Não usar sincronização bidirecional de diretórios ativos como substituto do backup. Não habilitar execução recorrente antes da primeira recuperação externa validada.

## Limites e dados ainda pendentes

- Backups locais anteriormente verificados não incluem histórico Git completo; não declarar proteção integral.
- Volume e chave de criptografia interna do FreeLLMAPI exigem plano próprio de recuperação. Este fluxo não os inclui automaticamente.
- Criptografar no Codespace protege a cópia armazenada no Drive, mas não esconde o conteúdo original do ambiente que o processa.
- APIs de IA externas recebem o conteúdo enviado para inferência. Criptografia de backup não muda essa condição.
- O componente criptográfico é opcional e usa formato/ferramenta estabelecidos; não criar algoritmo próprio.

## Evidência desta preparação

O ambiente temporário do assistente possui GnuPG, mas a geração de chave exclusivamente fictícia falhou porque gpg-agent não iniciou (exit status 2). Nenhum teste de ida e volta foi concluído. Nenhuma chave de recuperação real foi criada, nenhum arquivo do projeto foi criptografado e nenhum dado foi enviado ao Drive. Repetir o teste em ambiente compatível antes de implementar ou habilitar o envio.
