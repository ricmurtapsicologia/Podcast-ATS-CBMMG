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

---

# Política de preservação

A evolução mais recente do projeto foi deliberadamente conservadora.

Foram preservados:

- o banner/hero original;
- a imagem principal da ampulheta;
- as imagens originais das Séries 1 e 2;
- todos os links de áudio das Séries 1 e 2;
- a identidade visual azul-marinho/dourado;
- a lógica de abrir cada série no painel de conteúdo;
- o salvamento local de progresso dos áudios;
- o formulário/CTA de feedback existente.

A antiga Série 3, **“Prevenção e transformação de vidas”**, foi substituída visual e pedagogicamente por **“Primeiros Socorros Psicológicos”**.

> **Decisão de manutenção em 02/08/2026:** após auditoria completa de código, arquitetura, UX, acessibilidade, performance, segurança e manutenção, optou-se por **não modificar nenhum arquivo de código nesta etapa**. Somente este README foi atualizado para registrar o diagnóstico técnico e orientar futuras intervenções.

---

# Série 3 — Primeiros Socorros Psicológicos

O card externo utiliza uma fotografia em alta resolução da Pexels, sem texto sobreposto, mostrando um profissional de emergência oferecendo presença e suporte junto a uma ambulância.

Fonte visual do card externo:

- RDNE Stock project / Pexels — “Paramedic Talking to a Man”
- https://www.pexels.com/photo/paramedic-talking-to-a-man-6519869/

A imagem é carregada a partir do domínio `images.pexels.com`.

## Trilha de aprendizagem

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

Cada card contém conteúdo ampliado e estruturado em:

- síntese conceitual;
- contextualização para emergência e segurança pública;
- objetivo de aprendizagem;
- aplicação no campo;
- orientação específica para colega/equipe;
- condutas a evitar;
- microchecagem de retenção e tomada de decisão.

## Comportamento dos cards PSP

Para reduzir carga visual e melhorar ergonomia cognitiva:

- os 10 cards aparecem inicialmente **fechados**;
- no estado fechado ficam visíveis apenas imagem, número/fase, marcador temático e título;
- o conteúdo textual só aparece quando o usuário clica no card;
- apenas **um card pode permanecer aberto por vez**;
- ao abrir outro card, o anterior fecha automaticamente;
- o card aberto ocupa a largura da trilha para favorecer leitura;
- no celular, a leitura passa para uma única coluna;
- ao final da trilha existe um botão para **fechar a série e voltar à página inicial das séries**.

---

# Navegação das três séries

As três séries usam o mesmo painel de conteúdo.

- **Séries 1 e 2:** apresentam os episódios de áudio e, abaixo do último episódio, um botão para fechar a série e voltar à página inicial.
- **Série 3:** apresenta os 10 cards de PSP e, após o último conteúdo e as referências, um botão equivalente para retornar à página inicial.
- O botão superior **“Voltar às séries”** permanece disponível como segunda rota de saída.

---

# Imagens autorais dos 10 cards

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

Os SVGs possuem `viewBox`, título acessível e são apresentados no HTML com texto alternativo contextualizado.

---

# Base técnica de PSP

A trilha foi estruturada a partir de referências oficiais e rastreáveis:

- **World Health Organization; War Trauma Foundation; World Vision International.** *Psychological First Aid: Guide for Field Workers*.
  https://www.who.int/publications-detail-redirect/9789241548205
- **World Health Organization.** *Psychological First Aid: Facilitator’s Manual for Orienting Field Workers*.
  https://www.who.int/publications/i/item/psychological-first-aid
- **Organização Pan-Americana da Saúde.** *Primeiros cuidados psicológicos: guia para trabalhadores de campo*.
  https://iris.paho.org/handle/10665.2/7676

O conteúdo apresenta PSP como ajuda humana, prática e respeitosa após eventos críticos. Não os apresenta como psicoterapia, diagnóstico, interrogatório ou debriefing emocional obrigatório.

