(() => {
  "use strict";

  const AUDIO_URL = /\.(?:mp3|m4a|aac|wav|ogg)(?:$|[?#])/i;

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

  function removeDirectAudioActions(root = document) {
    const links = root.querySelectorAll?.("a") || [];
    links.forEach(link => {
      const href = link.getAttribute("href") || "";
      const isAudio = AUDIO_URL.test(href);
      const isDownload = link.hasAttribute("download") || /baixar\s+áudio/i.test(link.textContent || "");
      if (!isAudio && !isDownload) return;
      link.remove();
    });
  }

  function protect(root = document) {
    if (root instanceof HTMLAudioElement) protectAudio(root);
    root.querySelectorAll?.("audio").forEach(protectAudio);
    removeDirectAudioActions(root);
  }

  document.addEventListener("click", event => {
    const link = event.target?.closest?.("a");
    if (!link) return;
    const href = link.getAttribute("href") || "";
    if (link.hasAttribute("download") || AUDIO_URL.test(href)) block(event);
  }, true);

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
