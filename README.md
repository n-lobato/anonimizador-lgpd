# Anonimizador LGPD

Programa para Windows que encontra e substitui dados pessoais em documentos: petições, decisões, certidões, atas, transcrições, contratos e similares. Tudo roda no seu computador. Nenhum arquivo é enviado para a internet.

Você arrasta arquivos ou pastas para a janela, confere o que foi encontrado e o programa grava uma cópia anonimizada no mesmo formato do original.

```
MARIA APARECIDA DE SOUZA, brasileira, CPF 529.982.247-25, residente na SQS 308, Bloco C...
```

vira

```
[PESSOA_1], brasileira, CPF [CPF_1], residente na [ENDERECO_1]...
```

A mesma pessoa recebe sempre o mesmo código, inclusive quando aparece de outra forma ("Maria Souza", "MARIA:", "a Sra. Souza"). Assim o documento continua legível.

> **Atenção: trocar nomes e números não garante, sozinho, que ninguém consiga descobrir de quem é o documento.** O cargo, o local, as datas e os fatos narrados podem bastar para identificar a pessoa. Pela LGPD (art. 12), o dado só deixa de ser pessoal quando a identificação não é possível por meios técnicos razoáveis. Leia o documento anonimizado inteiro antes de compartilhar e retire à mão o contexto que ainda identifique alguém.

## Download

