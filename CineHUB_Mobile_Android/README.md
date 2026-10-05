# CineHUB Mobile

Aplicativo Android para celulares, isolado da versão WEB e da versão Android TV.

## Arquitetura

- A interface é servida pela versão WEB oficial em https://cinehub-web.pages.dev/.
- O APK é uma camada Android nativa leve, com WebView, fullscreen, downloads e atualização.
- O manifesto OTA fica em update.json e é consultado diretamente pelo APK via GitHub Raw.
- Cada versão é publicada em uma GitHub Release com a tag mobile-vX.Y.Z.

## OTA

O APK compara versionCode local com o manifesto remoto. Quando encontra uma versão maior, baixa o APK da release e abre o instalador do Android.

Todas as versões precisam usar a mesma chave de assinatura. O workflow espera os secrets:
- CINEHUB_MOBILE_KEYSTORE_BASE64
- CINEHUB_MOBILE_STORE_PASSWORD
- CINEHUB_MOBILE_KEY_ALIAS
- CINEHUB_MOBILE_KEY_PASSWORD

A chave nunca deve ser commitada no repositório.

## Isolamento

Não modificar CineHUB_WEB/ nem CineHUB_TV_Android/ para construir ou atualizar o Mobile.
