# Preparação de custódia local — experimental POSIX

key_custody.py prepara duas chaves Fernet geradas pela biblioteca cryptography,
em diretório novo modo700 e arquivos modo600. generate recusa diretório já
existente. check valida os arquivos sem imprimir segredos. load é API para
chamador confiável e retorna as chaves em memória; não expor essa API ao modelo.

Executar apenas em Linux/POSIX e filesystem compatível. Não foi validado no
Windows. O diretório pai deve ser confiável, privado e persistente, sem mudanças
de caminhos por terceiros. O programa não impõe essa propriedade ao pai.
Não usar Codespace/scratch como única guarda nem executar em PC compartilhado.

Exemplo ilustrativo: substituir o caminho somente após escolher local seguro
sob controle do usuário. O exemplo NÃO foi executado com chaves de produção:

```bash
python3 tools/portable-runtime/key_custody.py generate --directory /local-seguro/agent-keys
python3 tools/portable-runtime/key_custody.py check --directory /local-seguro/agent-keys
```

## Proteções e limites

Os arquivos são abertos com dir_fd e O_NOFOLLOW. load verifica proprietário,
permissões sem acesso de grupo/outros, arquivo regular com um link, tamanho e
formato de chave. generate usa criação exclusiva e fsync dos arquivos/diretório.
Uma falha parcial deixa o diretório privado para inspeção manual; não apaga nem
substitui chaves automaticamente. Não repetir generate sobre ele como correção.

As chaves ficam EM CLARO nos arquivos. Modo600 não é criptografia, não impede
administrador ou malware e depende das garantias do filesystem/host. A escolha
de armazenamento protegido e recuperação independente continua obrigatória.
Não salva em gerenciador de senhas, não faz upload, não sincroniza, não oferece
rotação ou revogação. Nunca colocar chaves em Git, chat, logs ou no mesmo pacote
de backup. A posse das duas chaves permite ler/forjar dados; perder uma pode
tornar o backup irrecuperável. generate não garante persistência do filesystem.

## Evidência em 25/10/2026

42 testes passaram. Três novos testes verificam geração temporária, reabertura,
check por subprocesso sem segredos no stdout/stderr, uso das chaves em ida/volta
de backup, preservação ao tentar gerar novamente e rejeição de permissões abertas,
symlink, chave ausente e codificações equivalentes da mesma chave. Todos os segredos são descartáveis e sintéticos.
Nenhuma chave de produção foi criada ou entregue. Nenhum serviço pago ativado.

## Limite antes de habilitar dados privados

Falta selecionar e validar um local persistente realmente controlado pelo
usuário, preparar recuperação independente das duas chaves e ensaiar no ambiente
de destino. Fazer isso em scratch criaria risco de perda, portanto não foi feito.
Não considerar o controle19 de RECOVERY-GATE.md concluído por estes testes.
Não migrar dados privados. O protótipo continua limitado à soma e recibos.