---

# Arquitetura atual

O projeto utiliza uma arquitetura estática, adequada ao GitHub Pages, composta por HTML, CSS e JavaScript nativos, sem framework de interface obrigatório.

Arquivos centrais:

- `index.html` — estrutura semântica, metadados, onboarding, conteúdo institucional e pontos de montagem das séries;
- `styles.css` — sistema visual principal, layout, responsividade, estados de interação e componentes compartilhados;
- `app.js` — dados das Séries 1 e 2, players de áudio, progresso local, onboarding e navegação principal;
- `psp.css` — componentes, acordeão e responsividade específicos da Série 3;
- `psp.js` — dados e renderização dos 10 cards PSP, adaptação visual da Série 3 e botões finais das três séries;
- `assets/psp-01.svg` a `assets/psp-10.svg` — artes autorais da trilha PSP;
- `README.md` — documentação funcional, editorial e técnica.

O repositório também contém os arquivos de áudio utilizados pelas Séries 1 e 2. Por isso, o tamanho global do repositório é significativamente maior do que o código-fonte isolado.

---

# Auditoria técnica — 02/08/2026

## Escopo da avaliação

A auditoria considerou as competências normalmente envolvidas em revisão profissional de uma plataforma educacional estática:

- engenharia de software front-end;
- arquitetura de código;
- HTML semântico;
- JavaScript nativo e gerenciamento de estado;
- CSS responsivo;
- UX/UI;
- ergonomia cognitiva;
- acessibilidade web;
- performance percebida;
- segurança de front-end;
- privacidade e dependências de terceiros;
- SEO técnico básico;
- manutenção e escalabilidade;
- resiliência de conteúdo e assets;
- documentação e governança de mudanças.

## Resultado executivo

**Avaliação global aproximada: 8,0/10.**

O sistema atual é funcional, visualmente coerente e adequado ao objetivo de material educacional estático. A separação recente entre HTML, CSS geral, JavaScript geral e componentes PSP reduziu significativamente o risco de manutenção em comparação com a versão monolítica anterior.

Não foi identificado defeito crítico que justifique refatoração imediata. Os principais pontos encontrados são **dívidas técnicas moderadas**, relevantes para futuras evoluções, mas compatíveis com a decisão atual de preservar o código.

### Scorecard técnico

| Dimensão | Avaliação | Parecer resumido |
|---|---:|---|
| Arquitetura geral | **8,0/10** | Simples, estática e adequada ao GitHub Pages; divisão de responsabilidades melhorou. |
| Funcionalidade e robustez | **8,3/10** | Fluxos principais são claros e possuem salvaguardas simples. |
| Qualidade/manutenibilidade do código | **7,0/10** | Funcional, porém há dados e comportamento acoplados e arquivos JS/CSS bastante compactados. |
| UX e ergonomia cognitiva | **8,8/10** | Hierarquia clara, abertura progressiva dos cards e rotas de retorno adequadas. |
| Responsividade | **8,5/10** | Breakpoints coerentes e boa adaptação dos cards para uma coluna. |
| Acessibilidade | **7,8/10** | Bom conjunto de recursos, com alguns pontos semânticos e de foco ainda melhoráveis. |
| Performance | **7,7/10** | Front-end leve; principal custo está em mídia externa e grande acervo de áudio. |
| Segurança front-end | **8,0/10** | Superfície de ataque pequena; `innerHTML` trabalha hoje apenas com dados controlados. |
| Privacidade | **7,0/10** | Progresso fica local, mas há Google Analytics e dependências externas que exigem governança. |
| SEO/social sharing | **8,0/10** | Metadados principais presentes; assets sociais ainda dependem de hospedagem externa. |
| Documentação | **9,0/10** | README passa a registrar arquitetura, preservação e dívida técnica explicitamente. |

---

# Pontos fortes identificados

## 1. Arquitetura compatível com o propósito