Baixe o arquivo `AnonimizadorLGPD-windows.zip` na página de [Releases](https://github.com/n-lobato/anonimizador-lgpd/releases), descompacte em qualquer pasta (ou pen drive) e execute `AnonimizadorLGPD.exe`. Não precisa instalar nada. O OCR em português já vem incluído.

O Windows pode mostrar o aviso "O Windows protegeu o computador", porque o executável não tem assinatura digital paga. Clique em **Mais informações** e depois em **Executar assim mesmo**.

### Conferir se o arquivo é o original

O pacote é gerado pelo GitHub Actions a partir do código deste repositório, e não no computador do autor. Cada versão traz, junto do .zip, o arquivo `AnonimizadorLGPD-windows.zip.sha256` com a impressão digital (hash SHA-256) do pacote. Para conferir, abra o PowerShell na pasta do download e rode:

```
Get-FileHash .\AnonimizadorLGPD-windows.zip -Algorithm SHA256
```

O código mostrado deve ser igual ao do arquivo `.sha256` e ao das notas da versão. Se for diferente, não use o arquivo.

## Como usar

Há três jeitos de colocar arquivos na fila:

1. Arrastar arquivos ou pastas para a janela do programa.
2. Arrastar arquivos sobre o ícone do `AnonimizadorLGPD.exe` (ou de um atalho dele).
3. Clicar com o botão direito em arquivos ou pastas e usar **Enviar para > Anonimizador LGPD**. Para criar essa opção, use o menu **Ferramentas > Adicionar ao menu "Enviar para"**.

Depois clique em **Anonimizar**. Com a revisão ligada (recomendado), abre uma tela com tudo o que foi detectado:

- desmarque o que **não** deve ser substituído;
- selecione uma linha para ver o trecho em que o dado aparece;
- use **Unir selecionados** quando duas linhas forem a mesma pessoa;
- use **Adicionar termo** para incluir algo que o programa não reconheceu;
- **Nunca anonimizar** e **Sempre anonimizar** guardam a escolha na sua lista para as próximas vezes.

Os arquivos são gravados na subpasta `anonimizados`, ao lado dos originais, com o sufixo `_anonimizado`. Os originais nunca são alterados. Também é possível escolher outra pasta de saída; nesse caso a estrutura de subpastas é mantida.

## Formatos

| Formato | O que é feito |
|---|---|
| Word (.docx) | Substitui o texto mantendo a formatação. Alcança corpo, tabelas, caixas de texto, cabeçalhos, rodapés, notas, comentários e alterações controladas. Limpa autor, empresa e autores de comentários e revisões. |
| PDF com texto | Tarja definitiva: o texto sob a tarja é **apagado do arquivo**, não apenas coberto. O código é escrito sobre a tarja. Remove metadados, anexos, links e valores de formulários. |
| PDF digitalizado | OCR em português e tarja nos pixels da imagem. |
| Imagens (.png, .jpg, .tif, .bmp) | OCR e tarja; a saída é uma imagem do mesmo tipo, sem os metadados EXIF. |
| Texto (.txt, .md, .csv, .srt, .vtt) | Substituição direta, mantendo a codificação do arquivo. |
| Excel (.xlsx) | Substitui o texto das células e comentários e limpa o autor. |

Formatos antigos (.doc, .xls, .rtf, .odt) devem ser salvos antes como .docx ou .xlsx. Apresentações ainda não são suportadas (exporte para PDF).

## O que é detectado

Nomes de pessoas (inclusive apelidos introduzidos por "vulgo" ou "conhecido como"), CPF, RG e identidade militar, CNH, título de eleitor, PIS/PASEP/NIT, CTPS, passaporte, inscrição na OAB, matrícula (funcional, SIAPE, imóvel), registro em conselho profissional (CRM, CREA, CRESS e outros), CNPJ (inclusive o novo formato alfanumérico), número de processo no padrão CNJ, e-mail, telefone, endereço, CEP, data de nascimento, placa de veículo, agência e conta bancária, cartão de crédito e endereço IP.

Em **Ferramentas > Tipos de dados a procurar** dá para desligar o que não interessa. Número de processo e CNPJ de empresa, por exemplo, costumam ser dados públicos.

### Como os nomes são reconhecidos

Documentos com dígito verificador (CPF, CNPJ, PIS, cartão, processo) são validados matematicamente. Números sem formato próprio (RG, CNH, conta) só são aceitos quando vêm junto da palavra que os identifica.

Para nomes, o programa usa regras explicáveis, sem inteligência artificial na nuvem:

- sequências de palavras com inicial maiúscula (ou em caixa alta), ligadas por "da", "de", "dos" etc.;
- listas de prenomes e sobrenomes brasileiros comuns;
- contexto jurídico: "requerente", "testemunha", "Sr.", "Dra.", ", brasileiro", ", CPF", rótulos de fala em transcrições ("MARIA:");
- profissões e relações antes do nome ("o engenheiro", "a vizinha", "a coordenadora"), linhas de assinatura (nome sozinho na linha, com o cargo logo abaixo), apelidos ("vulgo", "conhecido como") e colunas de tabela seguidas de CPF;
- exclusão de cargos, órgãos, meses, cidades, empresas ("Ltda", "S.A.") e homenagens ("Rua João Pessoa", "Lei Maria da Penha", "Câmara dos Deputados").

### Quanto ele acerta

A detecção foi medida em 18 documentos fictícios, com cada dado pessoal marcado à mão (pasta `tests/corpus`): petições, sentença, termos de audiência, atas, contrato, procuração, certidão de nascimento, e-mails, conversa de WhatsApp, boletim de ocorrência, laudo, ofício e lista de presença.

O número que vale é o da **validação**: 6 documentos escritos depois dos ajustes e que o programa nunca tinha "visto". Nesses textos, **sem a revisão manual**:

| | Versão 1.0.0 | Versão atual |
|---|---|---|
| Todos os dados pessoais (104) | 91% | 93% |
| Só nomes de pessoas (61) | 90% | 90% |
| Falsos positivos | 0 | 0 |

Ou seja: **cerca de 1 em cada 10 nomes passou sem ser detectado**. Os casos que escaparam foram apelidos ("conhecido na região como Magrão"), prenomes soltos em conversas ("o Josias"), um nome raro numa tabela e uma data de nascimento com o rótulo "Nascimento:". Esses casos foram corrigidos depois da medição, mas o número de referência continua sendo o medido antes, porque é o que indica o comportamento em documentos novos.

Cuidados ao interpretar:

- os documentos foram escritos por quem desenvolveu as regras, e os seus documentos reais serão mais variados. Espere um resultado **pior** do que o da tabela;
- a medição usa texto digital. Em PDF digitalizado e imagem, o resultado também depende da qualidade do OCR;
- um dado "coberto" é aquele em que todas as letras e números foram substituídos. Se sobrou parte do dado (por exemplo, um sobrenome), conta como vazamento.

#### Em PDF digitalizado

A mesma medição foi repetida com cada documento transformado num PDF que é só imagem, como um escaneado (200 dpi, sem sujeira nem inclinação). O programa anonimiza com OCR, e o resultado é lido de novo com OCR para ver o que continuou legível.

| | Desenvolvimento (188 dados) | Validação (103 dados) |
|---|---|---|
| Primeira medição | 97% | 80% |
| Depois das correções | 99% | 92% |

A primeira medição revelou dois problemas, depois corrigidos: nomes, endereços e números que quebravam no fim da linha não eram reconhecidos (isso valia para qualquer PDF, não só para os escaneados), e o OCR lê o "@" dos e-mails como "Q", "GQ" ou "(O", e nenhum e-mail era reconhecido. As correções usaram esses mesmos documentos, então o número que indica o comportamento em documentos novos é o da primeira medição. O ponto mais fraco que restou são **e-mails dentro de tabelas** em documentos escaneados.

Num escaneado real, com manchas, carimbos, assinaturas por cima do texto ou papel torto, o resultado tende a ser pior.

Para rodar a medição: `python build/avaliar.py --detalhes` (texto) e `python build/avaliar_ocr.py --detalhes` (PDF digitalizado, precisa do PyMuPDF e dos dados do OCR). Para contribuir com novos casos, veja `tests/corpus/LEIA-ME.md`.

Se o [spaCy](https://spacy.io) com um modelo em português estiver instalado (versão em código-fonte), ele é usado como reforço.

## Limitações (leia antes de usar)

- **Nenhuma detecção automática de nomes é perfeita.** Na medição acima, cerca de 1 em cada 10 nomes passou. Nomes raros, apelidos, prenomes soltos e nomes escritos em minúsculas são os que mais escapam, e algumas palavras podem ser marcadas por engano. Por isso a revisão vem ligada por padrão. Confira o resultado antes de compartilhar.
- Nomes de rua sem número ("Avenida Pau-Brasil") são tratados como endereço, mesmo quando são só referência de lugar. Desmarque na revisão quando não for o caso.
- Texto dentro de imagens incorporadas no Word (assinaturas, carimbos, prints) não é analisado. O programa avisa quando o documento tem imagens.
- No PDF, quando o nome é curto e o código não cabe na tarja, ela fica só preta. A correspondência continua no relatório.
- O OCR depende da qualidade da digitalização. Documentos tortos, manuscritos ou de baixa resolução podem ter falhas. Em escaneados, confira com atenção e-mails e dados dentro de tabelas: o OCR costuma ler o "@" errado.
- Cópias de planilhas podem perder gráficos e imagens (limitação da biblioteca openpyxl).
- Anonimizar com código numerado é, tecnicamente, **pseudonimização**: quem tiver o relatório consegue reverter. Para fins da LGPD (art. 12 e art. 13, § 4º), guarde o relatório separado e protegido, ou não o gere.

## Relatório de-para

Opcionalmente, o programa gera uma planilha `relatorio_anonimizacao_AAAAMMDD_HHMMSS.xlsx` com cada código e o dado original, as ocorrências e os avisos de cada arquivo. **Esse arquivo contém os dados pessoais originais.** Não o envie junto com os documentos anonimizados.

## Linha de comando

O pacote inclui `anonimizador-cli.exe`, útil para lotes grandes ou automação (sem revisão manual):

```
anonimizador-cli.exe "C:\Processos\2026" -o "D:\Anonimizados"
anonimizador-cli.exe peticao.docx --apenas-analisar
anonimizador-cli.exe pasta --tipos PESSOA,CPF,RG,ENDERECO --sem-relatorio
anonimizador-cli.exe --help
```

## Configurações e lista de termos

Ficam em `%APPDATA%\AnonimizadorLGPD` (`config.json` e `termos.json`). A lista de termos pode ser editada em **Ferramentas > Minha lista de termos**:

- **Sempre anonimizar**: nomes ou expressões que devem ser substituídos sempre (com o tipo desejado).
- **Nunca anonimizar**: expressões que não devem ser tocadas (nome do órgão, de uma lei, de um logradouro).

## Rodar a partir do código-fonte

Requer Python 3.10 ou superior.

```
git clone https://github.com/n-lobato/anonimizador-lgpd.git
cd anonimizador-lgpd
pip install -r requirements-dev.txt
python build/baixar_tessdata.py      # dados do OCR em português
python iniciar.py                     # abre a janela
python iniciar.py --cli arquivo.pdf   # linha de comando
python -m pytest                      # testes
python build/avaliar.py --detalhes    # mede os acertos no corpus de teste
pyinstaller anonimizador.spec         # gera o executável em dist/
```

A cada envio para o GitHub, o GitHub Actions roda os testes no Windows e no Linux e gera o executável. Ao criar uma tag `v*` (por exemplo `v1.0.0`), o .zip é publicado automaticamente em Releases.

## Estrutura

```
src/anonimizador/
  deteccao/     padrões, validadores e reconhecimento de nomes
  formatos/     leitura e gravação de docx, pdf, imagens, texto e xlsx
  gui/          janela, tela de revisão e diálogos (PySide6)
  registro.py   códigos e variantes de cada pessoa ou dado
  processador.py  fluxo listar > analisar > revisar > gravar
  relatorio.py  tabela de-para em Excel
  cli.py        linha de comando
tests/          testes automatizados
```

## Licença

GPL-3.0. O programa usa o [PyMuPDF](https://pymupdf.readthedocs.io), distribuído sob AGPL-3.0, para a tarja de PDFs; por isso o código deste projeto também é livre. Os dados de idioma do OCR vêm do projeto [tessdata_fast](https://github.com/tesseract-ocr/tessdata_fast) (Apache-2.0).

Autor: **n-lobato**

### Sobre o uso de inteligência artificial

O desenvolvimento contou com o Claude, assistente de IA da Anthropic, na escrita do código, dos testes e desta documentação. As escolhas sobre como o programa funciona foram feitas pelo autor. O código é aberto justamente para que qualquer pessoa possa conferir o que ele faz, e a medição de acertos acima existe para que ninguém precise confiar só na palavra de quem o fez.

Este programa é uma ferramenta de apoio. A responsabilidade pela conferência do resultado e pelo tratamento adequado dos dados é de quem o utiliza.
