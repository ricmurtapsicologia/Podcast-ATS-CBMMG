(() => {
  "use strict";

  /*
    O podcast reutiliza somente a validação canônica de credenciais do Curso ATS.
    Sessão e tentativas são isoladas por namespace próprio para que um login não
    autentique automaticamente a outra página.
  */
  const KEY_MAP = Object.freeze({
    curso_ats_auth_v3: "gav_auth_v1",
    ats_login_attempts_v3: "gav_login_attempts_v1"
  });

  const storageProto = Storage.prototype;
  if (!window.__gavAuthStorageMapped) {
    const original = Object.freeze({
      getItem: storageProto.getItem,
      setItem: storageProto.setItem,
      removeItem: storageProto.removeItem
    });

    const mapKey = key => KEY_MAP[String(key)] || String(key);
    storageProto.getItem = function (key) { return original.getItem.call(this, mapKey(key)); };
    storageProto.setItem = function (key, value) { return original.setItem.call(this, mapKey(key), value); };
    storageProto.removeItem = function (key) { return original.removeItem.call(this, mapKey(key)); };

    Object.defineProperty(window, "__gavAuthStorageMapped", { value: true });
  }

  const hourglassSvg = `
    <svg viewBox="0 0 64 64" aria-hidden="true" focusable="false">
      <rect width="64" height="64" rx="14" fill="#07101f"/>
      <path d="M20 13h24M20 51h24" stroke="#ffdd00" stroke-width="4" stroke-linecap="round"/>
      <path d="M23 16c0 9 5 12 9 16-4 4-9 7-9 16h18c0-9-5-12-9-16 4-4 9-7 9-16H23Z" fill="none" stroke="#fff" stroke-width="3.2" stroke-linejoin="round"/>
      <path d="M27 23h10c-1.7 3.2-3.4 4.7-5 6.3-1.7-1.6-3.3-3.1-5-6.3Zm2.2 18c.9-2 1.8-3 2.8-4 1 1 1.9 2 2.8 4h-5.6Z" fill="#ffdd00"/>
    </svg>`;

  let autoTimer = 0;
  const onlyDigits = value => String(value || "").replace(/\D/g, "");

  function setText(root, selector, value) {
    const node = root.querySelector(selector);
    if (node) node.textContent = value;
  }

  function bindAutoAccess(gate) {
    const form = gate.querySelector("#catsAuthForm");
    const input = gate.querySelector("#catsAuthInput");
    const submit = gate.querySelector("#catsAuthSubmit");
    if (!form || !input) return;

    if (submit) submit.remove();

    setText(gate, "#catsAuthHelp", "Digite sua matrícula BM/PM (7 números) ou CPF cadastrado (11 números). O acesso é validado automaticamente.");

    if (input.dataset.autoAccessBound === "1") return;
    input.dataset.autoAccessBound = "1";

    const trySubmit = delay => {
      window.clearTimeout(autoTimer);
      const current = onlyDigits(input.value);
      if (current.length !== 7 && current.length !== 11) return;
      autoTimer = window.setTimeout(() => {
        if (input.disabled) return;
        const latest = onlyDigits(input.value);
        if (latest !== current) return;
        if (latest.length !== 7 && latest.length !== 11) return;
        form.requestSubmit();
      }, delay);
    };

    input.addEventListener("input", () => {
      const length = onlyDigits(input.value).length;
      window.clearTimeout(autoTimer);
      if (length === 11) trySubmit(0);
      else if (length === 7) trySubmit(550);
    });
  }

  function maintainDynamicBranding(gate) {
    bindAutoAccess(gate);

    const messageText = gate.querySelector("#catsAuthMessageText");
    if (messageText?.textContent?.includes("Abrindo o ambiente")) {
      messageText.textContent = messageText.textContent.replace("Abrindo o ambiente", "Abrindo a biblioteca");
    }
  }

  function rebrandGate() {
    const gate = document.getElementById("catsAuthGate");
    if (!gate) return false;

    gate.removeAttribute("data-gav-branded");
    gate.setAttribute("aria-label", "Acesso ao Girando a Ampulheta da Vida");

    const brand = gate.querySelector(".cats-auth-brand");
    if (brand) brand.innerHTML = `${hourglassSvg}<span>CBMMG • Biblioteca de apoio</span>`;

    const title = gate.querySelector("#catsAuthTitle");
    if (title) title.innerHTML = `Girando a <span class="cats-auth-accent">Ampulheta</span> da Vida`;

    setText(gate, ".cats-auth-kicker", "Biblioteca sonora e trilhas de aprendizagem");
    setText(gate, ".cats-auth-hero-text", "Conteúdos complementares para escuta, reflexão técnica, aprofundamento em abordagem e Primeiros Socorros Psicológicos.");
    setText(gate, ".cats-auth-hero-foot span", "Identifique-se ao lado para acessar a biblioteca.");
    setText(gate, ".cats-auth-eyebrow", "Acesso à biblioteca");

    const loginTitle = gate.querySelector("#catsAuthLoginTitle");
    if (loginTitle) loginTitle.innerHTML = `Entre na <span class="cats-auth-accent">biblioteca</span>`;

    setText(gate, ".cats-auth-subtitle", "Informe a mesma credencial autorizada utilizada na plataforma ATS. O acesso ocorre automaticamente após a validação.");
    setText(gate, ".cats-auth-course-title", "Girando a Ampulheta da Vida");
    setText(gate, ".cats-auth-course-note", "Biblioteca de apoio às aulas e à formação em ATS.");
    setText(gate, ".cats-auth-note", "O acesso é individual e destinado às pessoas previamente cadastradas.");

    const logo = gate.querySelector(".cats-auth-logo");
    if (logo) logo.innerHTML = hourglassSvg;

    const footerSpans = gate.querySelectorAll(".cats-auth-footer span");
    if (footerSpans[0]) footerSpans[0].textContent = "© 2026 Corpo de Bombeiros Militar de Minas Gerais. Todos os direitos reservados.";
    if (footerSpans[1]) footerSpans[1].textContent = "Girando a Ampulheta da Vida";

    maintainDynamicBranding(gate);
    if (!gate.__gavBrandObserver) {
      const brandingObserver = new MutationObserver(() => maintainDynamicBranding(gate));
      brandingObserver.observe(gate, { childList: true, subtree: true, characterData: true });
      Object.defineProperty(gate, "__gavBrandObserver", { value: brandingObserver });
    }

    gate.dataset.gavBranded = "true";
    document.documentElement.classList.remove("gav-auth-pending");
    return true;
  }

  function observeGate() {
    if (rebrandGate()) return;
    const observer = new MutationObserver(() => {
      if (rebrandGate()) observer.disconnect();
    });
    observer.observe(document.documentElement, { childList: true, subtree: true });

    window.setTimeout(() => {
      if (document.getElementById("catsAuthGate")) return;
      observer.disconnect();
      document.documentElement.classList.remove("gav-auth-pending");
      document.documentElement.classList.add("gav-auth-failed");
    }, 5000);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", observeGate, { once: true });
  } else {
    observeGate();
  }
})();
