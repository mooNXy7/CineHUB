# CineHUB Data Engine — EPG Engine (Fase 7)

A Fase 7 adiciona um motor EPG multi-fonte **sem substituir os dados consumidos pelo WEB, Mobile ou TV**.

## Fluxo

```
EPG principal
     ↓
EPG secundário/fallback
     ↓
normalização de canais
     ↓
janela rolling de programação
     ↓
CineHUB_Data/epg/schedule.index.json
```

## Associação

A ordem de associação é:

1. `tvg-id` / ID do canal quando disponível;
2. nome canônico normalizado;
3. aliases já produzidos pelo Data Engine.

## Multi-fonte

Cada fonte possui prioridade. O engine:

- tenta todas as fontes habilitadas com retry controlado;
- usa a fonte de maior prioridade quando duas fontes possuem o mesmo programa;
- preenche lacunas com fontes secundárias;
- não descarta o canal quando uma fonte falha;
- registra latência, tamanho, canais associados e erros.

## Janela

A saída contém somente uma janela configurável de programação, padrão de 48 horas, em vez de entregar XMLTV bruto ao cliente.

O arquivo é gerado pelo Data Engine e pode ser publicado posteriormente em Cloudflare. WEB/Mobile/TV ainda não consomem esta saída nesta fase.

## Robustez

- timeout e limite de tamanho;
- retry limitado;
- XML inválido não derruba as outras fontes;
- horários convertidos para UTC;
- programas expirados excluídos;
- nenhum segredo no frontend;
- URLs externas tratadas como dados.

## Fontes

O registry começa com duas fontes públicas brasileiras configuráveis: um guia por país do ecossistema iptv-org e um guia brasileiro do projeto IPTV-com. A arquitetura permite trocar, remover ou acrescentar providers sem modificar o parser.

A implementação usa XMLTV e conceitos públicos de associação por ID/nome; não copia código do SaimoPlayer.