Para uma biblioteca educacional hospedada no GitHub Pages, HTML/CSS/JavaScript nativos são uma escolha tecnicamente adequada. A ausência de framework pesado reduz dependências, superfície de falhas, custo de atualização e complexidade de implantação.

## 2. Separação de responsabilidades melhor que a versão anterior

A extração de `styles.css`, `app.js`, `psp.css` e `psp.js` evita que toda alteração futura exija modificar um único HTML muito extenso.

A divisão atual é compreensível:

- núcleo da experiência e players em `app.js`;
- extensão PSP em `psp.js`;
- sistema visual geral em `styles.css`;
- sistema visual específico do acordeão PSP em `psp.css`.

## 3. Preservação das bibliotecas sonoras

A refatoração não alterou os URLs originais das duas séries de áudio. Esse é um ponto positivo de gestão de regressão, pois reduz a possibilidade de romper o acervo funcional ao evoluir a interface.

## 4. Estado local simples e apropriado

O uso de `localStorage` para:

- preferência do onboarding;
- última série sonora aberta;
- progresso de cada áudio;

é proporcional ao problema e evita backend desnecessário.

O progresso permanece no navegador do usuário e não precisa ser enviado ao servidor da aplicação.

## 5. UX da Série 3

A estratégia de esconder os textos dos 10 cards até o clique reduz densidade visual inicial. Manter apenas um card aberto por vez evita que o usuário receba simultaneamente uma grande massa textual.

O card expandido ocupar a largura total é uma decisão correta para leitura prolongada.

## 6. Redundância útil de navegação

A existência de:

- botão superior “Voltar às séries”; e
- botão equivalente após o último conteúdo

reduz deslocamento desnecessário e melhora a experiência em telas pequenas e conteúdos longos.

## 7. Responsividade

O CSS possui tratamento explícito para desktop, tablets e celulares. A trilha PSP reduz progressivamente colunas e reorganiza o card aberto para leitura vertical.

## 8. Acessibilidade já incorporada

Foram identificados recursos positivos:

- `lang="pt-BR"`;
- link de salto para o conteúdo;
- hierarquia de títulos compreensível;
- `aria-live` na região de conteúdo dinâmico;
- foco visível;
- `aria-expanded` e `aria-controls` no acordeão PSP;
- `alt` nas imagens;
- `<title>` nos SVGs autorais;
- suporte a `prefers-reduced-motion`;
- botões nativos em vez de `div` simulando controles;
- `rel="noopener noreferrer"` em links externos que abrem nova aba.

## 9. Conteúdo PSP separado da apresentação

As imagens autorais não carregam textos incorporados. O conteúdo permanece no DOM em HTML, o que favorece acessibilidade, tradução futura, responsividade e manutenção editorial.

## 10. Superfície de segurança reduzida

A aplicação não possui autenticação, banco de dados, formulários que gravem dados na aplicação ou backend próprio. Isso reduz significativamente a superfície de ataque em comparação com aplicações dinâmicas.

---

# Dívida técnica e oportunidades futuras

Os itens abaixo são **recomendações**, não alterações realizadas nesta auditoria.

## P1 — prioridade alta em futura refatoração

### 1. Fonte de verdade duplicada para a Série 3

`app.js` ainda contém a definição histórica da Série 3 como “Prevenção e transformação de vidas”, com estado `building`, enquanto `psp.js` localiza esse card no DOM e o transforma em “Primeiros Socorros Psicológicos”.

Hoje isso funciona porque:

1. `app.js` renderiza os três cards;
2. `psp.js` é carregado depois;
3. `psp.js` encontra o terceiro card;
4. substitui imagem, título, descrição e estado;
5. habilita o botão e registra o evento de abertura de PSP.

O comportamento é funcional, mas cria **duas fontes de verdade** para a mesma série.

Risco futuro: uma mudança em `app.js`, na ordem dos scripts, no `data-series-id` ou na estrutura do card pode impedir silenciosamente a transformação realizada por `psp.js`.

