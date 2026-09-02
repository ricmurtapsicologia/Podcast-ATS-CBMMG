# Girando a Ampulheta da Vida — Learning Experience v4

## Objetivo

Transformar a página de uma biblioteca de players em uma plataforma de aprendizagem orientada à continuidade, preservando a identidade visual azul-marinho/dourado, o banner canônico e o conteúdo institucional.

## Arquitetura canônica

`content-manifest.js` é a fonte única para séries, estados editoriais, títulos, imagens e episódios das Séries 1 e 2. A Série 3 é declarada no mesmo manifesto e usa `psp-cards.json` apenas para o conteúdo pedagógico específico dos 10 cards.

`app.js` é o controlador de navegação, estado, player das Séries 1/2, progresso, busca, filtros, deep links, CTA recorrente e onboarding. `psp.js` expõe somente o renderer `GAV_PSP.render`; ele não altera dados ou cards criados por outro módulo.

## Estado e persistência

A identidade do conteúdo é pedagógica, não física. O estado é salvo por ID estável:

- `a1-001` … `a1-021`;
- `a2-000` … `a2-013`;
- `psp-01` … `psp-10`.

Modelo:

```json
{"position": 0, "completed": false, "lastPlayedAt": null}
```

A URL/versionamento do MP3 pode mudar sem apagar progresso. O runtime migra posições legadas quando possível.

## Experiência de áudio

Cada série sonora possui um único player ativo. Os episódios são apresentados em lista compacta com estado individual, busca e filtros. A conclusão persiste após reload. O player oferece reinício, download e próximo episódio.

## Experiência recorrente

Sem progresso, o CTA primário é `Explorar as séries`. Com progresso, passa a ser `Continuar de onde parei`, e o hero entra em modo compacto. O último conteúdo pode ser retomado em um clique.

## Deep links

Rotas estáveis:

- `#serie-1/a1-007`
- `#serie-2/a2-003`
- `#serie-3/psp-03`

A rota não depende do nome ou da versão física do arquivo de áudio.

## Acessibilidade

- skip link;
- foco visível;
- diálogo de onboarding com `aria-modal`, Escape e focus trap;
- região `role=status` pequena e específica;
- controles nativos de áudio;
- suporte a `prefers-reduced-motion`;
- layout responsivo e controles com alvos adequados.

## Assets

Hero e imagens das três séries foram internalizados em `assets/img/`. O runtime não depende de Pinterest ou Pexels para esses elementos críticos.

## Estados editoriais

Taxonomia canônica:

- `available` → Disponível;
- `coming_soon` → Em preparação;
- `maintenance` → Em manutenção.

Termos internos de produção de áudio (N2/N3) não são expostos ao usuário.

## Gate de release

A release deve passar por:

1. `scripts/validate_learning_v4.py` — arquitetura, manifesto, release única, assets, player único e invariantes;
2. `scripts/smoke_player_e2e.py` — desktop/mobile, busca, filtros, estado, deep links, Série 3, teclado e reduced motion;
3. após merge em `main`, convergência do GitHub Pages e repetição do E2E contra a URL pública.

## Critérios de aceite

- zero estado editorial contraditório;
- uma fonte canônica de séries;
- um player por trilha aberta;
- progresso por ID estável e conclusão persistente;
- retorno ao último conteúdo em um clique;
- busca e filtros nas séries sonoras;
- deep links para conteúdo específico;
- Série 3 integrada ao mesmo modelo de estado;
- nenhum jargão N2/N3 visível;
- hero e imagens de série locais;
- navegação funcional por teclado e com reduced motion;
- gate local e público verdes antes de declarar a entrega concluída.

## Rollback

A implementação foi construída inicialmente em `refactor/learning-experience-v4`. Enquanto não houver merge, `main` permanece intacta. Depois do merge, rollback é feito revertendo o merge/commit de release e aguardando a reconvergência do GitHub Pages.
