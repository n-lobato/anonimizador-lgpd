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

## Download

Baixe o arquivo `AnonimizadorLGPD-windows.zip` na página de [Releases](https://github.com/n-lobato/anonimizador-lgpd/releases), descompacte em qualquer pasta (ou pen drive) e execute `AnonimizadorLGPD.exe`. Não precisa instalar nada. O OCR em português já vem incluído.

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

Nomes de pessoas, CPF, RG e identidade militar, CNH, título de eleitor, PIS/PASEP/NIT, CTPS, passaporte, inscrição na OAB, matrícula (funcional, SIAPE, imóvel), CNPJ (inclusive o novo formato alfanumérico), número de processo no padrão CNJ, e-mail, telefone, endereço, CEP, data de nascimento, placa de veículo, agência e conta bancária, cartão de crédito e endereço IP.

Em **Ferramentas > Tipos de dados a procurar** dá para desligar o que não interessa. Número de processo e CNPJ de empresa, por exemplo, costumam ser dados públicos.

### Como os nomes são reconhecidos

Documentos com dígito verificador (CPF, CNPJ, PIS, cartão, processo) são validados matematicamente. Números sem formato próprio (RG, CNH, conta) só são aceitos quando vêm junto da palavra que os identifica.

Para nomes, o programa usa regras explicáveis, sem inteligência artificial na nuvem:

- sequências de palavras com inicial maiúscula (ou em caixa alta), ligadas por "da", "de", "dos" etc.;
- listas de prenomes e sobrenomes brasileiros comuns;
- contexto jurídico: "requerente", "testemunha", "Sr.", "Dra.", ", brasileiro", ", CPF", rótulos de fala em transcrições ("MARIA:");
- exclusão de cargos, órgãos, meses, cidades e homenagens ("Rua João Pessoa", "Lei Maria da Penha").

Se o [spaCy](https://spacy.io) com um modelo em português estiver instalado (versão em código-fonte), ele é usado como reforço.

## Limitações (leia antes de usar)

- **Nenhuma detecção automática de nomes é perfeita.** Nomes raros, apelidos ou nomes escritos em minúsculas podem passar, e algumas palavras podem ser marcadas por engano. Por isso a revisão vem ligada por padrão. Confira o resultado antes de compartilhar.
- Texto dentro de imagens incorporadas no Word (assinaturas, carimbos, prints) não é analisado. O programa avisa quando o documento tem imagens.
- No PDF, quando o nome é curto e o código não cabe na tarja, ela fica só preta. A correspondência continua no relatório.
- O OCR depende da qualidade da digitalização. Documentos tortos, manuscritos ou de baixa resolução podem ter falhas.
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

Este programa é uma ferramenta de apoio. A responsabilidade pela conferência do resultado e pelo tratamento adequado dos dados é de quem o utiliza.
