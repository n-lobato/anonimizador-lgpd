# Corpus de avaliação

Documentos **fictícios** usados para medir quanto o anonimizador acerta. Nenhum
nome, número ou endereço pertence a uma pessoa real; os números de CPF, CNPJ,
PIS e processo foram gerados apenas para ter dígitos verificadores válidos.

## Marcação

Cada dado pessoal está marcado no texto:

    [[PESSOA|Maria da Silva]], CPF [[CPF|526.018.159-06]]

O tipo vem antes da barra e o trecho exato depois. Um `?` antes do tipo indica
dado **opcional**: o programa pode ou não anonimizar (número de processo, CNPJ
de empresa, endereço comercial). Esses trechos não contam como erro em nenhum
dos dois sentidos.

## Grupos

- `desenvolvimento/`: usados para encontrar falhas e ajustar a detecção.
- `validacao/`: nunca usados para ajustar nada. Medem o desempenho em textos
  que o programa "não viu" durante os ajustes.

## Como rodar

    python build/avaliar.py

O relatório mostra, por tipo de dado, quantos foram totalmente cobertos,
quantos vazaram em parte e quantos passaram inteiros, além das marcações
indevidas (falsos positivos).

## Histórico das medições

Um grupo de validação só mede de forma independente **antes** de ser usado
para corrigir o programa. Depois disso, ele vira material de desenvolvimento
e é preciso escrever documentos novos para medir de novo.

| Data | Grupo de validação | v1.0.0 | Após ajustes | Observação |
|---|---|---|---|---|
| nov/2026 | 1º grupo (sentença, e-mails, procuração, certidão, ata escolar, relatório social) | 94% | 94% | medido antes de olhar os erros; depois usado para corrigir e movido para `desenvolvimento/` |
| nov/2026 | 2º grupo, atual (boletim, WhatsApp, laudo, ofício, acordo, lista de presença) | 91% | 93% | número de referência do README; depois usado para corrigir |
| nov/2026 | 2º grupo, em PDF digitalizado (`build/avaliar_ocr.py`) | 80% | 92% | primeira medição com OCR; os e-mails e as quebras de linha foram corrigidos olhando estes documentos |

Para a próxima medição independente, escreva documentos novos em `validacao/`
(e mova os atuais para `desenvolvimento/`) **antes** de alterar a detecção.
O ideal é usar modelos dos documentos que você realmente anonimiza, com
dados trocados por fictícios.
