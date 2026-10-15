// Ventana flotante «Fondo y capas»: el fondo entre las composiciones aportadas y un
// interruptor por capa con su muestra de leyenda. Se cierra y queda un botón para reabrirla.

import { compositeUrl } from "./api.js";
import { text } from "./card.js";
import { ESTIMATED_FIRE, FIRE_BY_LEVEL } from "./viewer.js";

/** Orden del selector de fondo; solo salen las composiciones aportadas. */
const BACKGROUNDS = [
  ["true_color", "True Color"],
  ["swir", "SWIR"],
  ["wildfires", "Wildfires"],
];

const NO_BURN = "No se ha detectado superficie quemada en esta escena.";

/** Composición que se muestra de fondo por defecto: True Color si se subió, si no SWIR. */
export function defaultBackground(composites) {
  return composites.includes("true_color") ? "true_color" : "swir";
}

const TRIANGLE = "0,-10 9,7 -9,7";

function triangle(size, { fill, stroke, estimated = false }) {
  const halo = estimated
    ? `<polygon points="${TRIANGLE}" fill="none" stroke="#ffffff" stroke-width="4" stroke-linejoin="round" />`
    : "";
  return `<svg width="${size}" height="${size}" viewBox="-12 -12 24 24" aria-hidden="true">${halo}
    <polygon points="${TRIANGLE}" fill="${fill}" ${estimated ? 'fill-opacity="0.55"' : ""} stroke="${stroke}"
      stroke-width="${estimated ? 2.2 : 1.6}" stroke-linejoin="round" /></svg>`;
}

/** Muestras de leyenda, con los mismos colores que pinta el mapa. */
function swatch(name) {
  const span = document.createElement("span");
  span.setAttribute("aria-hidden", "true");
  if (name === "burned_area") span.className = "sw-burn";
  if (name === "relative_severity") {
    span.className = "sw-sev";
    span.innerHTML = "<i></i><i></i>";
  }
  if (name === "perimeter") span.className = "sw-per";
  if (name === "active_fire") {
    span.className = "sw-foc";
    span.innerHTML =
      [1, 2, 3, 4].map((level) => triangle(8 + (level - 1) * 3, { fill: FIRE_BY_LEVEL[level], stroke: FIRE_BY_LEVEL[level] })).join("") +
      triangle(16, { fill: ESTIMATED_FIRE, stroke: ESTIMATED_FIRE, estimated: true });
  }
  return span;
}

export function createLayerPanel({ panel, openButton, closeButton, backgroundRoot, layerRoot, onBackground, onLayer }) {
  let open = true;
  let fitting = false;

  function refresh() {
    panel.hidden = fitting || !open;
    openButton.hidden = fitting || open;
  }
  closeButton.addEventListener("click", () => {
    open = false;
    refresh();
    openButton.focus();
  });
  openButton.addEventListener("click", () => {
    open = true;
    refresh();
    closeButton.focus();
  });

  function layerRow(name, label, reason, visible, note) {
    const row = text("div", "", reason ? "layer is-off" : "layer");
    const line = text("div", "", "layer__row");
    const toggle = text("button", "", "switch");
    toggle.type = "button";
    toggle.setAttribute("role", "switch");
    toggle.setAttribute("aria-label", label);
    toggle.setAttribute("aria-checked", String(visible));
    toggle.disabled = Boolean(reason);
    toggle.addEventListener("click", () => {
      const on = toggle.getAttribute("aria-checked") !== "true";
      toggle.setAttribute("aria-checked", String(on));
      onLayer(name, on);
    });
    line.append(toggle, text("span", label, "layer__name"), swatch(name));
    row.append(line);
    if (note) row.append(text("div", note, "layer__note"));
    if (reason) row.append(text("div", reason, "layer__note"));
    return row;
  }

  return {
    /** Mientras se encaja no hay ni ventana ni botón. */
    setFitting(value) {
      fitting = value;
      refresh();
    },

    /** Un botón por composición aportada; `analysis` es la ruta de donde cuelgan. */
    showBackgrounds(composites, analysis) {
      let selected = defaultBackground(composites);
      const buttons = BACKGROUNDS.filter(([kind]) => composites.includes(kind)).map(([kind, label]) => {
        const button = text("button", label);
        button.type = "button";
        button.setAttribute("role", "radio");
        button.dataset.kind = kind;
        button.addEventListener("click", () => {
          selected = kind;
          mark();
          onBackground(compositeUrl(analysis, kind));
        });
        return button;
      });
      const mark = () => {
        for (const button of buttons) {
          const on = button.dataset.kind === selected;
          button.setAttribute("aria-checked", String(on));
          button.tabIndex = on ? 0 : -1;
        }
      };
      mark();
      // Grupo de radio: un solo botón tabulable y las flechas pasan de uno a otro.
      backgroundRoot.onkeydown = (event) => {
        const step = { ArrowRight: 1, ArrowDown: 1, ArrowLeft: -1, ArrowUp: -1 }[event.key];
        if (!step) return;
        event.preventDefault();
        const index = buttons.findIndex((button) => button.dataset.kind === selected);
        const next = buttons[(index + step + buttons.length) % buttons.length];
        next.click();
        next.focus();
      };
      backgroundRoot.replaceChildren(...buttons);
      onBackground(compositeUrl(analysis, selected));
    },

    /**
     * Un interruptor por capa; las que el resultado no trae quedan deshabilitadas con su
     * motivo. `estimated` dice si todos los focos son estimados desde la SWIR.
     */
    showLayers(available, { estimated = false } = {}) {
      const layers = [
        ["burned_area", "Superficie quemada", NO_BURN],
        ["relative_severity", "Severidad relativa", NO_BURN],
        ["perimeter", "Perímetro", NO_BURN],
        ["active_fire", estimated ? "Focos activos (estimados)" : "Focos activos", "No se han detectado focos activos."],
      ];
      layerRoot.replaceChildren(
        ...layers.map(([name, label, reason]) => {
          const usable = Boolean(available[name]);
          onLayer(name, usable);
          const note = name === "active_fire" ? "Niveles 1–4 · malva con borde blanco: estimado desde la SWIR" : null;
          return layerRow(name, label, usable ? null : reason, usable, note);
        }),
      );
      refresh();
    },
  };
}
