# BIQMapa

Aplicativo para organizar o mapeamento de quadras e lotes de Biquinhas/MG e consultar os dados dos imóveis. Desenvolvi para o trabalho dos setores de Tributos e Engenharia da Prefeitura.

A versão Windows parte da interface 0.7.0, com o painel lateral de quadras e a ficha do imóvel. O uso é individual, com os dados salvos no próprio computador.

## Instalação

Baixe `BIQMapa-Setup-0.7.1.exe` na página de [versões](https://github.com/lucaspfvr/biqmapa/releases). Execute o instalador e abra o BIQMapa pelo atalho criado na área de trabalho. Não precisa instalar Python nem usar terminal.

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
