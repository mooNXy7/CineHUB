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

## Fase 3 — Health Check

O mesmo pipeline agora verifica fontes remotas antes de considerá-las saudáveis.

- mede latência;
- registra HTTP status;
- aplica retries;
- rejeita respostas vazias;
- valida o formato básico de M3U/M3U8 e XML/EPG quando o tipo estiver declarado;
- mantém contagem de falhas consecutivas;
- classifica a fonte como healthy, unknown, degraded ou offline;
- não remove uma fonte após uma única falha.

A política atual é:

- primeira falha → unknown;
- segunda falha consecutiva → degraded;
- terceira ou mais → offline;
- sucesso → healthy e zera a sequência de falhas.

O Health Check valida a disponibilidade da fonte, não cada stream individual. A validação/fallback por entidade será aprofundada nas fases 4 e 5.

## Compatibilidade

Nesta primeira implementação, o pipeline não substitui CineHUB_WEB/dados, não reescreve assets do Mobile e não modifica os assets da TV.

Isso é intencional. Health check real, normalização, multi-source/fallback e publicação dos dados processados entram nas fases seguintes.

## SaimoPlayer

Foram aproveitadas ideias conceituais observadas no SaimoPlayer, como atualização automatizada, validação de fontes, geração separada de dados e tolerância a múltiplas fontes. Nenhum script ou estrutura foi copiado literalmente.

## Sem mudanças inúteis

Se as fontes permanecerem iguais, o workflow imprime:

NO CHANGES

e não cria commit.

## Fase 4 — Normalização e deduplicação

O Data Engine agora possui um normalizador central de canais em `CineHUB_Data/tools/normalize_channels.py`.

A etapa:

- lê fontes de canais habilitadas, locais e remotas;
- normaliza nomes, acentos, pontuação e marcadores de qualidade;
- cria IDs estáveis derivados da identidade canônica;
- mantém aliases encontrados nas fontes;
- agrega várias URLs/fontes na mesma entidade;
- preserva prioridade, logo, grupo, idioma, país e tvg-id quando disponíveis;
- deduplica registros sem apagar fontes alternativas;
- não processa fontes de catálogo VOD como canais;
- preserva o último dado conhecido de uma fonte que esteja temporariamente indisponível.

A saída é `CineHUB_Data/normalized/channels.json`.

Importante: esta fase ainda não substitui os dados consumidos pelo WEB, Mobile ou TV. O índice normalizado é produzido em paralelo e será conectado ao fluxo comum nas fases seguintes, depois de validação.

Exemplo conceitual:

```text
Canal X
Canal-X HD
CANAL X [HD]
      ↓
normalizer
      ↓
channel-a1b2c3...
      ├── Fonte A
      ├── Fonte B
      └── Fonte C
```
