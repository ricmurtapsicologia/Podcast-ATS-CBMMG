(() => {
  "use strict";

  let cardsPromise = null;
  const pad = value => String(value).padStart(2, "0");
  const format = seconds => {
    const total = Math.max(0, Math.floor(Number(seconds) || 0));
    return `${String(Math.floor(total / 60)).padStart(2, "0")}:${String(total % 60).padStart(2, "0")}`;
  };
  const reducedMotion = () => window.matchMedia?.("(prefers-reduced-motion: reduce)")?.matches === true;

  function loadCards() {
    if (!cardsPromise) {
      cardsPromise = fetch("psp-cards.json", {cache:"no-store"}).then(response => {
        if (!response.ok) throw new Error("Não foi possível carregar os cards PSP.");
        return response.json();
      });
    }
    return cardsPromise;
  }

  function itemId(index) { return `psp-${pad(index + 1)}`; }
  function audioUrl(index) { return `assets/audio/serie-3/psp-${pad(index + 1)}-n3.mp3`; }

  function stateLabel(storage, id) {
    const state = storage.get(id);
    if (state.completed) return "Concluído";
    if (state.position > 1) return `Retomar em ${format(state.position)}`;
    return "Novo";
  }

  function cardMarkup(card, index, storage) {
    const id = itemId(index);
    const state = storage.get(id);
    const detailsId = `psp-detail-${pad(index + 1)}`;
    return `<article class="psp-card${state.completed ? " is-complete" : ""}" data-psp-id="${id}">
      <button class="psp-card-toggle" type="button" aria-expanded="false" aria-controls="${detailsId}">
        <div class="psp-media"><img src="${card.image}" alt="${card.alt}" loading="lazy" decoding="async"></div>
        <div class="psp-summary">
          <div class="psp-top"><span class="psp-step">Card ${card.n} • ${card.phase}</span><span class="psp-tag">${card.tag}</span></div>
          <h3>${card.title}</h3>
          <div class="psp-summary-meta"><span class="psp-audio-chip">Microaula em áudio</span><span class="psp-card-state">${stateLabel(storage, id)}</span><span class="psp-open-label">Abrir conteúdo <span aria-hidden="true">＋</span></span></div>
        </div>
      </button>
      <div class="psp-card-details" id="${detailsId}" hidden>
        <p class="psp-lead">${card.lead}</p>
        <p class="psp-context">${card.context}</p>
        <div class="psp-objective"><strong>Objetivo de aprendizagem</strong><p>${card.objective}</p></div>
        <div class="psp-block"><strong>Aplicação no trabalho</strong><ul>${card.field.map(item => `<li>${item}</li>`).join("")}</ul></div>
        <div class="psp-block psp-team"><strong>Colega e equipe</strong><p>${card.team}</p></div>
        <div class="psp-block psp-avoid"><strong>Evite</strong><p>${card.avoid}</p></div>
        <p class="psp-check"><strong>Microchecagem:</strong> ${card.check}</p>
        <button class="btn secondary psp-listen" type="button" data-listen="${id}">${state.completed ? "Reouvir microaula" : state.position > 1 ? "Continuar microaula" : "Ouvir microaula"}</button>
      </div>
    </article>`;
  }

  function stats(cards, storage) {
    let completed = 0;
    let started = 0;
    cards.forEach((_, index) => {
      const state = storage.get(itemId(index));
      if (state.completed) completed += 1;
      if (state.completed || state.position > 1) started += 1;
    });
    return {completed, started, total:cards.length, percent:Math.round((completed / Math.max(1, cards.length)) * 100)};
  }

  async function render({series, root, storage, targetItemId = null, onStateChange = () => {}, onNavigate = () => {}, onClose = () => {}, announce = () => {}}) {
    const cards = await loadCards();
    const summary = stats(cards, storage);
    root.innerHTML = `
      <div class="learning-toolbar psp-learning-toolbar">
        <div class="learning-progress-summary">
          <strong>${summary.completed} de ${summary.total} concluídos</strong>
          <span>${summary.percent}% da trilha</span>
          <div class="learning-progress-track" aria-label="Progresso da trilha: ${summary.percent}%"><span style="width:${summary.percent}%"></span></div>
        </div>
      </div>
      <section class="active-player psp-active-player" id="pspActivePlayer" aria-labelledby="pspPlayerTitle">
        <div class="active-player-copy"><span class="section-kicker">Microaula</span><h3 id="pspPlayerTitle">Selecione um card</h3><p id="pspPlayerStatus">Abra um card e escolha “Ouvir microaula”.</p></div>
        <audio id="pspSharedAudio" controls preload="none" aria-label="Player das microaulas de PSP"></audio>
        <div class="player-actions"><button id="pspReset" class="text-action" type="button" hidden>Reiniciar microaula</button><button id="pspNext" class="btn secondary" type="button" hidden>Próximo card</button></div>
      </section>
      <div class="psp-path" aria-label="Estrutura da trilha">
        <div class="psp-path-step"><strong>Preparar</strong><span>antes do contato</span></div>
        <div class="psp-path-step"><strong>Observar</strong><span>segurança e necessidades</span></div>
        <div class="psp-path-step"><strong>Escutar</strong><span>presença e compreensão</span></div>
        <div class="psp-path-step"><strong>Conectar</strong><span>apoio prático e recursos</span></div>
        <div class="psp-path-step"><strong>Cuidar</strong><span>continuidade e equipe</span></div>
      </div>
      <div class="psp-intro"><strong>Como usar:</strong> na primeira passagem, siga os cards em ordem. Depois, use a trilha como consulta rápida. O conteúdo aplica princípios de Primeiros Socorros Psicológicos da OMS ao contexto educacional de prevenção em saúde mental, apoio entre pares e autocuidado operacional.</div>
      <div class="psp-grid" id="pspGrid">${cards.map((card, index) => cardMarkup(card, index, storage)).join("")}</div>
      <div class="psp-references"><strong>Base técnica e escopo</strong><p>Conteúdo baseado no guia de Primeiros Socorros Psicológicos da OMS/WHO e na versão em português da OPAS. A aplicação ao apoio entre pares e à prevenção em saúde mental de profissionais de segurança e emergência é uma adaptação educacional deste projeto. <a href="https://www.who.int/publications-detail-redirect/9789241548205" target="_blank" rel="noopener noreferrer">OMS/WHO</a> • <a href="https://iris.paho.org/handle/10665.2/7676" target="_blank" rel="noopener noreferrer">OPAS/OMS</a>.</p></div>
      <div class="series-end-action"><button class="btn ghost" type="button" data-psp-close>Fechar esta trilha e voltar às séries</button></div>`;

    const audio = root.querySelector("#pspSharedAudio");
    const title = root.querySelector("#pspPlayerTitle");
    const status = root.querySelector("#pspPlayerStatus");
    const reset = root.querySelector("#pspReset");
    const next = root.querySelector("#pspNext");
    let activeIndex = -1;
    let activeId = null;
    let saveTick = 0;

    function updateSummary() {
      const current = stats(cards, storage);
      const box = root.querySelector(".learning-progress-summary");
      if (box) box.innerHTML = `<strong>${current.completed} de ${current.total} concluídos</strong><span>${current.percent}% da trilha</span><div class="learning-progress-track" aria-label="Progresso da trilha: ${current.percent}%"><span style="width:${current.percent}%"></span></div>`;
      root.querySelectorAll(".psp-card").forEach((card, index) => {
        const id = itemId(index);
        const state = storage.get(id);
        card.classList.toggle("is-complete", state.completed);
        const badge = card.querySelector(".psp-card-state");
        const listen = card.querySelector(".psp-listen");
        if (badge) badge.textContent = stateLabel(storage, id);
        if (listen) listen.textContent = state.completed ? "Reouvir microaula" : state.position > 1 ? "Continuar microaula" : "Ouvir microaula";
      });
      onStateChange();
    }

    function updatePlayer() {
      if (activeIndex < 0) return;
      const card = cards[activeIndex];
      const state = storage.get(activeId);
      if (title) title.textContent = `Card ${card.n}: ${card.title}`;
      if (status) status.textContent = state.completed ? "Concluído. Você pode reouvir ou seguir para o próximo card." : state.position > 1 ? `Progresso salvo em ${format(state.position)}.` : "Pronto para ouvir.";
      if (reset) reset.hidden = !(state.completed || state.position > 1);
      if (next) {
        next.hidden = activeIndex >= cards.length - 1;
        if (!next.hidden) next.textContent = `Próximo: Card ${cards[activeIndex + 1].n}`;
      }
    }

    function closeOtherCards(except = null) {
      root.querySelectorAll(".psp-card").forEach(card => {
        if (card === except) return;
        card.classList.remove("is-open");
        const toggle = card.querySelector(".psp-card-toggle");
        const details = card.querySelector(".psp-card-details");
        const label = card.querySelector(".psp-open-label");
        toggle?.setAttribute("aria-expanded", "false");
        if (details) details.hidden = true;
        if (label) label.innerHTML = 'Abrir conteúdo <span aria-hidden="true">＋</span>';
      });
    }

    function openCard(index, shouldScroll = false) {
      const card = root.querySelectorAll(".psp-card")[index];
      if (!card) return;
      closeOtherCards(card);
      card.classList.add("is-open");
      const toggle = card.querySelector(".psp-card-toggle");
      const details = card.querySelector(".psp-card-details");
      const label = card.querySelector(".psp-open-label");
      toggle?.setAttribute("aria-expanded", "true");
      if (details) details.hidden = false;
      if (label) label.innerHTML = 'Ocultar conteúdo <span aria-hidden="true">−</span>';
      onNavigate(itemId(index));
      if (shouldScroll) card.scrollIntoView({behavior:reducedMotion() ? "auto" : "smooth", block:"start"});
    }

    function selectAudio(index, shouldScroll = true) {
      if (!audio || !cards[index]) return;
      audio.pause();
      activeIndex = index;
      activeId = itemId(index);
      const state = storage.get(activeId);
      audio.src = audioUrl(index);
      audio.preload = "metadata";
      audio.load();
      updatePlayer();
      onNavigate(activeId);
      if (shouldScroll) root.querySelector("#pspActivePlayer")?.scrollIntoView({behavior:reducedMotion() ? "auto" : "smooth", block:"center"});
      if (state.completed) announce(`Card ${cards[index].n} já concluído e pronto para reouvir.`);
    }

    root.querySelectorAll(".psp-card-toggle").forEach((toggle, index) => {
      toggle.addEventListener("click", () => {
        const card = toggle.closest(".psp-card");
        const opening = toggle.getAttribute("aria-expanded") !== "true";
        if (opening) openCard(index, false);
        else {
          card?.classList.remove("is-open");
          card?.querySelector(".psp-card-details")?.setAttribute("hidden", "");
          toggle.setAttribute("aria-expanded", "false");
          const label = card?.querySelector(".psp-open-label");
          if (label) label.innerHTML = 'Abrir conteúdo <span aria-hidden="true">＋</span>';
        }
      });
    });

    root.querySelectorAll(".psp-listen").forEach((button, index) => button.addEventListener("click", () => selectAudio(index, true)));
    root.querySelector("[data-psp-close]")?.addEventListener("click", onClose);

    audio?.addEventListener("loadedmetadata", () => {
      if (!activeId) return;
      const state = storage.get(activeId);
      if (!state.completed && state.position > 1 && state.position < audio.duration - 2) audio.currentTime = state.position;
      updatePlayer();
    });
    audio?.addEventListener("play", () => {
      if (!activeId) return;
      storage.set(activeId, {completed:false, lastPlayedAt:new Date().toISOString()});
      updateSummary();
      announce(`Reproduzindo Card ${cards[activeIndex].n}: ${cards[activeIndex].title}`);
    });
    audio?.addEventListener("timeupdate", () => {
      if (!activeId || audio.paused || !Number.isFinite(audio.currentTime)) return;
      const now = Date.now();
      if (now - saveTick < 1400) return;
      saveTick = now;
      storage.set(activeId, {position:audio.currentTime, completed:false, lastPlayedAt:new Date().toISOString()});
      updatePlayer();
    });
    audio?.addEventListener("pause", () => {
      if (!activeId || audio.ended) return;
      storage.set(activeId, {position:audio.currentTime || 0, completed:false, lastPlayedAt:new Date().toISOString()});
      updateSummary();
      updatePlayer();
    });
    audio?.addEventListener("ended", () => {
      if (!activeId) return;
      storage.set(activeId, {position:0, completed:true, lastPlayedAt:new Date().toISOString()});
      updateSummary();
      updatePlayer();
      announce(`Card ${cards[activeIndex].n} concluído. Próximo card disponível.`);
    });
    audio?.addEventListener("error", () => {
      if (status) status.textContent = "Microaula temporariamente indisponível. Tente novamente em instantes.";
      announce("Não foi possível carregar esta microaula.");
    });
    reset?.addEventListener("click", () => {
      if (!activeId || !audio) return;
      audio.pause();
      audio.currentTime = 0;
      storage.set(activeId, {position:0, completed:false, lastPlayedAt:new Date().toISOString()});
      updateSummary();
      updatePlayer();
    });
    next?.addEventListener("click", () => {
      if (activeIndex < 0 || activeIndex >= cards.length - 1) return;
      openCard(activeIndex + 1, true);
      selectAudio(activeIndex + 1, true);
    });

    if (targetItemId) {
      const index = cards.findIndex((_, idx) => itemId(idx) === targetItemId);
      if (index >= 0) {
        openCard(index, false);
        selectAudio(index, false);
      }
    }
  }

  window.GAV_PSP = Object.freeze({render});
})();
