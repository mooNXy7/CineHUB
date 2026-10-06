# Sources Registry

O arquivo `registry.json` é o primeiro registro central das fontes do CineHUB.

Ele foi criado a partir das fontes já utilizadas pelo projeto.

## Importante

Este registro **não substitui ainda** `CineHUB_WEB/dados/listas.json`.

Durante a Fase 1, os dois coexistem:

- `listas.json` continua sendo consumido pelo sistema atual;
- `registry.json` representa a nova camada central;
- nas próximas fases, o pipeline poderá passar a gerar/validar os dados consumidos pela aplicação.

Isso evita uma migração brusca.
