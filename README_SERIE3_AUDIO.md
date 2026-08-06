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
- `psp.js`: renderização, acordeão, players HTML5 e progresso;
- `psp.css`: apresentação responsiva dos cards e área de áudio;
- `roteiros/serie-3/psp-01.md` a `psp-10.md`: roteiros-fonte das microaulas;
- `assets/audio/serie-3/psp-01.mp3` a `psp-10.mp3`: arquivos finais reproduzidos na página;
- `scripts/generate_psp_audio.py`: gerador dos arquivos a partir dos roteiros;
- `.github/workflows/generate-psp-audio.yml`: automação de geração e publicação.

## Reprodução

A Série 3 usa arquivos MP3 reais hospedados no próprio repositório, seguindo o mesmo padrão utilizado nas demais páginas sonoras do projeto.

Os arquivos são gerados com duas vozes neurais em português brasileiro:

- instrutor: `pt-BR-AntonioNeural`;
- profissional/aluno: `pt-BR-FranciscaNeural`.

O navegador reproduz os arquivos por `<audio controls>` nativo. A reprodução:

- não depende das vozes instaladas no celular ou notebook;
- mantém timbre consistente entre dispositivos;
- utiliza uma voz principal e uma segunda voz para dúvidas curtas;
- mantém apenas um áudio ativo por vez;
- pausa outro player quando uma nova faixa é iniciada;
- salva posição por card no `localStorage`;
- permite retomada;
- marca conclusão;
- permite reiniciar o áudio;
- usa `preload="metadata"`;
- não usa autoplay.

## UX

No estado fechado, o card mostra apenas o conteúdo visual essencial e o marcador `Áudio • 2–4 min`.

Ao abrir o card, o usuário encontra:

1. conteúdo escrito preservado;
2. bloco `Microaula em áudio`;
3. player HTML5 simples e conhecido;
4. status `Novo`, `Retomar em mm:ss`, `Em mm:ss` ou `Concluído`;
5. botão discreto para reiniciar quando aplicável;
6. demais blocos escritos do card e microchecagem.

Em telas estreitas, o player usa 100% da largura disponível e não cria overflow horizontal.

## Manutenção editorial

Para alterar uma microaula, edite seu roteiro em `roteiros/serie-3/` e execute novamente o workflow de geração.

As falas devem manter o formato:

`**INSTRUTOR:** texto`

`**PROFISSIONAL:** texto`

O script reconhece essas marcações, gera cada fala com a voz correspondente, insere pausas discretas e exporta um único MP3 por card.

## Não regressão

Antes de publicar futuras alterações:

- abrir Séries 1 e 2 e confirmar reprodução normal;
- confirmar que seus URLs e catálogo continuam inalterados;
- abrir os 10 cards PSP;
- testar os 10 MP3s;
- iniciar um áudio e depois outro;
- testar pausa, retomada, conclusão e reinício;
- recarregar a página e verificar retomada;
- testar Chrome/Edge no notebook e Chrome no Android;
- verificar ausência de overflow horizontal e erros no console.
