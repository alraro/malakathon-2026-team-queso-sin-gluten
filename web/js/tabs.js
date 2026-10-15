// Pestañas de la columna de resultados: cada botón `[data-tab]` de `root` muestra el
// panel que nombra su `aria-controls`. Las flechas izquierda y derecha pasan de una a otra.

export function createTabs(root) {
  const tabs = [...root.querySelectorAll("[data-tab]")];
  const panelOf = (tab) => document.getElementById(tab.getAttribute("aria-controls"));
  const visible = () => tabs.filter((tab) => !tab.hidden);

  function show(name) {
    for (const tab of tabs) {
      const on = tab.dataset.tab === name;
      tab.setAttribute("aria-selected", String(on));
      tab.tabIndex = on ? 0 : -1;
      panelOf(tab).hidden = !on;
    }
  }

  for (const tab of tabs) tab.addEventListener("click", () => show(tab.dataset.tab));
  root.addEventListener("keydown", (event) => {
    const step = { ArrowRight: 1, ArrowLeft: -1 }[event.key];
    if (!step) return;
    const shown = visible();
    const next = shown[(shown.indexOf(document.activeElement) + step + shown.length) % shown.length];
    show(next.dataset.tab);
    next.focus();
  });

  return {
    show,

    /** Pone el contador de una pestaña (ninguno con `null`) y la muestra u oculta. */
    configure(name, { count = null, available = true } = {}) {
      const tab = tabs.find((candidate) => candidate.dataset.tab === name);
      tab.hidden = !available;
      tab.querySelector("small").textContent = count === null ? "" : String(count);
    },
  };
}
