(() => {
  "use strict";

  const ACCESS_URL = "https://ricmurtapsicologia.github.io/Curso-ATS/access-2026.js?v=20260917-1";
  const ACCESS_HOTFIX_URL = "https://ricmurtapsicologia.github.io/Curso-ATS/access-hotfix-20260918.js?v=20260918-2";
  const AUDIO_URL = /\.(?:mp3|m4a|aac|wav|ogg)(?:$|[?#])/i;

  function loadAccess(src, marker) {
    if (document.querySelector(`script[src*="${marker}"]`)) return;
    const script = document.createElement("script");
    script.src = src;
    script.async = false;
    document.head.appendChild(script);
  }

  function loadCanonicalAccess() {
    loadAccess(ACCESS_URL, "access-2026.js");
    loadAccess(ACCESS_HOTFIX_URL, "access-hotfix-20260918.js");
  }

  function block(event) {
    event.preventDefault();
    event.stopPropagation();
  }

  function protectAudio(audio) {
    if (!(audio instanceof HTMLAudioElement)) return;

    audio.setAttribute("controlsList", "nodownload noremoteplayback");
    audio.setAttribute("disableRemotePlayback", "");
    audio.setAttribute("draggable", "false");
    try { audio.disableRemotePlayback = true; } catch {}

    if (audio.dataset.gavMediaProtected === "1") return;
    audio.dataset.gavMediaProtected = "1";
    audio.addEventListener("contextmenu", block, {capture:true});
    audio.addEventListener("dragstart", block, {capture:true});
  }

  function isDirectAudioAction(link) {
    if (!(link instanceof HTMLAnchorElement)) return false;
    const href = link.getAttribute("href") || "";
    return link.hasAttribute("download") || AUDIO_URL.test(href) || /baixar\s+áudio/i.test(link.textContent || "");
  }

  function stripDirectAudioAction(link) {
    if (isDirectAudioAction(link)) link.remove();
  }

  function removeDirectAudioActions(root = document) {
    if (root instanceof HTMLAnchorElement) stripDirectAudioAction(root);
    root.querySelectorAll?.("a").forEach(stripDirectAudioAction);
  }

  function protect(root = document) {
    if (root instanceof HTMLAudioElement) protectAudio(root);
    root.querySelectorAll?.("audio").forEach(protectAudio);
    removeDirectAudioActions(root);
  }

  function blockDirectAudioLink(event) {
    const link = event.target?.closest?.("a");
    if (isDirectAudioAction(link)) block(event);
  }

  loadCanonicalAccess();
  document.addEventListener("click", blockDirectAudioLink, true);
  document.addEventListener("auxclick", blockDirectAudioLink, true);
  document.addEventListener("contextmenu", event => {
    if (event.target?.closest?.("audio")) block(event);
  }, true);

  protect(document);

  const observer = new MutationObserver(mutations => {
    for (const mutation of mutations) {
      for (const node of mutation.addedNodes) {
        if (node.nodeType === Node.ELEMENT_NODE) protect(node);
      }
    }
  });
  observer.observe(document.documentElement, {childList:true, subtree:true});
})();