**Recomendação futura:** mover a definição real da Série 3 para uma fonte de dados única e permitir que o renderer principal compreenda diretamente séries do tipo `audio` e `psp`.

### 2. Ausência de testes automatizados

Não há evidência, na arquitetura atual analisada, de testes automatizados de regressão para:

- abertura das três séries;
- reprodução e retomada dos áudios;
- exclusividade do acordeão PSP;
- botões de retorno;
- onboarding;
- acessibilidade básica;
- links e assets externos.

Para o tamanho atual, testes manuais ainda são viáveis. Contudo, conforme o projeto cresce, regressões podem passar despercebidas.

**Recomendação futura:** adicionar pelo menos uma validação automatizada simples em CI para HTML/JS e smoke tests de navegação.

## P2 — prioridade média

### 3. JavaScript e CSS muito compactados

`app.js` e `styles.css` estão altamente compactados. Isso reduz tamanho textual, mas piora:

- leitura humana;
- revisão de diff no GitHub;
- depuração;
- manutenção por terceiros;
- localização de regressões.

Para um projeto sem pipeline de build, manter o código-fonte formatado seria mais vantajoso do que salvar alguns kilobytes.

**Recomendação futura:** manter arquivos-fonte legíveis e, apenas se necessário, produzir versões minificadas por automação.

### 4. Dados de áudio acoplados ao comportamento

A lista de dezenas de episódios está declarada dentro de `app.js`, junto com a lógica de player, navegação e onboarding.

Isso aumenta o custo de manutenção editorial: trocar um título ou arquivo de áudio exige editar o mesmo arquivo que controla a aplicação.

**Recomendação futura:** separar catálogo de conteúdo e lógica, por exemplo em um arquivo de dados próprio.

### 5. Conteúdo PSP e renderer no mesmo arquivo

`psp.js` reúne:

- os textos completos dos 10 cards;
- a transformação da Série 3;
- o HTML dos cards;
- comportamento do acordeão;
- botões finais;
- observação de mutações do DOM.

O arquivo continua manejável, mas já cumpre funções diferentes.

**Recomendação futura:** se a trilha crescer, separar dados pedagógicos de comportamento.

### 6. Estrutura interna do botão expansível

O botão `.psp-card-toggle` envolve blocos visuais complexos, incluindo elementos de layout e heading. Os navegadores atuais toleram e executam o padrão, e a interação por teclado é preservada, porém essa composição merece validação semântica formal em futura revisão de HTML.

**Recomendação futura:** validar o componente com um validador HTML e, se necessário, manter o controle de expansão como botão semanticamente simples associado ao conteúdo visual.

### 7. Modal de onboarding sem focus trap completo

O onboarding:

- usa `role="dialog"`;
- usa `aria-modal="true"`;
- move o foco para um controle;
- aceita `Escape`;
- restaura o foco ao fechar.

Esses são bons comportamentos. Porém não existe um mecanismo explícito que mantenha a navegação por `Tab` restrita ao modal enquanto ele está aberto.

**Recomendação futura:** implementar focus trap para conformidade de acessibilidade mais robusta.

### 8. Dependências de imagens externas

O hero e imagens das Séries 1 e 2 dependem do Pinterest; o card externo de PSP depende da Pexels.

Consequências possíveis:

- imagem removida pelo provedor;
- bloqueio de hotlink;
- latência de terceiros;
- alteração de políticas do domínio;
- menor controle sobre cache e disponibilidade.

Como há requisito de preservação das imagens existentes, nenhuma mudança foi realizada.

**Recomendação futura:** manter cópia autorizada/local apenas quando houver segurança jurídica e editorial para isso.

## P3 — melhoria evolutiva

### 9. Content Security Policy

O projeto não define uma política CSP explícita.

