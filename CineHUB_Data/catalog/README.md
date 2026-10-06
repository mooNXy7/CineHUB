# Catalog Data Contract

O catálogo atual permanece em `CineHUB_WEB/dados/conteudo/`.

Nesta fase, esta pasta define somente o contrato para a futura camada de catálogo.

## Datasets previstos

- filmes;
- séries;
- temporadas;
- episódios;
- destaques;
- lançamentos;
- índices;
- metadados.

## Regra

Dados brutos e dados processados deverão ser separados.

A aplicação deve consumir índices/chunks adequados em vez de carregar o catálogo inteiro sem necessidade.

A migração do catálogo atual para este contrato será feita em fases posteriores, com validação antes de alterar os consumidores.
