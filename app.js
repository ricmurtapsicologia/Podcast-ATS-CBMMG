(() => {
  "use strict";

  const manifest = window.GAV_MANIFEST;
  if (!manifest?.series?.length) throw new Error("GAV_MANIFEST ausente ou inválido.");

  const seriesById = Object.fromEntries(manifest.series.map(series => [series.id, series]));
  const itemById = new Map();
  manifest.series.forEach(series => (series.items || []).forEach(item => itemById.set(item.id, {series, item})));

  const LS = {
    ONBOARD: "gav:v4:onboard-done",
    LAST: "gav:v4:last-item",
    FILTER: seriesId => `gav:v4:filter:${seriesId}`,
    ITEM: itemId => `gav:v4:item:${itemId}`,
    LEGACY_LAST: "gav:last_series_v2",
    LEGACY_PROGRESS: url => `gav:progress:${url}`
  };

  const $ = (selector, root = document) => root.querySelector(selector);
  const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];
  const reducedMotion = () => window.matchMedia?.("(prefers-reduced-motion: reduce)")?.matches === true;
  const smooth = () => reducedMotion() ? "auto" : "smooth";
  const formatTime = seconds => {
    const value = Math.max(0, Math.floor(Number(seconds) || 0));
    return `${String(Math.floor(value / 60)).padStart(2, "0")}:${String(value % 60).padStart(2, "0")}`;
  };

  const dom = {
    body: document.body,
    onboarding: $("#onboarding"),
    onboardStart: $("#onboardStart"),
    onboardSkip: $("#onboardSkip"),
    aboutOpen: $("#aboutOpen"),
    aboutToggle: $("#aboutToggle"),
    aboutContent: $("#aboutContent"),
    heroPrimary: $("#heroPrimary"),
    heroProgress: $("#heroProgress"),
    seriesGrid: $("#seriesGrid"),
    panel: $("#libraryPanel"),
    kicker: $("#activeSeriesKicker"),
    title: $("#activeSeriesTitle"),
    desc: $("#activeSeriesDescription"),
    list: $("#episodeList"),
    tip: $("#audioTip"),
    back: $("#backToSeries"),
    live: $("#appStatus")
  };

  let lastFocus = null;
  let activeSeries = null;
  let activeItem = null;
  let audio = null;
  let saveTick = 0;
  let searchQuery = "";
  let filterMode = "all";

  const storage = {
    get(itemId) {
      try {
        const raw = localStorage.getItem(LS.ITEM(itemId));
        if (!raw) return {position:0, completed:false, lastPlayedAt:null};
        const parsed = JSON.parse(raw);
        return {
          position: Math.max(0, Number(parsed.position) || 0),
          completed: Boolean(parsed.completed),
          lastPlayedAt: parsed.lastPlayedAt || null
        };
      } catch {
        return {position:0, completed:false, lastPlayedAt:null};
      }
    },
    set(itemId, patch) {
      try {
        const current = this.get(itemId);
        const next = {...current, ...patch};
        localStorage.setItem(LS.ITEM(itemId), JSON.stringify(next));
        return next;
      } catch {
        return {...this.get(itemId), ...patch};
      }
    },
    setLast(seriesId, itemId) {
      try {
        localStorage.setItem(LS.LAST, JSON.stringify({seriesId, itemId, at:new Date().toISOString()}));
      } catch {}
    },
    getLast() {
      try {
        const raw = localStorage.getItem(LS.LAST);
        if (raw) {
          const value = JSON.parse(raw);
          if (seriesById[value.seriesId]) return value;
        }
      } catch {}
      return null;
    },
    migrateLegacy() {
      manifest.series.forEach(series => {
        (series.items || []).forEach(item => {
          try {
            if (localStorage.getItem(LS.ITEM(item.id))) return;
            const raw = localStorage.getItem(LS.LEGACY_PROGRESS(item.url));
            if (raw == null) return;
            const position = Math.max(0, parseFloat(raw) || 0);
            if (position > 0) this.set(item.id, {position, completed:false, lastPlayedAt:null});
          } catch {}
        });
      });
      try {
        if (!localStorage.getItem(LS.LAST)) {
          const legacySeries = localStorage.getItem(LS.LEGACY_LAST);
          const series = seriesById[legacySeries];
          if (series?.items?.length) {
            const candidate = series.items.find(item => this.get(item.id).position > 0) || series.items[0];
            this.setLast(series.id, candidate.id);
          }
        }
      } catch {}
    },
    seriesStats(series) {
      const items = series.items || [];
      if (!items.length) return {completed:0, started:0, total:series.itemCount || 0, percent:0};
      let completed = 0;
      let started = 0;
      items.forEach(item => {
        const state = this.get(item.id);
        if (state.completed) completed += 1;
        if (state.completed || state.position > 1) started += 1;
      });
      return {completed, started, total:items.length, percent:Math.round((completed / items.length) * 100)};
    }
  };

  function announce(message) {
    if (!dom.live) return;
    dom.live.textContent = "";
    requestAnimationFrame(() => { dom.live.textContent = message; });
  }

  function scrollTo(element, block = "start") {
    element?.scrollIntoView({behavior:smooth(), block});
  }

  function setAbout(open) {
    dom.aboutContent?.classList.toggle("is-open", open);
    dom.aboutToggle?.setAttribute("aria-expanded", String(open));
    if (dom.aboutToggle) dom.aboutToggle.textContent = open ? "Ocultar proposta" : "Entenda a proposta";
  }

  function getFocusable(root) {
    return $$("a[href],button:not([disabled]),input:not([disabled]),select:not([disabled]),textarea:not([disabled]),[tabindex]:not([tabindex='-1'])", root)
      .filter(el => !el.hidden && el.offsetParent !== null);
  }

  function openOnboard() {
    if (!dom.onboarding) return;
    lastFocus = document.activeElement;
    dom.onboarding.classList.add("is-open");
    dom.onboarding.setAttribute("aria-hidden", "false");
    document.documentElement.style.overflow = "hidden";
    window.setTimeout(() => dom.onboardStart?.focus(), 40);
  }

  function closeOnboard() {
    try { localStorage.setItem(LS.ONBOARD, "1"); } catch {}
    dom.onboarding?.classList.remove("is-open");
    dom.onboarding?.setAttribute("aria-hidden", "true");
    document.documentElement.style.overflow = "";
    lastFocus?.focus?.();
  }

  function trapOnboardFocus(event) {
    if (event.key !== "Tab" || !dom.onboarding?.classList.contains("is-open")) return;
    const focusable = getFocusable(dom.onboarding);
    if (!focusable.length) return;
    const first = focusable[0];
    const last = focusable[focusable.length - 1];
    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault();
      last.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault();
      first.focus();
    }
  }

  function seriesStatus(series) {
    if (series.status === "available") return {label:"Disponível", className:"available"};
    if (series.status === "maintenance") return {label:"Em manutenção", className:"building"};
    return {label:"Em preparação", className:"building"};
  }

  function renderSeries() {
    if (!dom.seriesGrid) return;
    dom.seriesGrid.innerHTML = "";
    manifest.series.forEach(series => {
      const status = seriesStatus(series);
      const stats = storage.seriesStats(series);
      const total = series.items?.length || series.itemCount || 0;
      const progressText = stats.completed > 0 ? `${stats.completed} de ${total} concluídos` : `${total} ${series.kind === "psp" ? "cards" : "episódios"}`;
      const action = series.status === "available" ? (stats.started > 0 ? "Continuar trilha" : (series.kind === "psp" ? "Abrir trilha" : "Explorar episódios")) : "Disponível em breve";
      const card = document.createElement("article");
      card.className = "series-card";
      card.dataset.series = series.id;
      card.innerHTML = `
        <div class="series-media"><img src="${series.image}" alt="${series.alt}" loading="lazy" decoding="async"><span class="series-badge">Série ${series.id}</span></div>
        <div class="series-body">
          <h3>${series.title}</h3>
          <p>${series.description}</p>
          <div class="series-meta"><span class="pill ${status.className}">${status.label}</span><span class="pill">${progressText}</span></div>
          ${stats.total ? `<div class="series-progress" aria-label="Progresso: ${stats.percent}%"><span style="width:${stats.percent}%"></span></div>` : ""}
          <div class="series-actions"><button class="btn ${series.status === "available" ? "" : "ghost"}" type="button" data-series-id="${series.id}" ${series.status === "available" ? "" : "disabled"}>${action}</button></div>
        </div>`;
      const button = $("button", card);
      if (series.status === "available") button?.addEventListener("click", () => openSeries(series.id));
      dom.seriesGrid.appendChild(card);
    });
  }

  function updateHero() {
    const last = storage.getLast();
    const target = last?.itemId ? itemById.get(last.itemId) : null;
    if (last?.seriesId === "3" && last.itemId) {
      const series = seriesById["3"];
      dom.body?.classList.add("has-progress");
      if (dom.heroPrimary) {
        dom.heroPrimary.textContent = "Continuar de onde parei";
        dom.heroPrimary.href = `#serie-3/${last.itemId}`;
      }
      if (dom.heroProgress) {
        dom.heroProgress.hidden = false;
        dom.heroProgress.textContent = `Última trilha: ${series.shortTitle}`;
      }
      return;
    }
    if (target) {
      const state = storage.get(target.item.id);
      dom.body?.classList.add("has-progress");
      if (dom.heroPrimary) {
        dom.heroPrimary.textContent = "Continuar de onde parei";
        dom.heroPrimary.href = `#serie-${target.series.id}/${target.item.id}`;
      }
      if (dom.heroProgress) {
        dom.heroProgress.hidden = false;
        dom.heroProgress.textContent = `${target.series.shortTitle} · ${target.item.code}${state.position > 1 ? ` · ${formatTime(state.position)}` : ""}`;
      }
    } else {
      dom.body?.classList.remove("has-progress");
      if (dom.heroPrimary) {
        dom.heroPrimary.textContent = "Explorar as séries";
        dom.heroPrimary.href = "#series";
      }
      if (dom.heroProgress) dom.heroProgress.hidden = true;
    }
  }

  function stateLabel(item) {
    const state = storage.get(item.id);
    if (state.completed) return "Concluído";
    if (state.position > 1) return `Retomar em ${formatTime(state.position)}`;
    return "Novo";
  }

  function matchesFilter(item) {
    const state = storage.get(item.id);
    if (filterMode === "new" && (state.completed || state.position > 1)) return false;
    if (filterMode === "progress" && (state.completed || state.position <= 1)) return false;
    if (filterMode === "completed" && !state.completed) return false;
    if (searchQuery) {
      const haystack = `${item.code} ${item.title}`.toLocaleLowerCase("pt-BR");
      if (!haystack.includes(searchQuery)) return false;
    }
    return true;
  }

  function audioSeriesMarkup(series) {
    const stats = storage.seriesStats(series);
    return `
      <div class="learning-toolbar">
        <div class="learning-progress-summary">
          <strong>${stats.completed} de ${stats.total} concluídos</strong>
          <span>${stats.percent}% da série</span>
          <div class="learning-progress-track" aria-label="Progresso da série: ${stats.percent}%"><span style="width:${stats.percent}%"></span></div>
        </div>
        <label class="episode-search"><span>Buscar episódio</span><input type="search" id="episodeSearch" placeholder="Título, tema ou número" autocomplete="off"></label>
      </div>
      <div class="filter-row" role="group" aria-label="Filtrar episódios">
        <button type="button" data-filter="all" class="filter-chip is-active">Todos</button>
        <button type="button" data-filter="new" class="filter-chip">Não iniciados</button>
        <button type="button" data-filter="progress" class="filter-chip">Em andamento</button>
        <button type="button" data-filter="completed" class="filter-chip">Concluídos</button>
      </div>
      <section class="active-player" id="activePlayer" aria-labelledby="activeEpisodeTitle">
        <div class="active-player-copy">
          <span class="section-kicker">Agora</span>
          <h3 id="activeEpisodeTitle">Selecione um episódio</h3>
          <p id="activeEpisodeStatus">Escolha um item abaixo para começar ou retomar.</p>
        </div>
        <audio id="seriesAudio" controls preload="none" aria-label="Player da série"></audio>
        <div class="player-actions">
          <a id="downloadActive" class="text-action" href="#" download hidden>Baixar áudio</a>
          <button id="resetActive" class="text-action" type="button" hidden>Reiniciar episódio</button>
          <button id="nextEpisode" class="btn secondary" type="button" hidden>Próximo episódio</button>
        </div>
      </section>
      <div class="episode-index-head"><strong>Episódios</strong><span id="episodeResultCount"></span></div>
      <div class="episode-index" id="episodeIndex"></div>
      <div class="series-end-action"><button class="btn ghost" type="button" data-close-series>Fechar esta série e voltar às trilhas</button></div>`;
  }

  function renderEpisodeRows(series) {
    const root = $("#episodeIndex", dom.list);
    const count = $("#episodeResultCount", dom.list);
    if (!root) return;
    root.innerHTML = "";
    const visible = series.items.filter(matchesFilter);
    if (count) count.textContent = `${visible.length} de ${series.items.length}`;
    visible.forEach((item, index) => {
      const state = storage.get(item.id);
      const originalIndex = series.items.findIndex(candidate => candidate.id === item.id);
      const row = document.createElement("article");
      row.className = `episode-row${activeItem?.id === item.id ? " is-active" : ""}${state.completed ? " is-complete" : ""}`;
      row.dataset.itemId = item.id;
      row.innerHTML = `
        <button class="episode-select" type="button" data-item-id="${item.id}" aria-label="${state.completed ? "Reouvir" : state.position > 1 ? "Retomar" : "Ouvir"} ${item.code}: ${item.title}">
          <span class="episode-number">${String(originalIndex + 1).padStart(2, "0")}</span>
          <span class="episode-row-copy"><strong>${item.code}: ${item.title}</strong><span>${stateLabel(item)}</span></span>
          <span class="episode-row-action">${state.completed ? "Reouvir" : state.position > 1 ? "Continuar" : "Ouvir"}</span>
        </button>`;
      $("button", row)?.addEventListener("click", () => selectAudioItem(series, item, {updateHash:true, focusPlayer:true}));
      root.appendChild(row);
    });
    if (!visible.length) root.innerHTML = `<p class="empty-state">Nenhum episódio corresponde a este filtro.</p>`;
  }

  function updateAudioPlayerUi(series, item) {
    if (!item) return;
    const state = storage.get(item.id);
    const title = $("#activeEpisodeTitle", dom.list);
    const status = $("#activeEpisodeStatus", dom.list);
    const download = $("#downloadActive", dom.list);
    const reset = $("#resetActive", dom.list);
    const next = $("#nextEpisode", dom.list);
    if (title) title.textContent = `${item.code}: ${item.title}`;
    if (status) status.textContent = state.completed ? "Concluído. Você pode reouvir ou seguir para o próximo episódio." : state.position > 1 ? `Progresso salvo em ${formatTime(state.position)}.` : "Pronto para ouvir.";
    if (download) { download.href = item.url; download.hidden = false; }
    if (reset) reset.hidden = !(state.completed || state.position > 1);
    const index = series.items.findIndex(candidate => candidate.id === item.id);
    if (next) {
      next.hidden = index >= series.items.length - 1;
      next.textContent = index < series.items.length - 1 ? `Próximo: ${series.items[index + 1].code}` : "";
    }
  }

  function attachAudioEvents(series) {
    audio = $("#seriesAudio", dom.list);
    if (!audio) return;
    audio.addEventListener("loadedmetadata", () => {
      if (!activeItem) return;
      const state = storage.get(activeItem.id);
      if (!state.completed && state.position > 1 && state.position < audio.duration - 2) audio.currentTime = state.position;
      updateAudioPlayerUi(series, activeItem);
    });
    audio.addEventListener("play", () => {
      if (!activeItem) return;
      storage.set(activeItem.id, {completed:false, lastPlayedAt:new Date().toISOString()});
      storage.setLast(series.id, activeItem.id);
      updateHero();
      renderSeries();
      announce(`Reproduzindo ${activeItem.code}: ${activeItem.title}`);
    });
    audio.addEventListener("timeupdate", () => {
      if (!activeItem || audio.paused || !Number.isFinite(audio.currentTime)) return;
      const now = Date.now();
      if (now - saveTick < 1400) return;
      saveTick = now;
      storage.set(activeItem.id, {position:audio.currentTime, completed:false, lastPlayedAt:new Date().toISOString()});
      updateAudioPlayerUi(series, activeItem);
    });
    audio.addEventListener("pause", () => {
      if (!activeItem || audio.ended) return;
      storage.set(activeItem.id, {position:audio.currentTime || 0, completed:false, lastPlayedAt:new Date().toISOString()});
      renderEpisodeRows(series);
      updateHero();
    });
    audio.addEventListener("ended", () => {
      if (!activeItem) return;
      storage.set(activeItem.id, {position:0, completed:true, lastPlayedAt:new Date().toISOString()});
      updateAudioPlayerUi(series, activeItem);
      renderEpisodeRows(series);
      renderSeries();
      updateHero();
      announce(`${activeItem.code} concluído. Próximo episódio disponível.`);
    });
    audio.addEventListener("error", () => {
      const status = $("#activeEpisodeStatus", dom.list);
      if (status) status.textContent = "Áudio temporariamente indisponível. Tente novamente em instantes.";
      announce("Não foi possível carregar este áudio.");
    });
  }

  function selectAudioItem(series, item, options = {}) {
    if (!audio) return;
    if (activeItem?.id === item.id && audio.src) {
      if (options.focusPlayer) scrollTo($("#activePlayer", dom.list), "center");
      return;
    }
    audio.pause();
    activeItem = item;
    const state = storage.get(item.id);
    audio.src = item.url;
    audio.preload = "metadata";
    audio.load();
    storage.setLast(series.id, item.id);
    updateAudioPlayerUi(series, item);
    renderEpisodeRows(series);
    renderSeries();
    updateHero();
    if (options.updateHash) history.replaceState(null, "", `#serie-${series.id}/${item.id}`);
    if (options.focusPlayer) scrollTo($("#activePlayer", dom.list), "center");
    if (state.completed) announce(`${item.code} já foi concluído e está pronto para reouvir.`);
  }

  function bindAudioSeries(series) {
    filterMode = "all";
    searchQuery = "";
    attachAudioEvents(series);
    const search = $("#episodeSearch", dom.list);
    search?.addEventListener("input", event => {
      searchQuery = event.target.value.trim().toLocaleLowerCase("pt-BR");
      renderEpisodeRows(series);
    });
    $$('[data-filter]', dom.list).forEach(button => {
      button.addEventListener("click", () => {
        filterMode = button.dataset.filter || "all";
        $$('[data-filter]', dom.list).forEach(candidate => candidate.classList.toggle("is-active", candidate === button));
        renderEpisodeRows(series);
      });
    });
    $("#resetActive", dom.list)?.addEventListener("click", () => {
      if (!activeItem || !audio) return;
      audio.pause();
      audio.currentTime = 0;
      storage.set(activeItem.id, {position:0, completed:false, lastPlayedAt:new Date().toISOString()});
      updateAudioPlayerUi(series, activeItem);
      renderEpisodeRows(series);
      renderSeries();
      updateHero();
      announce(`${activeItem.code} reiniciado.`);
    });
    $("#nextEpisode", dom.list)?.addEventListener("click", () => {
      if (!activeItem) return;
      const index = series.items.findIndex(item => item.id === activeItem.id);
      const next = series.items[index + 1];
      if (next) selectAudioItem(series, next, {updateHash:true, focusPlayer:true});
    });
    $("[data-close-series]", dom.list)?.addEventListener("click", closeSeries);
    renderEpisodeRows(series);
  }

  async function renderPspSeries(series, targetItemId = null) {
    if (!window.GAV_PSP?.render) {
      dom.list.innerHTML = `<p class="empty-state">A trilha de PSP não pôde ser carregada.</p>`;
      announce("Falha ao carregar a trilha de PSP.");
      return;
    }
    await window.GAV_PSP.render({
      series,
      root: dom.list,
      storage,
      targetItemId,
      onStateChange() { renderSeries(); updateHero(); },
      onNavigate(itemId) {
        storage.setLast(series.id, itemId);
        history.replaceState(null, "", `#serie-3/${itemId}`);
        updateHero();
      },
      onClose: closeSeries,
      announce
    });
  }

  async function openSeries(id, targetItemId = null, options = {}) {
    const series = seriesById[String(id)];
    if (!series || series.status !== "available") return;
    if (audio) { audio.pause(); audio = null; }
    activeSeries = series;
    activeItem = null;
    dom.panel?.classList.add("is-open");
    if (dom.tip) dom.tip.hidden = true;
    if (dom.kicker) dom.kicker.textContent = `Série ${series.id} • ${series.items?.length || series.itemCount || 0} ${series.kind === "psp" ? "cards" : "episódios"}`;
    if (dom.title) dom.title.textContent = series.title;
    if (dom.desc) dom.desc.textContent = series.description;
    if (series.kind === "audio") {
      dom.list.innerHTML = audioSeriesMarkup(series);
      bindAudioSeries(series);
      const desired = targetItemId ? series.items.find(item => item.id === targetItemId) : null;
      const last = storage.getLast();
      const resume = last?.seriesId === series.id ? series.items.find(item => item.id === last.itemId) : null;
      selectAudioItem(series, desired || resume || series.items[0], {updateHash:options.updateHash !== false, focusPlayer:false});
    } else {
      dom.list.innerHTML = `<p class="loading-state">Carregando trilha…</p>`;
      await renderPspSeries(series, targetItemId);
      if (!targetItemId && options.updateHash !== false) history.replaceState(null, "", `#serie-${series.id}`);
    }
    announce(`${series.title} aberta.`);
    if (options.scroll !== false) window.setTimeout(() => scrollTo(dom.panel), 40);
  }

  function closeSeries() {
    if (audio) audio.pause();
    audio = null;
    activeItem = null;
    activeSeries = null;
    dom.panel?.classList.remove("is-open");
    if (dom.list) dom.list.innerHTML = "";
    history.replaceState(null, "", `${location.pathname}${location.search}#series`);
    announce("Trilha fechada. Séries disponíveis.");
    window.setTimeout(() => scrollTo($("#series")), 20);
  }

  function parseHash() {
    const hash = decodeURIComponent(location.hash.replace(/^#/, ""));
    const match = hash.match(/^serie-(\d)(?:\/([a-z0-9-]+))?$/i);
    if (!match) return null;
    return {seriesId:match[1], itemId:match[2] || null};
  }

  async function restoreFromHash() {
    const route = parseHash();
    if (!route) return false;
    await openSeries(route.seriesId, route.itemId, {updateHash:false, scroll:true});
    return true;
  }

  function bind() {
    dom.aboutToggle?.addEventListener("click", () => setAbout(!dom.aboutContent.classList.contains("is-open")));
    dom.aboutOpen?.addEventListener("click", () => { setAbout(true); scrollTo($("#sobre")); });
    dom.back?.addEventListener("click", closeSeries);
    dom.onboardStart?.addEventListener("click", () => { closeOnboard(); scrollTo($("#series")); });
    dom.onboardSkip?.addEventListener("click", closeOnboard);
    dom.heroPrimary?.addEventListener("click", event => {
      const route = dom.heroPrimary.getAttribute("href")?.match(/^#serie-(\d)(?:\/([a-z0-9-]+))?$/i);
      if (!route) return;
      event.preventDefault();
      openSeries(route[1], route[2] || null, {updateHash:true, scroll:true});
    });
    document.addEventListener("keydown", event => {
      if (event.key === "Escape" && dom.onboarding?.classList.contains("is-open")) closeOnboard();
      trapOnboardFocus(event);
    });
    window.addEventListener("hashchange", () => {
      const route = parseHash();
      if (route && (activeSeries?.id !== route.seriesId || (route.itemId && activeItem?.id !== route.itemId))) openSeries(route.seriesId, route.itemId, {updateHash:false, scroll:true});
    });
  }

  async function init() {
    storage.migrateLegacy();
    renderSeries();
    updateHero();
    bind();
    const routed = await restoreFromHash();
    if (!routed) {
      try { if (localStorage.getItem(LS.ONBOARD) !== "1") openOnboard(); } catch { openOnboard(); }
    }
  }

  window.GAV_APP = Object.freeze({openSeries, closeSeries, storage, manifest});
  document.readyState === "loading" ? document.addEventListener("DOMContentLoaded", init, {once:true}) : init();
})();
