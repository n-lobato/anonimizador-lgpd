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
