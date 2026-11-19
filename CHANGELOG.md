# BIQMapa 0.7.2 — em revisão

- Seletor de base próprio, com uma única opção selecionada e indicação visual distinta do estado de passar o mouse.
- Ordenação dos trechos de satélite por resolução real para impedir que imagens mais borradas cubram trechos nítidos.
- Consideração da densidade de pixels da tela ao escolher o nível do satélite.
- Imagem local estática em 4K, preparada uma vez com internet e mantida fora da pasta de instalação e do repositório.
- Mesma referência geográfica ao alternar entre imagem local e satélite; os contornos não são deslocados nem convertidos.
- Backup JSON inclui a base local preparada.
- Alterações em branch e PR, aguardando o comentário APROVADO antes da integração à main.

# BIQMapa 0.7.1 para Windows

- Corrige o acesso da janela local às imagens do satélite utilizado no protótipo HTML.
- Move o resumo do mapa para o menu superior e aproveita a altura antes ocupada pelo cabeçalho da página.
- Mantém os trechos carregados durante a sessão ao navegar entre as telas e em quedas curtas de conexão.
- Acrescenta uma opção para tentar carregar o satélite novamente.
- Verifica o carregamento real das imagens no Windows antes de publicar o instalador.
- Preserva o banco e os backups da versão 0.7.0.

# BIQMapa 0.7.0 para Windows

- Primeira versão instalável para uso individual.
- Base inicial vazia, com importação direta do arquivo JSON de imóveis ou CSV.
- Interface da versão 0.7.0: painel de quadras e lotes, ficha do imóvel, desenho e edição de contornos.
- Banco SQLite local, separado da instalação.
- Backup JSON compatível com o protótipo e cópias automáticas do banco.
- Satélite online e mapa de ruas offline de Biquinhas.
- Instalador para Windows 10/11 de 64 bits, sem necessidade de instalar Python.

Esta é a primeira versão de instalação. A conferência final dos fluxos de trabalho será feita durante o uso no setor. O instalador ainda não possui assinatura digital.