O risco atual é limitado porque a aplicação é estática e os dados inseridos em `innerHTML` são definidos no próprio código. Ainda assim, uma CSP seria uma camada adicional de defesa.

A implementação exige planejamento porque o site carrega:

- Google Analytics;
- imagens do Pinterest;
- imagem da Pexels;
- mídia do GitHub/raw GitHub;
- links externos.

### 10. Uso de `innerHTML`

O projeto utiliza `innerHTML` para renderizar cards e episódios.

**Estado atual:** risco baixo, pois os dados vêm de constantes controladas no próprio repositório.

**Risco futuro:** se esses dados passarem a vir de formulário, CMS, API ou arquivo não confiável, deverá existir sanitização ou construção via DOM APIs seguras.

### 11. Tratamento silencioso de erros de `localStorage`

Blocos `try/catch {}` garantem que falhas de armazenamento não interrompam o site. Isso é positivo para resiliência, mas erros são completamente silenciados.

Em ambiente de desenvolvimento, logs condicionais poderiam ajudar a diagnosticar problemas sem afetar o usuário final.

### 12. Estado PSP não persistido como as séries sonoras

O sistema restaura automaticamente uma série sonora previamente aberta, desde que ela tenha episódios. A Série 3 não participa desse mesmo mecanismo de persistência porque não pertence ao catálogo de áudio.

Isso não é um defeito funcional; é apenas uma assimetria de comportamento que deve ser consciente se, futuramente, for desejável retomar também o último card PSP estudado.

---

# Performance

## Pontos positivos

- HTML estático;
- CSS e JS locais;
- ausência de framework pesado;
- imagens SVG internas leves;
- `loading="lazy"` nos cards PSP;
- `preload="metadata"` nos players em vez de carregar todos os áudios integralmente;
- imagem principal pré-carregada;
- `preconnect` para domínios externos relevantes;
- CSS responsivo sem biblioteca externa.

## Custos principais

### Arquivos de áudio

O acervo de áudio é, naturalmente, o maior componente de armazenamento do repositório. O metadata preload evita download completo antecipado no navegador, mas a disponibilidade dos episódios depende de GitHub/raw GitHub.

### Imagens externas

Hero e cards externos exigem requisições para domínios terceiros. A performance final depende da disponibilidade e da latência desses provedores.

### Google Analytics

O Analytics adiciona uma requisição externa e execução adicional de JavaScript. O impacto não é alto para o projeto atual, mas deve ser considerado em auditorias de privacidade e performance.

---

# Segurança e privacidade

## Avaliação atual

A aplicação possui baixo risco estrutural por ser estática e não armazenar registros clínicos, credenciais ou dados de usuários em backend próprio.

### Dados locais

O progresso de áudio e preferências do onboarding são armazenados em `localStorage` no navegador.

Não devem ser tratados como armazenamento permanente: podem ser removidos pelo usuário, pelo navegador ou por políticas de limpeza.

### Google Analytics

O site carrega Google Analytics e configura `anonymize_ip: true`.

Isso não equivale, por si só, a uma declaração de conformidade com LGPD ou outras normas de privacidade. A necessidade de aviso, base legal, consentimento ou configuração adicional deve ser avaliada conforme o contexto institucional e a política aplicável ao projeto.

### Conteúdo de terceiros

Pinterest, Pexels, GitHub e Google Analytics são dependências externas. Sua utilização deve continuar sendo revisada sob os critérios de:

- disponibilidade;
- licenciamento;
- privacidade;
- políticas de uso;
- continuidade operacional.

---

# SEO e compartilhamento

O `index.html` contém:

- título descritivo;
- `meta description`;
- palavras-chave;
- autor;
- Open Graph title;
- Open Graph description;
- Open Graph image;
- URL canônica de compartilhamento via `og:url`;
- `og:type`.

O nível atual é satisfatório para um ambiente educacional específico.

O `og:image` ainda depende de uma imagem externa. Em evolução futura, uma imagem social própria e estável dentro do domínio do projeto seria tecnicamente mais controlável.

