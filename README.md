# BIQMapa

Aplicativo para organizar o mapeamento de quadras e lotes de Biquinhas/MG e consultar os dados dos imóveis. Desenvolvi para o trabalho dos setores de Tributos e Engenharia da Prefeitura.

O uso é individual, com os dados salvos no próprio computador. A interface reúne o mapa, a consulta de imóveis e os históricos de alterações.

## Instalação

Baixe o instalador do BIQMapa na página de [versões](https://github.com/lucaspfvr/biqmapa/releases). Execute o instalador e abra o BIQMapa pelo atalho criado na área de trabalho. Não precisa instalar Python nem usar terminal.

Requisitos: Windows 10 ou 11, 64 bits. O instalador ainda não tem assinatura digital.

## Primeiro uso

O aplicativo começa sem imóveis. Em **Configurações → Importar dados**, selecione seu arquivo JSON de imóveis (.json), o mesmo arquivo já utilizado no setor. A importação é direta pelo arquivo; não depende de outro programa instalado. Confira os registros novos e as alterações antes de aplicar a importação. Também é possível importar CSV.

O CIM identifica o imóvel nas atualizações. Quadra e lote são comparados sem zeros à esquerda. Duplicidades aparecem para conferência e não impedem selecionar o cadastro correto pelo CIM. Um imóvel ausente no relatório não é excluído automaticamente.

Para continuar um trabalho feito no protótipo HTML, exporte o backup naquele arquivo e restaure em **Configurações → Backup** no aplicativo.

## Mapa

O satélite carrega pela internet. O mapa de ruas de Biquinhas funciona offline. Cadastros, fotos, histórico e desenhos ficam no computador; os dados dos proprietários não são enviados ao fornecedor das imagens nem ao GitHub.

Desenhe a quadra e depois vincule cada lote ao cadastro correspondente. Durante o desenho, use Espaço + arrastar ou o botão direito para mover o mapa. A roda do mouse controla o zoom. O último ponto fica ligado ao primeiro para facilitar o fechamento.

As demarcações servem para localização e referência visual. Não têm precisão de levantamento cadastral.

## Dados e backup

A base fica em `%LOCALAPPDATA%\BIQMapa\biqmapa.sqlite3`, fora da pasta de instalação. Atualizações e a desinstalação preservam essa pasta.

Antes da primeira alteração de cada dia, o aplicativo faz uma cópia local do banco. São mantidas as últimas 30 cópias na pasta `backups`. Exporte também backups JSON e mantenha uma cópia fora do computador.

Não coloque relatórios reais, bancos, backups ou fotos de imóveis neste repositório. Os testes usam dados fictícios. O histórico incluído em backups antigos continua disponível quando eles são restaurados.

## Desenvolvimento

```powershell
py -3.13 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements-build.txt
python main.py
```

Testes:

```powershell
python -m unittest discover -s tests -v
node tests/frontend.cjs
python scripts/smoke.py
```

Para montar o instalador no Windows, instale o NSIS e execute:

```powershell
python scripts/build_windows.py
```

O GitHub Actions executa os testes, monta o aplicativo e gera o instalador a cada atualização da branch `main`. A publicação em Releases acontece depois que a instalação silenciosa e a abertura do programa empacotado passam na verificação automática.

## Estrutura

- `biqmapa/desktop.py`: janela, impressão, downloads e integração com a interface.
- `biqmapa/storage.py`: banco SQLite e cópias de segurança.
- `biqmapa/assets/`: interface, mapa de ruas, brasão e imagem ilustrativa.
- `installer/`: instalador e desinstalador.
- `scripts/`: montagem e verificação do aplicativo.
- `tests/`: persistência e importação.

Desenvolvido por Lucas Cézar de Oliveira.

## Imagem local 4K

Na primeira preparação com conexão, o aplicativo solicita uma imagem estática de Biquinhas ao mesmo serviço do satélite. A exportação tem 4096 × 3106 pixels, o limite de largura informado pelo serviço. A imagem fica na pasta de dados local e também acompanha os backups JSON. Não é enviada ao GitHub nem incluída no repositório.

O botão **Imagem local** abre essa cópia com a mesma referência geográfica do mapa online, preservando quadras, lotes, posição e zoom. A primeira preparação precisa de internet. Depois disso ela funciona sem conexão, inclusive após fechar e reabrir o programa. Aumentar o zoom não cria detalhes além dos pixels disponíveis; o satélite online pode ter mais detalhe que a exportação de toda a cidade.

A cópia é uma representação estática para uso interno, com créditos ao fornecedor. Não é um pacote de tiles e não é redistribuída junto ao instalador. A opção antiga de imagem personalizada continua disponível quando já há uma base ou contornos nesse espaço.

A primeira preparação da imagem local pode demorar até dois minutos, conforme a resposta do serviço de imagens. A navegação continua disponível durante a preparação.


## Interface

O menu do cabeçalho reúne configurações, importação, backup, guia de uso e informações sobre o BIQMapa. As abas Mapa, Imóveis e Histórico dão acesso às telas principais. No mapa, o painel esquerdo organiza quadras e lotes; o resumo do imóvel abre à direita. Os indicadores gerais do acervo ficam em Imóveis.
