# CineHUB Data Engine — publicação

A publicação final do Data Engine é gerada por `tools/publish_data.py`.

## Fluxo

`sources → health check → normalization → resolver → VOD indexes → EPG → publication`

O pacote público fica em `CineHUB_WEB/data-engine/`. Isso é intencional: o Cloudflare Pages já publica `CineHUB_WEB`, então a publicação de dados pode acompanhar o deploy WEB sem criar um segundo aplicativo ou exigir APK novo.

## Contrato público

- `manifest.json` — índice e hashes dos datasets publicados.
- `status-public.json` — observabilidade consolidada.
- `status.json` — status bruto do Data Engine.
- `sources.json` — registro de fontes.
- `channels/normalized.json` — entidades normalizadas.
- `channels/resolved.json` — entidades com fallback/múltiplas fontes.
- `catalog/*.json` — índices VOD pré-processados.
- `epg/*` — EPG processado quando disponível.

Os caminhos são relativos a `/data-engine/` e podem ser consumidos por WEB, Mobile e TV futuramente através de um adaptador comum.

## Compatibilidade

A publicação é aditiva. Os caminhos existentes em `CineHUB_WEB/dados/` e nos assets Android não são substituídos. Assim, uma falha no novo pacote não impede o aplicativo atual de continuar usando seus dados conhecidos.

## Atualização

O workflow do Data Engine gera o pacote depois do processamento. O Cloudflare Pages publica a alteração automaticamente porque o diretório pertence ao output WEB.

Se não houver diferença real, o workflow não cria commit de dados.
