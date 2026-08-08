(() => {
  "use strict";

  const PSP_IMAGE = "https://images.pexels.com/photos/6519869/pexels-photo-6519869.jpeg?auto=compress&cs=tinysrgb&w=1200&h=1500&fit=crop";
  const STATE_PREFIX = "gav:psp-audio:";
  let CARDS = [];

  const pad = n => String(n).padStart(2, "0");
  const audioUrl = index => `assets/audio/serie-3/psp-${pad(index + 1)}.mp3`;
  const format = seconds => {
    const total = Math.max(0, Math.floor(Number(seconds) || 0));
    return `${String(Math.floor(total / 60)).padStart(2, "0")}:${String(total % 60).padStart(2, "0")}`;
  };

  function loadState(index) {
    try {
      return { time: 0, completed: false, ...JSON.parse(localStorage.getItem(STATE_PREFIX + pad(index + 1)) || "{}") };
    } catch {
      return { time: 0, completed: false };
    }
  }

  function saveState(index, state) {
    try {
      localStorage.setItem(STATE_PREFIX + pad(index + 1), JSON.stringify(state));
    } catch {}
  }

  async function loadCards() {
    const response = await fetch("psp-cards.json", { cache: "no-store" });
    if (!response.ok) throw new Error("Não foi possível carregar os cards PSP.");
    CARDS = await response.json();
  }

  function pauseAllAudio(except = null) {
    document.querySelectorAll("audio").forEach(audio => {
      if (audio !== except && !audio.paused) audio.pause();
    });
  }

  function updateAudioUi(card) {
    if (!card) return;
    const index = Number(card.dataset.pspIndex);
    const audio = card.querySelector("audio[data-psp-audio]");
    const status = card.querySelector("[data-audio-status]");
    const reset = card.querySelector("[data-audio-reset]");
    const state = loadState(index);
    if (!status || !audio) return;

    if (state.completed) status.textContent = "Concluído";
    else if (!audio.paused && !audio.ended) status.textContent = `Em ${format(audio.currentTime)}`;
    else if (state.time > 1) status.textContent = `Retomar em ${format(state.time)}`;
    else status.textContent = "Novo";

    if (reset) reset.hidden = !(state.completed || state.time > 1 || audio.currentTime > 1);
  }

  function bindPspAudio(card) {
    const index = Number(card.dataset.pspIndex);
    const audio = card.querySelector("audio[data-psp-audio]");
    const reset = card.querySelector("[data-audio-reset]");
    if (!audio) return;

    audio.addEventListener("loadedmetadata", () => {
      const state = loadState(index);
      if (!state.completed && state.time > 1 && state.time < audio.duration - 2) {
        audio.currentTime = state.time;
      }
      updateAudioUi(card);
    });

    audio.addEventListener("play", () => {
      pauseAllAudio(audio);
      const state = loadState(index);
      saveState(index, { time: audio.currentTime || state.time || 0, completed: false });
      updateAudioUi(card);
    });

    audio.addEventListener("pause", () => {
      if (!audio.ended) {
        saveState(index, { time: audio.currentTime || 0, completed: false });
        updateAudioUi(card);
      }
    });

    audio.addEventListener("timeupdate", () => {
      if (!audio.paused && Number.isFinite(audio.currentTime)) {
        saveState(index, { time: audio.currentTime, completed: false });
        updateAudioUi(card);
      }
    });

    audio.addEventListener("ended", () => {
      saveState(index, { time: 0, completed: true });
      updateAudioUi(card);
    });

    audio.addEventListener("error", () => {
      const status = card.querySelector("[data-audio-status]");
      if (status) status.textContent = "Áudio temporariamente indisponível";
    });

    if (reset) {
      reset.addEventListener("click", () => {
        audio.pause();
        audio.currentTime = 0;
        saveState(index, { time: 0, completed: false });
        updateAudioUi(card);
      });
    }
  }

  function audioMarkup(card, index) {
    const src = audioUrl(index);
    return `<section class="psp-audio" aria-label="Microaula em áudio do Card ${card.n}">
      <div class="psp-audio-head">
        <div>
          <span class="psp-audio-kicker">Microaula em áudio</span>
          <strong>${card.title}</strong>
        </div>
        <span class="psp-audio-duration">2–4 min</span>
      </div>
      <p class="psp-audio-note">Ouça uma explicação aplicada deste card. O conteúdo escrito permanece integralmente disponível para consulta.</p>
      <audio data-psp-audio controls preload="metadata" style="width:100%;max-width:100%" aria-label="Microaula ${card.n}: ${card.title}">
        <source src="${src}" type="audio/mpeg">
        Seu navegador não suporta áudio HTML5.
      </audio>
      <div class="psp-audio-controls">
        <span class="psp-audio-status" data-audio-status>Novo</span>
        <button class="psp-audio-reset" type="button" data-audio-reset hidden>Reiniciar áudio</button>
      </div>
    </section>`;
  }

  function cardMarkup(card, index) {
    const detailId = `psp-detail-${index + 1}`;
    return `<article class="psp-card" data-psp-index="${index}">
      <button class="psp-card-toggle" type="button" aria-expanded="false" aria-controls="${detailId}">
        <div class="psp-media"><img src="${card.image}" alt="${card.alt}" loading="lazy" decoding="async"></div>
        <div class="psp-summary">
          <div class="psp-top"><span class="psp-step">Card ${card.n} • ${card.phase}</span><span class="psp-tag">${card.tag}</span></div>
          <h3>${card.title}</h3>
          <div class="psp-summary-meta"><span class="psp-audio-chip">Áudio • 2–4 min</span><span class="psp-open-label">Abrir conteúdo <span aria-hidden="true">＋</span></span></div>
        </div>
      </button>
      <div class="psp-card-details" id="${detailId}" hidden>
        <p class="psp-lead">${card.lead}</p>
        <p class="psp-context">${card.context}</p>
        ${audioMarkup(card, index)}
        <div class="psp-objective"><strong>Objetivo de aprendizagem</strong><p>${card.objective}</p></div>
        <div class="psp-block"><strong>Aplicação no trabalho</strong><ul>${card.field.map(item => `<li>${item}</li>`).join("")}</ul></div>
        <div class="psp-block psp-team"><strong>Colega e equipe</strong><p>${card.team}</p></div>
        <div class="psp-block psp-avoid"><strong>Evite</strong><p>${card.avoid}</p></div>
        <p class="psp-check"><strong>Microchecagem:</strong> ${card.check}</p>
      </div>
    </article>`;
  }

  function closeAllCards(exceptCard = null) {
    document.querySelectorAll(".psp-card").forEach(card => {
      if (card === exceptCard) return;
      card.querySelector("audio[data-psp-audio]")?.pause();
      card.classList.remove("is-open");
      const toggle = card.querySelector(".psp-card-toggle");
      const details = card.querySelector(".psp-card-details");
      const label = card.querySelector(".psp-open-label");
      if (toggle) toggle.setAttribute("aria-expanded", "false");
      if (details) details.hidden = true;
      if (label) label.innerHTML = 'Abrir conteúdo <span aria-hidden="true">＋</span>';
    });
  }

  function bindPspCards() {
    document.querySelectorAll(".psp-card").forEach(card => {
      bindPspAudio(card);
      updateAudioUi(card);
    });

    document.querySelectorAll(".psp-card-toggle").forEach(toggle => {
      toggle.addEventListener("click", () => {
        const card = toggle.closest(".psp-card");
        const details = card?.querySelector(".psp-card-details");
        const label = card?.querySelector(".psp-open-label");
        if (!card || !details) return;

        const opening = toggle.getAttribute("aria-expanded") !== "true";
        closeAllCards(opening ? card : null);
        if (!opening) card.querySelector("audio[data-psp-audio]")?.pause();

        card.classList.toggle("is-open", opening);
        toggle.setAttribute("aria-expanded", String(opening));
        details.hidden = !opening;
        if (label) label.innerHTML = opening
          ? 'Ocultar conteúdo <span aria-hidden="true">−</span>'
          : 'Abrir conteúdo <span aria-hidden="true">＋</span>';

        if (opening) {
          updateAudioUi(card);
          window.setTimeout(() => card.scrollIntoView({ behavior: "smooth", block: "start" }), 40);
        }
      });
    });
  }

  function returnToSeries() {
    pauseAllAudio();
    const back = document.getElementById("backToSeries");
    if (back) back.click();
    else document.getElementById("series")?.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  function endActionMarkup(label = "Fechar esta série e voltar à página inicial") {
    return `<div class="series-end-action"><button class="btn ghost series-end-button" type="button">${label}</button></div>`;
  }

  function bindEndButtons(root = document) {
    root.querySelectorAll(".series-end-button").forEach(button => {
      if (button.dataset.bound === "1") return;
      button.dataset.bound = "1";
      button.addEventListener("click", returnToSeries);
    });
  }

  function ensureAudioEndAction() {
    const list = document.getElementById("episodeList");
    if (!list || !list.children.length || list.querySelector(".psp-shell")) return;
    if (!list.querySelector(".series-end-action")) list.insertAdjacentHTML("beforeend", endActionMarkup());
    bindEndButtons(list);
  }

  function openPsp() {
    const panel = document.getElementById("libraryPanel");
    const kicker = document.getElementById("activeSeriesKicker");
    const title = document.getElementById("activeSeriesTitle");
    const description = document.getElementById("activeSeriesDescription");
    const audioTip = document.getElementById("audioTip");
    const episodeList = document.getElementById("episodeList");
    if (!panel || !kicker || !title || !description || !episodeList) return;

    pauseAllAudio();
    if (audioTip) audioTip.hidden = true;
    kicker.textContent = "Série 3 • 10 cards • 10 microaulas";
    title.textContent = "Primeiros Socorros Psicológicos no Trabalho";
    description.textContent = "PSP aplicado à prevenção em saúde mental de profissionais de segurança e emergência: reconhecer mudanças, aproximar, escutar, conectar e cuidar.";

    episodeList.innerHTML = `<div class="psp-shell">
      <div class="psp-path" aria-label="Progressão da trilha de PSP">
        <div class="psp-path-step"><strong>Preparar</strong><span>momento, lugar e postura</span></div>
        <div class="psp-path-step"><strong>Observar</strong><span>mudanças e funcionamento</span></div>
        <div class="psp-path-step"><strong>Escutar</strong><span>presença e necessidades</span></div>
        <div class="psp-path-step"><strong>Conectar</strong><span>apoio e próximo passo</span></div>
        <div class="psp-path-step"><strong>Cuidar</strong><span>colega, equipe e si</span></div>
      </div>
      <div class="psp-intro"><strong>Como usar:</strong> esta trilha foi construída para profissionais de segurança e emergência. Na primeira leitura, siga a ordem numérica; depois, use os cards como consulta rápida para reconhecer mudanças, preparar uma abordagem, observar, escutar, conectar, acompanhar e praticar autocuidado. O progresso dos áudios fica salvo neste dispositivo.</div>
      <div class="psp-grid">${CARDS.map(cardMarkup).join("")}</div>
      <div class="psp-references"><strong>Base técnica</strong><p>Conteúdo estruturado a partir do guia de Primeiros Socorros Psicológicos da OMS/WHO e da versão em português da OPAS, adaptado ao contexto de prevenção em saúde mental e apoio entre pares no trabalho. <a href="https://www.who.int/publications-detail-redirect/9789241548205" target="_blank" rel="noopener noreferrer">OMS/WHO</a> • <a href="https://iris.paho.org/handle/10665.2/7676" target="_blank" rel="noopener noreferrer">OPAS/OMS em português</a>.</p></div>
      ${endActionMarkup("Fechar a trilha de PSP e voltar à página inicial")}
    </div>`;

    bindPspCards();
    bindEndButtons(episodeList);
    panel.classList.add("is-open");
    window.setTimeout(() => panel.scrollIntoView({ behavior: "smooth", block: "start" }), 40);
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
      image.alt = "Profissional de emergência oferecendo presença e apoio a um colega";
      image.referrerPolicy = "no-referrer";
    }
    if (heading) heading.textContent = "Primeiros Socorros Psicológicos no Trabalho";
    if (description) description.textContent = "Trilha prática de prevenção em saúde mental e apoio entre pares para profissionais de segurança e emergência.";
    if (meta) meta.innerHTML = '<span class="pill available">Disponível</span><span class="pill">10 cards + 10 áudios</span>';

    button.disabled = false;
    button.classList.remove("ghost");
    button.textContent = "Abrir trilha de PSP";
    if (button.dataset.pspBound !== "1") {
      button.dataset.pspBound = "1";
      button.addEventListener("click", openPsp);
    }

    const aboutItems = document.querySelectorAll(".about-list li");
    if (aboutItems[2]) aboutItems[2].innerHTML = "<strong>Série 3:</strong> Primeiros Socorros Psicológicos no Trabalho — prevenção em saúde mental, apoio entre pares e autocuidado.";
  }

  function observeSeriesContent() {
    const list = document.getElementById("episodeList");
    if (!list) return;
    const observer = new MutationObserver(() => window.setTimeout(ensureAudioEndAction, 0));
    observer.observe(list, { childList: true, subtree: false });
  }

  async function init() {
    try {
      await loadCards();
      enhancePage();
      observeSeriesContent();
    } catch (error) {
      console.error("Falha ao inicializar a Série 3 de PSP:", error);
    }
  }

  document.readyState === "loading"
    ? document.addEventListener("DOMContentLoaded", init, { once: true })
    : init();
})();