---

# Acessibilidade — parecer detalhado

## Implementado adequadamente

- idioma do documento definido;
- skip link;
- botões reais para ações;
- foco visual evidente;
- `aria-live` no conteúdo dinâmico;
- labels textuais compreensíveis;
- `aria-expanded` no acordeão;
- `aria-controls` ligando botão e detalhe;
- conteúdo oculto com atributo `hidden`;
- `alt` de imagens;
- título nos SVGs;
- respeito a redução de movimento;
- botão de retorno no início e fim do conteúdo.

## Pontos a validar futuramente

- focus trap do onboarding;
- semântica interna do botão complexo do card PSP;
- teste real com NVDA/JAWS/VoiceOver/TalkBack;
- teste completo por teclado sem mouse;
- contraste medido de textos secundários sobre superfícies translúcidas;
- comportamento de anúncios de abertura/fechamento do card em leitores de tela.

---

# UX e ergonomia cognitiva

A experiência atual é coerente com consumo educacional em desktop e celular.

## Aspectos especialmente positivos

- apenas três portas principais de entrada;
- identidade visual consistente;
- descrição resumida antes de entrar nas séries;
- cards PSP fechados por padrão;
- leitura progressiva;
- somente um conteúdo expansível aberto por vez;
- títulos funcionam como mapa cognitivo;
- progressão PSP explicitada;
- segmentação visual entre conceito, contexto, objetivo, aplicação, equipe, alertas e microchecagem;
- rotas claras de retorno;
- redução para coluna única em telas estreitas.

A estrutura evita transformar a página inicial em uma tela com excesso de texto e preserva o princípio de divulgação progressiva de informação.

---

# Robustez funcional

## Séries de áudio

O código:

- pausa outro áudio ao iniciar um novo;
- salva tempo atual no navegador;
- restaura progresso quando aplicável;
- permite zerar o progresso;
- marca conclusão;
- mantém links diretos de download;
- fecha e limpa a série ao retornar.

## PSP

O código:

- habilita o terceiro card após a renderização principal;
- impede múltiplos listeners usando `data-psp-bound`;
- permite apenas um card aberto por vez;
- mantém `aria-expanded` sincronizado;
- altera corretamente o atributo `hidden`;
- faz scroll para o card aberto;
- injeta botão final de retorno;
- evita duplicação do botão final nas séries sonoras;
- usa `MutationObserver` de modo limitado à região de conteúdo.

O `MutationObserver` adiciona complexidade, mas o comportamento atual possui salvaguarda para evitar reinserção contínua do botão final.

---

# Plano recomendado para uma futura refatoração

Nenhum dos itens abaixo deve ser executado automaticamente sem nova decisão de escopo.

## Fase 1 — consolidação sem alteração visual

1. criar fonte única de configuração das três séries;
2. distinguir explicitamente `type: "audio"` e `type: "psp"`;
3. remover a transformação posterior da Série 3 via DOM;
4. formatar `app.js` e `styles.css` para leitura humana;
5. separar dados dos áudios da lógica do player;
6. preservar integralmente a experiência visual e os URLs existentes.

## Fase 2 — qualidade automatizada

1. validação HTML;
2. lint de JavaScript;
3. lint de CSS;
4. checagem automática de links críticos;
5. smoke test de abertura das três séries;
6. teste de acordeão PSP;
7. teste básico de acessibilidade;
8. GitHub Actions somente para validação, sem alterar o modelo simples de publicação.

## Fase 3 — acessibilidade e resiliência

1. focus trap do onboarding;
2. revisão semântica do botão dos cards;
3. auditoria WCAG com leitor de tela;
4. avaliação de assets externos;
5. avaliação de CSP;
6. revisão da governança de Analytics/LGPD.

---

# Critérios de não regressão

Qualquer futura alteração deve preservar obrigatoriamente:

