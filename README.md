# 🎬 CineHUB

<p align="center">
  <img src="https://www.dropbox.com/scl/fi/836r2ngi5gykwifgjfy25/logo-horizontal.png?rlkey=tvczx4xrvlan6vqzw3f9m70wn&raw=1" alt="CineHUB" width="520">
</p>

<p align="center">
  <strong>Entretenimento sem limites.</strong><br>
  Filmes • Séries • Programação • Canais • Conteúdo online
</p>

<p align="center">
  <img src="https://img.shields.io/badge/CineHUB-Gratuito-E50914?style=for-the-badge" alt="CineHUB gratuito">
  <img src="https://img.shields.io/badge/WEB-Estável-111111?style=for-the-badge" alt="WEB estável">
  <img src="https://img.shields.io/badge/Android%20TV-Suportado-E50914?style=for-the-badge" alt="Android TV">
</p>

---

## 🍿 Sobre o CineHUB

O **CineHUB** é um aplicativo independente desenvolvido com foco em **dispositivos móveis e entretenimento digital**, reunindo diferentes experiências em uma única plataforma.

A proposta é oferecer uma interface moderna, simples e confortável para descobrir e acompanhar **filmes, séries, programação de TV, canais e diversos conteúdos online**, com foco em desempenho, navegação intuitiva e uma experiência inspirada no universo dos grandes serviços de streaming.

### ❤️ A proposta

O CineHUB foi pensado para ser:

- 🎬 **Completo** — filmes, séries, programação e canais em um só lugar.
- 📱 **Mobile-first** — desenvolvido pensando primeiro na experiência em dispositivos móveis.
- 📺 **Preparado para TV** — experiência própria e otimizada para Android TV.
- ⚡ **Rápido e leve** — arquitetura voltada para carregamento progressivo e melhor desempenho.
- 🎨 **Moderno** — identidade visual própria, com interface cinematográfica e acabamento premium.
- 🆓 **Totalmente gratuito** — o projeto é disponibilizado gratuitamente.

---

## ✨ Principais recursos

| Recurso | Descrição |
|---|---|
| 🎞️ **Filmes** | Catálogo de filmes e reprodução integrada. |
| 📺 **Séries** | Séries organizadas por temporadas e episódios. |
| 📡 **Programação** | Canais e programação de TV. |
| 🗓️ **EPG** | Guia eletrônico de programação quando disponível. |
| 🔎 **Pesquisa** | Busca e descoberta de conteúdos. |
| ❤️ **Favoritos** | Organização dos conteúdos preferidos. |
| ▶️ **Reprodução** | Player integrado para conteúdos compatíveis. |
| 📱 **WEB** | Experiência completa para navegadores. |
| 📺 **Android TV** | Navegação por controle remoto e interface própria para TV. |

---

## 🌐 CineHUB WEB

A versão **WEB** é a experiência principal para navegadores, com interface responsiva e catálogo organizado por categorias.

**Status atual:** 🟢 **Estável e funcionando corretamente**

A versão WEB está separada da arquitetura Android TV para evitar que alterações em uma plataforma afetem a outra.

> **Importante:** o CineHUB WEB é mantido em CineHUB_WEB/.

---

## 📺 CineHUB Android TV

A versão **CineHUB TV** possui uma arquitetura própria para televisores e dispositivos Android TV.

Ela foi desenvolvida para trabalhar com:

- 🎮 Navegação por D-pad/controle remoto.
- ↩️ Botão Back.
- 🖥️ Tela cheia.
- ▶️ Controles de reprodução.
- 🔊 Volume e mute.
- ⏪ Avanço e retrocesso.
- 📐 Layout otimizado para TV.
- 🔄 Sistema de atualização do aplicativo.
- 🚀 Distribuição automatizada por GitHub Actions.

> **Importante:** o Android TV é mantido separado em CineHUB_TV_Android/.

---

## 🎨 Identidade visual

O CineHUB possui identidade visual própria, baseada em uma linguagem **cinematográfica, tecnológica, moderna e premium**, com destaque para o vermelho CineHUB, preto, branco, transparências e elementos de vidro.

<p align="center">
  <img src="https://www.dropbox.com/scl/fi/b244hfzwvzscryc4p3s47/CineHub_-entretenimento-sem-limites.png?rlkey=vua1fk92qeoj78ul83t6m6sts&raw=1" alt="CineHUB — entretenimento sem limites" width="850">
</p>

---

## 📱 Interface do CineHUB

Alguns registros da interface atual:

<p align="center">
  <img src="https://www.dropbox.com/scl/fi/69hx9l9b04zhsldyj8vbn/Screenshot_2026-10-04-23-00-22-817_com.android.chrome.png?rlkey=oe9he5m1uz07c5x617p9jphyh&raw=1" width="31%" alt="CineHUB interface 1">
  <img src="https://www.dropbox.com/scl/fi/9g1ueaqv76pe3oprczgee/Screenshot_2026-10-04-23-04-32-969_com.android.chrome.png?rlkey=14oj7nwi3r7hfjgf6msgycx0w&raw=1" width="31%" alt="CineHUB interface 2">
  <img src="https://www.dropbox.com/scl/fi/wsjnu3mdy27lr43e8d1vx/Screenshot_2026-10-04-23-03-33-775_com.android.chrome.png?rlkey=86ukcu1lw9rcccafl0etnjruq&raw=1" width="31%" alt="CineHUB interface 3">
</p>

<p align="center">
  <img src="https://www.dropbox.com/scl/fi/0mr67ggxqrcgq1bwi61fw/Screenshot_2026-10-04-23-16-39-337_com.android.chrome.jpg?rlkey=cm7txszw3tfj9es4uwubaoxof&raw=1" width="31%" alt="CineHUB interface 4">
  <img src="https://www.dropbox.com/scl/fi/cluvznpt22d8t41i3occ1/Screenshot_2026-10-04-23-20-31-142_com.android.chrome.png?rlkey=a1fwnkts72usduwbnab0q2ch1&raw=1" width="31%" alt="CineHUB interface 5">
</p>

---

## 🧩 Estrutura do projeto

~~~text
CineHUB/
├── CineHUB_WEB/
│   └── Versão WEB oficial
│
├── CineHUB_TV_Android/
│   └── Aplicativo Android TV
│
├── .github/
│   └── GitHub Actions
│
└── README.md
~~~

A separação entre WEB e Android TV é intencional: cada plataforma possui sua própria estrutura e ciclo de evolução.

---

## 🚀 Desenvolvimento

O CineHUB continua em desenvolvimento e recebe melhorias de:

- desempenho;
- estabilidade;
- reprodução;
- organização de conteúdo;
- interface;
- compatibilidade;
- experiência mobile;
- experiência Android TV.

A prioridade do projeto é **evoluir sem quebrar o que já funciona**.

---

## 💬 Comunidade

Quer acompanhar o projeto, novidades e atualizações?

<p align="center">
  <strong>Entre para a comunidade CineHUB no Discord.</strong><br><br>
  <a href="https://discord.gg/FVFayvger">💬 Acompanhar o CineHUB em tempo real</a>
</p>

---

## 📌 Status

### CineHUB WEB
🟢 **Estável**

### CineHUB Android TV
🟢 **Em evolução**

---

## 📜 Aviso

O CineHUB é um projeto independente desenvolvido para fins de tecnologia, desenvolvimento de software e entretenimento.

A disponibilidade, origem e funcionamento de conteúdos externos dependem de suas respectivas fontes e serviços.

---

<p align="center">
  <strong>🎬 CineHUB</strong><br>
  <sub>Entretenimento sem limites.</sub>
</p>
