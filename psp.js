(() => {
  "use strict";

  const PSP_IMAGE = "https://images.pexels.com/photos/6519869/pexels-photo-6519869.jpeg?auto=compress&cs=tinysrgb&w=1200&h=1500&fit=crop";

  const PSP_CARDS = [
    {
      n:"01", phase:"Fundamentos", tag:"Compreender", image:"assets/psp-01.svg",
      alt:"Ilustração autoral sobre apoio humano e proteção nos Primeiros Socorros Psicológicos",
      title:"O que são Primeiros Socorros Psicológicos",
      lead:"PSP são uma forma de ajuda humana, prática e respeitosa para pessoas afetadas por eventos críticos. O foco inicial é favorecer segurança, orientação, dignidade e acesso a recursos úteis.",
      objective:"Reconhecer PSP como apoio inicial, e não como psicoterapia ou diagnóstico.",
      field:["Ofereça presença calma e respeitosa.","Pergunte o que seria útil agora, sem presumir necessidades.","Priorize ajuda prática, informação simples e conexão com recursos."],
      team:"O mesmo princípio vale entre colegas: disponibilidade sem invasão e respeito ao tempo de cada profissional.",
      avoid:"Não force conversa, não interprete reações como diagnóstico e não prometa resultados que você não pode garantir.",
      check:"Minha presença está aumentando segurança, orientação e autonomia?"
    },
    {
      n:"02", phase:"Fundamentos", tag:"Indicação", image:"assets/psp-02.svg",
      alt:"Ilustração autoral sobre preparação e indicação dos Primeiros Socorros Psicológicos",
      title:"Quando usar PSP — e quando outra resposta é necessária",
      lead:"PSP podem ser úteis após situações críticas quando a pessoa demonstra sofrimento ou necessidade de apoio. Nem toda pessoa afetada precisa ou deseja intervenção imediata.",
      objective:"Distinguir uma oferta de apoio inicial de situações que exigem outros recursos profissionais ou operacionais.",
      field:["Ofereça ajuda sem obrigar a pessoa a aceitá-la.","Observe necessidades concretas e capacidade de compreender informações.","Acione os recursos institucionais adequados quando a necessidade ultrapassar sua função."],
      team:"Entre pares, uma conversa breve pode ser suficiente; quando o funcionamento permanece prejudicado, facilite acesso a suporte formal.",
      avoid:"Não transforme PSP em avaliação clínica improvisada nem em procedimento obrigatório para todos após uma ocorrência.",
      check:"Esta pessoa precisa de presença e apoio prático ou de outro recurso especializado agora?"
    },
    {
      n:"03", phase:"Preparar", tag:"Antes do contato", image:"assets/psp-03.svg",
      alt:"Ilustração autoral sobre observação de segurança e necessidades prioritárias",
      title:"Preparar: cenário, segurança, papel e recursos",
      lead:"Antes de ajudar, compreenda o contexto. Uma atuação organizada depende de informação mínima sobre segurança, estrutura da ocorrência, serviços disponíveis e limites da própria função.",
      objective:"Entrar no contato com um mapa simples do cenário e capacidade realista de ajudar.",
      field:["Confirme as condições de segurança e o fluxo da ocorrência.","Identifique recursos de saúde, assistência, transporte, abrigo, informação e apoio social.","Alinhe sua atuação com equipe, comando e protocolos institucionais."],
      team:"Faça também um autocheck: estou orientado e em condição de oferecer presença útil? Se não, sinalize a necessidade de apoio ou troca de função quando possível.",
      avoid:"Não prometa recursos que você não controla e não deixe o apoio psicossocial competir com necessidades operacionais prioritárias.",
      check:"Segurança conhecida • papel definido • recursos mapeados • equipe alinhada."
    },
    {
      n:"04", phase:"Observar", tag:"Priorizar", image:"assets/psp-04.svg",
      alt:"Ilustração autoral sobre aproximação respeitosa e primeiro contato",
      title:"Observar: quem precisa de quê primeiro",
      lead:"Observar em PSP significa organizar prioridades, não diagnosticar. Procure necessidades básicas urgentes, pessoas sem suporte e sinais de desorganização que dificultem compreender ou utilizar a ajuda disponível.",
      objective:"Priorizar a resposta a partir de segurança, necessidades e funcionamento atual.",
      field:["Observe proteção física, cuidados de saúde, abrigo, água, informação e contato com pessoas de referência.","Perceba barreiras de comunicação, orientação ou mobilidade.","Direcione a pessoa ao recurso mais adequado para a necessidade identificada."],
      team:"Observe a equipe também: exaustão, confusão ou queda importante de atenção podem indicar necessidade de pausa ou reorganização de função.",
      avoid:"Não rotule reações esperadas ao estresse. O foco inicial é o que a pessoa precisa para funcionar e permanecer protegida.",
      check:"Segurança → necessidades básicas → capacidade de compreender → recurso adequado."
    },
    {
      n:"05", phase:"Escutar", tag:"Contato", image:"assets/psp-05.svg",
      alt:"Ilustração autoral sobre escuta ativa sem pressão",
      title:"Aproximar-se e escutar sem pressionar",
      lead:"O primeiro contato deve ser previsível e respeitoso. Apresente-se, explique sua função e escute necessidades atuais. A pessoa não precisa recontar toda a experiência para receber ajuda.",
      objective:"Criar vínculo suficiente para compreender necessidades sem retirar autonomia desnecessariamente.",
      field:["Diga quem você é e por que está ali.","Use perguntas breves e abertas sobre o presente.","Dê tempo para resposta, aceite silêncio e resuma o que compreendeu."],
      team:"Com colegas, prefira abordagem discreta e concreta, evitando exposição diante do grupo.",
      avoid:"Não force desabafo, não busque detalhes por curiosidade e não use frases que minimizem o sofrimento.",
      check:"Ao final da escuta, consigo identificar uma ou duas necessidades prioritárias?"
    },
    {
      n:"06", phase:"Conectar", tag:"Ação útil", image:"assets/psp-06.svg",
      alt:"Ilustração autoral sobre conexão com pessoas e recursos de apoio",
      title:"Ajudar de forma prática e conectar recursos",
      lead:"PSP tornam-se concretos quando a conversa facilita um próximo passo útil: informação confiável, necessidade básica, pessoa de referência, serviço ou apoio disponível.",
      objective:"Converter acolhimento em ação simples, possível e compreendida.",
      field:["Ajude a priorizar um problema de cada vez.","Forneça apenas informações confirmadas e compatíveis com sua função.","Facilite contato com pessoas, serviços ou recursos pertinentes."],
      team:"Para um colega, conexão pode significar companhia, pausa, substituição temporária, contato com chefia ou acesso a suporte institucional.",
      avoid:"Não sobrecarregue com muitas orientações e não encaminhe sem explicar o que acontecerá em seguida.",
      check:"Para onde? Com quem? Qual é o próximo passo?"
    },
    {
      n:"07", phase:"Cuidar", tag:"Entre pares", image:"assets/psp-07.svg",
      alt:"Ilustração autoral sobre apoio entre colegas e cuidado em equipe",
      title:"Cuidar do colega: apoio entre pares",
      lead:"Profissionais de emergência e segurança pública também são afetados por eventos críticos. Apoio entre pares combina observação, aproximação discreta, escuta, ajuda prática e conexão com suporte quando necessário.",
      objective:"Oferecer ajuda sem estigmatizar, expor ou assumir o papel de terapeuta do colega.",
      field:["Observe mudanças relevantes no funcionamento após ocorrências exigentes.","Ofereça ajuda específica: água, pausa, companhia, informação ou reorganização de tarefa.","Facilite acesso aos recursos institucionais quando o apoio entre pares não for suficiente."],
      team:"Uma cultura de segurança trata pedir ajuda como comportamento profissional, não como falha pessoal.",
      avoid:"Não faça diagnóstico informal, não exponha confidências e não pressione o colega a falar diante da equipe.",
      check:"O que pode reduzir a carga deste colega agora sem retirar sua autonomia?"
    },
    {
      n:"08", phase:"Cuidar", tag:"Autocuidado", image:"assets/psp-08.svg",
      alt:"Ilustração autoral sobre autocuidado operacional e recuperação",
      title:"Cuidar de si: autocuidado operacional",
      lead:"Autocuidado operacional ajuda a preservar atenção, julgamento e comunicação. Ele não substitui condições adequadas de trabalho, apoio de equipe ou gestão da carga, mas integra uma resposta profissional sustentável.",
      objective:"Reconhecer medidas básicas de preservação funcional antes, durante e depois de ocorrências exigentes.",
      field:["Proteja necessidades básicas possíveis: hidratação, alimentação, descanso e pausas.","Alterne tarefas de alta carga quando a organização da operação permitir.","Após a ocorrência, favoreça recuperação gradual, rotina e suporte social."],
      team:"Chefias e pares podem apoiar a recuperação com rodízio, informação clara, pausas e acesso sem estigma aos recursos institucionais.",
      avoid:"Não normalize exaustão extrema como prova de comprometimento e não imponha uma única forma de processar a experiência.",
      check:"Minha atenção, julgamento e comunicação continuam adequados para a função?"
    },
    {
      n:"09", phase:"Limites", tag:"Ética", image:"assets/psp-09.svg",
      alt:"Ilustração autoral sobre limites profissionais e proteção ética",
      title:"Limites profissionais: o que fazer e o que evitar",
      lead:"Limites claros protegem a pessoa atendida, o colega e a confiança institucional. PSP exigem honestidade sobre o que o profissional sabe, pode fazer e deve encaminhar.",
      objective:"Evitar intervenções que aumentem dependência, vergonha, confusão ou exposição desnecessária.",
      field:["Seja honesto sobre possibilidades e limites.","Compartilhe somente informações necessárias à continuidade e conforme normas institucionais.","Mantenha linguagem respeitosa e não julgadora."],
      team:"Apoio entre pares não substitui avaliação especializada quando há prejuízo importante e persistente do funcionamento.",
      avoid:"Evite falsas garantias, conselhos moralizantes, comparações de sofrimento, exposição pública e debriefing emocional obrigatório.",
      check:"Minha forma de ajudar preserva dignidade, privacidade e autonomia?"
    },
    {
      n:"10", phase:"Encerrar", tag:"Continuidade", image:"assets/psp-10.svg",
      alt:"Ilustração autoral sobre continuidade do cuidado e passagem segura",
      title:"Encerrar: próximo passo, passagem e reorganização da equipe",
      lead:"O apoio inicial termina melhor quando a pessoa compreende o que foi combinado, quem seguirá responsável e como acessar o recurso seguinte. A equipe também precisa reorganizar-se após atuações exigentes.",
      objective:"Finalizar PSP com continuidade clara e sem criar dependência desnecessária.",
      field:["Resuma necessidades identificadas e ações realizadas.","Confirme o próximo recurso ou responsável.","Faça passagem objetiva das informações necessárias, respeitando privacidade e protocolos."],
      team:"Depois da ocorrência, faça uma checagem operacional de necessidades da equipe e facilite suporte adicional para quem precisar.",
      avoid:"Não prolongue o contato sem finalidade e não transforme revisão operacional em exposição emocional obrigatória.",
      check:"Necessidade principal encaminhada • próximo passo compreendido • equipe reorganizada."
    }
  ];

  function cardMarkup(c) {
    return `<article class="psp-card">
      <div class="psp-media"><img src="${c.image}" alt="${c.alt}" loading="lazy" decoding="async"></div>
      <div class="psp-content">
        <div class="psp-top"><span class="psp-step">Card ${c.n} • ${c.phase}</span><span class="psp-tag">${c.tag}</span></div>
        <h3>${c.title}</h3>
        <p class="psp-lead">${c.lead}</p>
        <div class="psp-objective"><strong>Objetivo de aprendizagem</strong><p>${c.objective}</p></div>
        <div class="psp-block"><strong>Aplicação no campo</strong><ul>${c.field.map(item => `<li>${item}</li>`).join("")}</ul></div>
        <div class="psp-block psp-team"><strong>Colega e equipe</strong><p>${c.team}</p></div>
        <div class="psp-block psp-avoid"><strong>Evite</strong><p>${c.avoid}</p></div>
        <p class="psp-check"><strong>Microchecagem:</strong> ${c.check}</p>
      </div>
    </article>`;
  }

  function openPsp() {
    const panel = document.getElementById("libraryPanel");
    const kicker = document.getElementById("activeSeriesKicker");
    const title = document.getElementById("activeSeriesTitle");
    const description = document.getElementById("activeSeriesDescription");
    const audioTip = document.getElementById("audioTip");
    const episodeList = document.getElementById("episodeList");
    if (!panel || !kicker || !title || !description || !episodeList) return;

    if (audioTip) audioTip.hidden = true;
    kicker.textContent = "Série 3 • 10 cards • PSP";
    title.textContent = "Primeiros Socorros Psicológicos";
    description.textContent = "Trilha visual para profissionais de emergência e segurança pública: apoio à pessoa atendida, cuidado entre pares e autocuidado operacional.";
    episodeList.innerHTML = `<div class="psp-shell">
      <div class="psp-path" aria-label="Progressão da trilha de PSP">
        <div class="psp-path-step"><strong>Preparar</strong><span>contexto e recursos</span></div>
        <div class="psp-path-step"><strong>Observar</strong><span>segurança e prioridades</span></div>
        <div class="psp-path-step"><strong>Escutar</strong><span>contato e necessidades</span></div>
        <div class="psp-path-step"><strong>Conectar</strong><span>apoio e continuidade</span></div>
        <div class="psp-path-step"><strong>Cuidar</strong><span>colega, equipe e si</span></div>
      </div>
      <div class="psp-intro">Use os cards em sequência na primeira leitura. Depois, eles funcionam como consulta rápida. PSP são apoio humano, prático e respeitoso e não substituem protocolos operacionais nem atendimento especializado quando necessário.</div>
      <div class="psp-grid">${PSP_CARDS.map(cardMarkup).join("")}</div>
      <div class="psp-references"><strong>Base técnica</strong><p>Conteúdo estruturado a partir do guia de Primeiros Socorros Psicológicos da OMS/WHO e da versão em português da OPAS. <a href="https://www.who.int/publications-detail-redirect/9789241548205" target="_blank" rel="noopener noreferrer">OMS/WHO</a> • <a href="https://iris.paho.org/handle/10665.2/7676" target="_blank" rel="noopener noreferrer">OPAS/OMS em português</a>.</p></div>
    </div>`;
    panel.classList.add("is-open");
    setTimeout(() => panel.scrollIntoView({behavior:"smooth", block:"start"}), 40);
  }

  function enhancePage() {
    const cards = [...document.querySelectorAll(".series-card")];
    const button = document.querySelector('button[data-series-id="3"]');
    const card = button?.closest(".series-card") || cards[2];
    if (!card || !button) return;

    card.dataset.series = "3";
    const image = card.querySelector(".series-media img");
    const heading = card.querySelector(".series-body h3");
    const description = card.querySelector(".series-body p");
    const meta = card.querySelector(".series-meta");

    if (image) {
      image.src = PSP_IMAGE;
      image.alt = "Paramédico oferecendo presença e apoio a uma pessoa junto a uma ambulância";
      image.referrerPolicy = "no-referrer";
    }
    if (heading) heading.textContent = "Primeiros Socorros Psicológicos";
    if (description) description.textContent = "Trilha prática e progressiva de PSP para profissionais de emergência e segurança pública, incluindo cuidado com a pessoa, com o colega e consigo.";
    if (meta) meta.innerHTML = '<span class="pill available">Disponível</span><span class="pill">10 cards</span>';

    button.disabled = false;
    button.classList.remove("ghost");
    button.textContent = "Abrir trilha de PSP";
    button.addEventListener("click", openPsp);

    const aboutItems = document.querySelectorAll(".about-list li");
    if (aboutItems[2]) aboutItems[2].innerHTML = "<strong>Série 3:</strong> Primeiros Socorros Psicológicos.";

    const heroText = document.querySelector(".hero-text");
    if (heroText) heroText.textContent = "Conteúdos complementares para escuta, reflexão técnica e aprofundamento em abordagem, compreensão do sofrimento em crise e Primeiros Socorros Psicológicos.";

    const aboutLead = document.querySelector(".about-summary p");
    if (aboutLead) aboutLead.textContent = "O projeto organiza conteúdos de apoio à formação técnica em ATS e uma trilha visual de Primeiros Socorros Psicológicos para profissionais de emergência e segurança pública.";
  }

  function init() {
    window.setTimeout(enhancePage, 0);
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init, {once:true});
  else init();
})();