// Las tres pantallas de la app sobre el esqueleto fijo de index.html: solo una visible.

const SCREENS = {
  new: "screen-new",
  load: "screen-load",
  work: "screen-work",
};

/** Muestra la pantalla `name` («new», «load» o «work») y oculta las demás. */
export function showScreen(name) {
  for (const [screen, id] of Object.entries(SCREENS)) {
    document.getElementById(id).hidden = screen !== name;
  }
}
