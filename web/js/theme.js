// Tema claro u oscuro. El de arranque lo pone el script de <head> de index.html (el
// guardado o, en la primera visita, el del sistema); aquí se cambia y se recuerda.

const STORAGE_KEY = "uh-theme";

const current = () =>
  document.documentElement.getAttribute("data-theme") === "light" ? "light" : "dark";

/** Conecta los botones `[data-theme-toggle]` de todas las pantallas. */
export function setUpThemeToggles(root = document) {
  const buttons = [...root.querySelectorAll("[data-theme-toggle]")];

  function paint() {
    const label = current() === "dark" ? "☀ Tema claro" : "☾ Tema oscuro";
    for (const button of buttons) button.textContent = label;
  }

  for (const button of buttons) {
    button.addEventListener("click", () => {
      const next = current() === "dark" ? "light" : "dark";
      document.documentElement.setAttribute("data-theme", next);
      // Sin almacenamiento (ventana privada, datos bloqueados) el tema dura la visita.
      try {
        localStorage.setItem(STORAGE_KEY, next);
      } catch {}
      paint();
    });
  }
  paint();
}
