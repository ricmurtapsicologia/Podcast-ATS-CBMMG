# Girando a Ampulheta da Vida — Biblioteca de Apoio ATS

Ambiente web complementar às aulas de **Atendimento a Tentativas de Suicídio (ATS)**, publicado no GitHub Pages.

## Página publicada

https://ricmurtapsicologia.github.io/Podcast-ATS-CBMMG/

## Objetivo

Reunir, em uma única experiência de aprendizagem:

- a biblioteca sonora original sobre abordagem técnica em ATS;
- a biblioteca sonora original sobre compreensão do sofrimento em crise;
- uma trilha visual de **Primeiros Socorros Psicológicos (PSP)** para profissionais de emergência e segurança pública;
- conteúdos de cuidado com a pessoa atendida, apoio entre pares e autocuidado operacional.

O projeto é material educacional complementar. Não substitui doutrina operacional, protocolos institucionais, treinamento, supervisão ou atendimento especializado.

## Política de preservação

A atualização que criou a trilha PSP foi deliberadamente conservadora.

Foram preservados:

- o banner/hero original do projeto;
- a imagem principal da ampulheta;
- as imagens originais das Séries 1 e 2;
- todos os links de áudio das Séries 1 e 2;
- a identidade visual azul-marinho/dourado;
- a lógica de abrir uma série no painel de conteúdo;
- o salvamento local de progresso dos áudios;
- o formulário/CTA de feedback existente.

A antiga Série 3, **“Prevenção e transformação de vidas”**, foi substituída por **“Primeiros Socorros Psicológicos”**.

## Série 3 — Primeiros Socorros Psicológicos

O card externo utiliza uma fotografia em alta resolução da Pexels, sem texto sobreposto, mostrando um profissional de emergência oferecendo presença e suporte junto a uma ambulância.

Fonte visual do card externo:

- RDNE Stock project / Pexels — “Paramedic Talking to a Man”
- https://www.pexels.com/photo/paramedic-talking-to-a-man-6519869/

A imagem é carregada a partir do domínio `images.pexels.com`.

### Trilha de aprendizagem

A Série 3 contém 10 cards internos e segue a progressão:

**Preparar → Observar → Escutar → Conectar → Cuidar**

Os cards são:

1. **O que são Primeiros Socorros Psicológicos** — fundamentos e finalidade.
2. **Quando usar PSP — e quando outra resposta é necessária** — indicação e limites.
3. **Preparar: cenário, segurança, papel e recursos** — organização antes do contato.
4. **Observar: quem precisa de quê primeiro** — priorização funcional.
5. **Aproximar-se e escutar sem pressionar** — primeiro contato e escuta.
6. **Ajudar de forma prática e conectar recursos** — ação útil e continuidade.
7. **Cuidar do colega: apoio entre pares** — cuidado profissional sem estigma.
8. **Cuidar de si: autocuidado operacional** — preservação funcional e recuperação.
9. **Limites profissionais: o que fazer e o que evitar** — ética, privacidade e competência.
10. **Encerrar: próximo passo, passagem e reorganização da equipe** — continuidade segura.

Cada card contém:

- imagem autoral;
- síntese conceitual;
- objetivo de aprendizagem;
- aplicação no campo;
- orientação específica para colega/equipe;
- condutas a evitar;
- microchecagem de retenção.

## Imagens autorais dos 10 cards

Os cards internos utilizam SVGs próprios e locais, sem texto embutido na arte:

- `assets/psp-01.svg`
- `assets/psp-02.svg`
- `assets/psp-03.svg`
- `assets/psp-04.svg`
- `assets/psp-05.svg`
- `assets/psp-06.svg`
- `assets/psp-07.svg`
- `assets/psp-08.svg`
- `assets/psp-09.svg`
- `assets/psp-10.svg`

A opção por SVG oferece:

- alta definição em celular e desktop;
- carregamento leve;
- independência de bancos externos para os cards internos;
- consistência visual entre os 10 módulos;
- melhor manutenção futura.

## Base técnica de PSP

A trilha foi estruturada a partir de referências oficiais e rastreáveis:

- **World Health Organization; War Trauma Foundation; World Vision International.** *Psychological First Aid: Guide for Field Workers*.
  https://www.who.int/publications-detail-redirect/9789241548205
- **World Health Organization.** *Psychological First Aid: Facilitator’s Manual for Orienting Field Workers*.
  https://www.who.int/publications/i/item/psychological-first-aid
- **Organização Pan-Americana da Saúde.** *Primeiros cuidados psicológicos: guia para trabalhadores de campo*.
  https://iris.paho.org/handle/10665.2/7676

O conteúdo apresenta PSP como ajuda humana, prática e respeitosa após eventos críticos. Não os apresenta como psicoterapia, diagnóstico, interrogatório ou debriefing emocional obrigatório.

## Arquitetura

- `index.html` — estrutura semântica e conteúdo institucional;
- `styles.css` — identidade visual e responsividade base;
- `app.js` — séries sonoras, players, progresso local e navegação principal;
- `psp.css` — componentes e responsividade dos cards PSP;
- `psp.js` — ativação da Série 3 e conteúdo dos 10 cards;
- `assets/psp-01.svg` a `assets/psp-10.svg` — artes autorais da trilha PSP;
- `README.md` — documentação do projeto.

## UX e acessibilidade

A versão atual mantém ou acrescenta:

- navegação responsiva;
- link “Pular para o conteúdo”;
- foco visível por teclado;
- áreas de clique adequadas;
- textos alternativos nas imagens;
- suporte a `prefers-reduced-motion`;
- cards com hierarquia visual consistente;
- progressão explícita da trilha PSP;
- separação entre conteúdo conceitual, aplicação, cuidado da equipe e alertas.

## Manutenção

Ao alterar o projeto:

1. preservar o banner e as imagens das Séries 1 e 2;
2. preservar os links de áudio já existentes;
3. manter a Série 3 como Primeiros Socorros Psicológicos;
4. manter os 10 cards em progressão pedagógica;
5. não substituir os SVGs internos por imagens externas sem necessidade;
6. verificar periodicamente a disponibilidade da imagem externa da Pexels;
7. usar fontes técnicas oficiais para alterações de conteúdo;
8. testar desktop e mobile;
9. testar abertura e fechamento das três séries;
10. testar reprodução, retomada e download dos áudios após qualquer refatoração.

## Publicação

A publicação ocorre pelo GitHub Pages a partir do branch padrão `main`.