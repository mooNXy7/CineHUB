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


## Fase 5 — Multi-source + fallback

O Data Engine agora possui um resolvedor central em `CineHUB_Data/tools/resolve_sources.py`.

Ele transforma as múltiplas fontes de cada entidade normalizada em uma cadeia de fallback determinística, usando:

1. estado do Health Check;
2. prioridade da fonte;
3. qualidade declarada;
4. ordem estável como desempate.

A saída é `CineHUB_Data/resolved/channels.json`.

### Política de fallback

- no máximo 4 tentativas por entidade;
- fontes `healthy` vêm antes de `degraded`, `unknown` e `offline`;
- fontes offline não são apagadas: podem permanecer como último recurso para recuperar automaticamente quando voltarem;
- não existem retries infinitos;
- falhas ficam registradas no estado da fonte;
- Referer e User-Agent presentes no M3U são preservados para o player.

Exemplo:

```text
Canal X
  ↓
Resolver
  ├─ Fonte A · healthy · prioridade 1
  ├─ Fonte B · healthy · prioridade 2
  ├─ Fonte C · degraded · prioridade 3
  └─ Fonte D · offline · último recurso
```

### Compatibilidade

A Fase 5 é adicionada de forma paralela. O WEB, Mobile e TV continuam usando seus fluxos atuais de reprodução e listas. O novo manifesto resolvido fica disponível para a futura integração comum, sem obrigar atualização de APK nesta etapa.

A implementação aproveita o conceito já existente no CineHUB de `sources[]` e o princípio observado no SaimoPlayer de manter várias fontes por canal e tentar a próxima quando a anterior falhar. Não foi copiado código do SaimoPlayer.

### Pipeline

O workflow diário agora executa:

```text
Health Check
     ↓
Normalizer
     ↓
Multi-source Resolver
     ↓
Resolved Manifest
     ↓
Commit somente se CineHUB_Data mudar
```
