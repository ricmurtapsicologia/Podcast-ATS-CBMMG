(() => {
  "use strict";

  function percentageFrom(element) {
    const explicit = element.getAttribute("aria-valuenow");
    if (explicit != null && explicit !== "") return Math.max(0, Math.min(100, Number(explicit) || 0));
    const label = element.getAttribute("aria-label") || "";
    const match = label.match(/(\d{1,3})\s*%/);
    if (match) return Math.max(0, Math.min(100, Number(match[1]) || 0));
    const fill = element.querySelector(":scope > span");
    const width = fill?.style?.width || "";
    const widthMatch = width.match(/(\d{1,3}(?:\.\d+)?)%/);
    return widthMatch ? Math.max(0, Math.min(100, Number(widthMatch[1]) || 0)) : 0;
  }

  function normalize(root = document) {
    root.querySelectorAll?.(".series-progress, .learning-progress-track").forEach(element => {
      const value = percentageFrom(element);
      element.setAttribute("role", "progressbar");
      element.setAttribute("aria-valuemin", "0");
      element.setAttribute("aria-valuemax", "100");
      element.setAttribute("aria-valuenow", String(Math.round(value)));
      if (!element.getAttribute("aria-label")) element.setAttribute("aria-label", "Progresso");
    });
  }

  function init() {
    normalize(document);
    const observer = new MutationObserver(records => {
      for (const record of records) {
        record.addedNodes.forEach(node => {
          if (node.nodeType !== Node.ELEMENT_NODE) return;
          if (node.matches?.(".series-progress, .learning-progress-track")) normalize(node.parentElement || document);
          else normalize(node);
        });
      }
    });
    observer.observe(document.body, {childList:true, subtree:true});
  }

  document.readyState === "loading"
    ? document.addEventListener("DOMContentLoaded", init, {once:true})
    : init();
})();
