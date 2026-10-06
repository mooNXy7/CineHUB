# CineHUB Data Engine — Data Layer

Esta pasta é a camada central de dados do CineHUB.

## Objetivo

Separar progressivamente:

**APLICAÇÃO ≠ DADOS ≠ FONTES ≠ PROCESSAMENTO**

A Data Layer não substitui os dados existentes do CineHUB nesta fase. Ela cria uma estrutura estável para que as próximas etapas possam migrar o processamento sem quebrar WEB, Mobile ou TV.

## Estrutura

```text
CineHUB_Data/
├── sources/       # registro das fontes e configurações
├── catalog/       # contratos e índices do catálogo
├── epg/           # contratos e dados do EPG
├── manifests/     # manifestos de distribuição
├── status/        # estado e observabilidade dos dados
├── metadata/      # contratos de metadados
└── providers/     # contratos dos providers
```

## Regra desta fase

Os dados atuais continuam nos locais que as aplicações já utilizam.

Nenhum arquivo de:

- CineHUB_WEB
- CineHUB_Mobile_Android
- CineHUB_TV_Android

é movido ou substituído pela Data Layer nesta etapa.

A Data Layer passa a funcionar como **fonte de organização e contrato**, preparando as próximas fases.

## Fonte atual

O registro inicial foi derivado da configuração existente em:

`CineHUB_WEB/dados/listas.json`

e mantém referências para os dados já existentes, em vez de duplicá-los.

## Próximas etapas

1. atualização automática;
2. health check;
3. normalização;
4. multi-source;
5. catálogo VOD;
6. EPG Engine;
7. publicação e observabilidade.
