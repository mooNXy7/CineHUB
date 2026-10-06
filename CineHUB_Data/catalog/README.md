# CineHUB Data Engine — VOD Catalog

A Fase 6 cria uma camada VOD processada sem substituir o catálogo existente.

## Fonte

A entrada continua sendo o catálogo atual em:
`CineHUB_WEB/dados/conteudo/catalogo/*.m3u8`

Nenhum arquivo do WEB, Mobile ou TV é removido ou reescrito.

## Saídas

- `movies.index.json` — índice compacto de filmes.
- `series.index.json` — índice compacto de séries.
- `featured.json` — seleção leve para áreas de destaque.
- `trending.json` — seleção leve para áreas de descoberta.
- `releases.json` — seleção leve de lançamentos.
- `metadata.json` — contrato, estatísticas e timestamp da geração.

Cada item possui um ID estável derivado de tipo + título + URL, além de título, grupo, logo, URL e arquivo de origem.

## Separação

```text
CATÁLOGO EXISTENTE
      ↓
build_vod_catalog.py
      ↓
CINEHUB DATA ENGINE
      ├── índices de filmes
      ├── índices de séries
      └── índices leves da Home
```

O cliente não precisa varrer dezenas de milhares de entradas apenas para montar a Home.

## Compatibilidade

A integração com os aplicativos fica propositalmente para uma etapa posterior. Nesta fase, o Data Engine produz os dados processados em paralelo; portanto não há alteração obrigatória no APK nem no player atual.

## Segurança

O builder não consulta serviços externos nem expõe tokens. URLs existentes são tratadas como dados de catálogo e não são executadas durante a geração.
