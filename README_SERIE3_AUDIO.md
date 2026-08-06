# Série 3 — Microaulas em áudio

## Escopo

Implementação restrita à Série 3 — Primeiros Socorros Psicológicos.

Regras de preservação:

- Séries 1 e 2 permanecem sem alteração de catálogo, URLs, players e progresso;
- o conteúdo escrito dos 10 cards da Série 3 permanece integral;
- cada card recebe uma microaula complementar de aproximadamente 2 a 4 minutos;
- a experiência é mobile first, progressiva e sem autoplay.

## Arquitetura

- `psp-cards.json`: fonte de dados do conteúdo escrito dos 10 cards;
- `psp.js`: renderização, acordeão, reprodução das microaulas e progresso;
- `psp.css`: apresentação responsiva dos cards e controles de áudio;
- `roteiros/serie-3/psp-01.md` a `psp-10.md`: roteiros-fonte das microaulas.

Os roteiros são carregados somente quando o usuário solicita a reprodução do card correspondente.

## Reprodução

A Série 3 usa `SpeechSynthesis` do navegador/dispositivo para evitar a publicação de arquivos de voz artificial de baixa qualidade. A reprodução:

- usa voz em português disponível no dispositivo;
- tenta usar vozes distintas para instrutor e profissional quando há mais de uma voz pt-BR/pt disponível;
- usa ritmo aproximado de 125 palavras por minuto;
- mantém apenas uma microaula ativa por vez;
- pausa os players HTML5 das Séries 1 e 2 quando uma microaula PSP é iniciada;
- cancela a microaula PSP quando um áudio HTML5 é iniciado;
- salva progresso por card no `localStorage`;
- oferece pausar, retomar, reiniciar e indicação de conclusão;
- não usa autoplay.

A qualidade e o timbre dependem das vozes instaladas no sistema operacional/navegador. A arquitetura permite substituir futuramente a síntese nativa por MP3s neurais sem alterar o conteúdo dos cards.

## UX

No estado fechado, o card mostra apenas o conteúdo visual essencial e o marcador `Áudio • 2–4 min`.

Ao abrir o card, o usuário encontra:

1. conteúdo escrito preservado;
2. bloco `Microaula em áudio`;
3. botão principal de ouvir/pausar/retomar;
4. status de progresso;
5. barra discreta de progresso;
6. botão de reinício quando aplicável;
7. demais blocos escritos do card e microchecagem.

Em telas estreitas, os controles ocupam a largura disponível e evitam overflow horizontal.

## Manutenção editorial

Para alterar uma microaula, edite somente seu arquivo em `roteiros/serie-3/`.

As falas devem manter o formato:

`**INSTRUTOR:** texto`

`**PROFISSIONAL:** texto`

O parser do player reconhece essas duas marcações.

## Validação recomendada

- abrir Séries 1 e 2 e confirmar reprodução normal;
- abrir os 10 cards PSP;
- testar as 10 microaulas;
- iniciar um áudio e depois outro;
- testar pausar, retomar, reiniciar e concluir;
- recarregar a página e verificar retomada;
- testar Chrome/Edge no notebook e Chrome no Android;
- verificar ausência de overflow horizontal e erros no console.