# CineHUB Mobile

<p align="center"><img src="./CineHUB_Assets/logo-completa.png" alt="CineHUB" width="520"></p>

<p align="center"><strong>Aplicativo Android oficial do CineHUB.</strong></p>

Este repositório é dedicado exclusivamente ao **CineHUB Mobile**: aplicativo Android, integração com o sistema, distribuição de APKs e atualização OTA.

## Repositórios oficiais

- **Mobile (este repositório):** https://github.com/mooNXy7/CineHUB
- **WEB:** https://github.com/mooNXy7/CineHUB-WEB
- **TV / Android TV:** https://github.com/mooNXy7/CineHUB-TV

Os projetos WEB e TV têm repositórios independentes. Seus códigos-fonte não ficam mais armazenados neste repositório mobile.

## Estrutura

- `CineHUB_Mobile_Android/` — projeto Android e configuração de atualização OTA.
- `CineHUB_Assets/` — identidade visual e recursos compartilhados do Mobile.
- `CineHUB_Data/` — manifestos e ferramentas de dados utilizados pelo ecossistema CineHUB.
- `.github/workflows/mobile-release.yml` — compilação, verificação de assinatura e publicação do APK Mobile.

## Atualização OTA

O aplicativo consulta o manifesto:

`CineHUB_Mobile_Android/update.json`

O manifesto informa a versão estável, o link do APK e seu SHA-256. O workflow de release compila o aplicativo, valida o APK e publica a atualização na release `mobile-vX.Y.Z`.

A versão atual publicada é **1.0.7**.

## Princípios do projeto

- Estabilidade antes de novas funcionalidades.
- Manter a identidade visual oficial CineHUB.
- Preservar a assinatura de release para permitir atualizações sobre instalações existentes.
- Validar a integridade do APK e seu SHA-256 antes da publicação.
- Manter Mobile, WEB e TV separados para evitar builds cruzados e alterações acidentais.

## Licença e conteúdo

Consulte os avisos e as licenças dos recursos de terceiros antes de redistribuí-los. A disponibilidade de conteúdo e fontes externas pode variar.
