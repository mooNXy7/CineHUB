# CineHUB Data Engine — Data Layer

A Data Layer centraliza contratos e referencias de dados sem substituir os caminhos usados pelas aplicações.

## Fase 2 — Atualização automática

O pipeline diário:

1. lê CineHUB_Data/sources/registry.json;
2. busca fontes remotas habilitadas;
3. aplica timeout e retries controlados;
4. calcula SHA-256 do conteúdo;
5. registra fingerprint e resultado da coleta;
6. atualiza manifest/status somente quando houver mudança relevante;
7. cria commit apenas quando CineHUB_Data realmente mudou.

O workflow também pode ser executado manualmente.

## Compatibilidade

Nesta primeira implementação, o pipeline não substitui CineHUB_WEB/dados, não reescreve assets do Mobile e não modifica os assets da TV.

Isso é intencional. Health check real, normalização, multi-source/fallback e publicação dos dados processados entram nas fases seguintes.

## SaimoPlayer

Foram aproveitadas ideias conceituais observadas no SaimoPlayer, como atualização automatizada, validação de fontes, geração separada de dados e tolerância a múltiplas fontes. Nenhum script ou estrutura foi copiado literalmente.

## Sem mudanças inúteis

Se as fontes permanecerem iguais, o workflow imprime:

NO CHANGES

e não cria commit.