1. banner/hero atual, salvo decisão editorial expressa em contrário;
2. imagens das Séries 1 e 2;
3. URLs e disponibilidade dos áudios;
4. card externo de PSP ou substituto previamente aprovado;
5. 10 SVGs autorais internos;
6. ordem pedagógica dos 10 cards PSP;
7. comportamento de um card PSP aberto por vez;
8. botão superior e botão final de retorno;
9. progresso local dos áudios;
10. funcionamento em desktop e celular;
11. navegação por teclado;
12. foco visível;
13. `prefers-reduced-motion`;
14. ausência de backend ou coleta desnecessária de dados pessoais.

---

# Checklist manual antes de publicar mudanças futuras

## Estrutura

- [ ] Hero continua íntegro.
- [ ] As três séries aparecem.
- [ ] Série 3 está identificada como PSP.
- [ ] Nenhum texto histórico de “Prevenção” fica visível ao usuário.

## Áudios

- [ ] Série 1 abre.
- [ ] Série 2 abre.
- [ ] Player inicia áudio.
- [ ] Um player pausa o outro.
- [ ] Progresso é salvo.
- [ ] Progresso é restaurado.
- [ ] “Zerar progresso” funciona.
- [ ] Download funciona.
- [ ] Botão final de retorno funciona.

## PSP

- [ ] Trilha abre no terceiro card.
- [ ] Dez cards são renderizados.
- [ ] Todos começam fechados.
- [ ] Apenas um card permanece aberto.
- [ ] `aria-expanded` acompanha o estado visual.
- [ ] As 10 imagens SVG carregam.
- [ ] Layout aberto funciona em desktop.
- [ ] Layout aberto funciona em celular.
- [ ] Referências abrem corretamente.
- [ ] Botão final de retorno funciona.

## Acessibilidade

- [ ] Skip link funciona.
- [ ] Todos os controles recebem foco.
- [ ] Ordem de Tab é lógica.
- [ ] Escape fecha o onboarding.
- [ ] Navegação continua possível sem mouse.

## Dependências externas

- [ ] Hero do Pinterest carrega.
- [ ] Imagens das Séries 1 e 2 carregam.
- [ ] Imagem Pexels do PSP carrega.
- [ ] URLs raw/GitHub dos áudios respondem.
- [ ] Google Analytics não impede carregamento da página caso falhe.

---

# Governança de manutenção

Ao alterar o projeto:

1. preservar o banner e as imagens das Séries 1 e 2;
2. preservar os links de áudio existentes;
3. manter a Série 3 como Primeiros Socorros Psicológicos;
4. manter os 10 cards em progressão pedagógica;
5. manter o comportamento de apenas um card PSP aberto por vez;
6. preservar o botão final de retorno nas três séries;
7. não substituir os SVGs internos por imagens externas sem necessidade;
8. verificar periodicamente a disponibilidade da imagem externa da Pexels;
9. testar desktop e mobile;
10. testar abertura/fechamento dos cards, reprodução, retomada e download dos áudios após qualquer refatoração;
11. evitar alterações simultâneas de conteúdo, arquitetura e identidade visual sem necessidade;
12. preferir mudanças pequenas, rastreáveis e reversíveis;
13. revisar este README quando a arquitetura for modificada.

---

# Parecer técnico final

O estado atual é **satisfatório e operacionalmente adequado** para o propósito do projeto.

A principal recomendação não é uma refatoração imediata, mas a manutenção de disciplina de mudança: preservar a experiência atual e, quando houver necessidade real de evolução técnica, resolver primeiro a duplicidade da Série 3 e a separação entre dados e comportamento.

A arquitetura atual não exige framework, backend ou reconstrução completa. Uma futura melhoria deve ser incremental, com foco em manutenção, testes e acessibilidade, evitando alterar elementos visuais e funcionais que já estão consolidados.

---

# Publicação

A publicação ocorre pelo GitHub Pages a partir do branch padrão `main`.
