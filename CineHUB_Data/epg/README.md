# CineHUB Data Engine — EPG Engine (Fase 7)

A Fase 7 cria o EPG Engine multi-fonte sem substituir os dados consumidos atualmente pelo WEB, Mobile ou TV.

## Fluxo

```text
fontes XMLTV
    ↓
retry + validação
    ↓
cache HTTP condicional / cache processado
    ↓
associação por tvg-id → nome canônico → alias
    ↓
janela rolling
    ↓
merge por prioridade + preenchimento de lacunas
    ↓
CineHUB_Data/epg/schedule.index.json
```

## Multi-fonte

Cada fonte possui prioridade. O engine:

- tenta as fontes em ordem de prioridade;
- usa retry limitado;
- aceita ETag / Last-Modified quando a origem fornece;
- reutiliza o resultado processado enquanto o cache estiver válido;
- não baixa/processa novamente o XML inteiro quando um cache condicional pode ser reutilizado;
- usa a fonte de maior prioridade quando dois feeds possuem o mesmo programa;
- permite que fontes secundárias preencham canais/programações ausentes;
- registra latência, HTTP status, cache hit, canais associados, programas e erros.

## Normalização

A associação segue:

1. tvg-id / ID do canal;
2. nome canônico normalizado;
3. aliases produzidos pelo Data Engine.

A normalização remove acentos, pontuação e marcadores de qualidade como HD/FHD/UHD/4K.

## Janela e cache

A saída padrão contém 48 horas de programação.

O cache processado possui validade padrão de 12 horas. Cache expirado não é tratado silenciosamente como programação atual: quando expirado, o engine volta à fonte e gera um novo conjunto.

O cache processado fica em CineHUB_Data/.cache/epg/ e é persistido pelo GitHub Actions Cache, sem aumentar o histórico Git.

O cliente não recebe XMLTV bruto e não precisa processá-lo.

## Robustez

- timeout configurável;
- limite de tamanho;
- até 3 tentativas por fonte;
- XML inválido não derruba as outras fontes;
- estados healthy, degraded, offline e unknown;
- primeira falha → unknown;
- segunda falha consecutiva → degraded;
- terceira ou mais → offline;
- horários convertidos para UTC;
- programas expirados excluídos;
- uma fonte indisponível não derruba o restante do EPG.

## Publicação

O workflow .github/workflows/epg-engine.yml:

1. roda testes;
2. valida o registry;
3. executa o EPG Engine;
4. publica schedule.index.json e epg-status.json;
5. cria commit somente quando esses arquivos mudam.

Ele também é disparado após uma execução bem-sucedida do workflow diário do Data Engine. Isso garante que o EPG use os canais normalizados/resolvidos mais recentes.

## Compatibilidade

A Fase 7 é aditiva. Nenhuma rota atual de dados do WEB, Mobile ou TV foi substituída.

A saída foi desenhada para ser consumida posteriormente pelo contrato comum do CineHUB Data Engine e publicada em infraestrutura de dados/Cloudflare sem exigir alteração de APK para cada atualização de programação.

## SaimoPlayer

Foram consultadas ideias públicas do SaimoPlayer relacionadas a:

- cache de EPG já processado;
- janela curta de programação;
- múltiplas fontes;
- associação robusta de canais;
- processamento fora da UI.

A implementação do CineHUB é própria e não copia código do projeto.
