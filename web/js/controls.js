// Controles del visor: elegir la composición de fondo y encender o apagar cada capa.

import { compositeUrl } from "./api.js";

const COMPOSITE_LABELS = {
  swir: "SWIR",
  true_color: "True Color",
  wildfires: "Wildfires",
};

const LAYER_LABELS = {
  burned_area: "Superficie quemada",
  relative_severity: "Severidad relativa",
  perimeter: "Perímetro",
  active_fire: "Focos activos",
};

/** Composición que se muestra de fondo por defecto: True Color si se subió, si no SWIR. */
export function defaultBackground(composites) {
  return composites.includes("true_color") ? "true_color" : "swir";
}

export function createControls({ backgroundRoot, layerRoot, onBackground, onLayer }) {
  return {
    /** Un botón de radio por composición subida; `analysis` es la ruta de donde cuelgan. */
    showBackgrounds(composites, analysis) {
      const selected = defaultBackground(composites);
      reset(backgroundRoot, "Imagen de fondo");
      for (const kind of composites) {
        backgroundRoot.append(
          option({
            type: "radio",
            name: "background",
            label: COMPOSITE_LABELS[kind],
            checked: kind === selected,
            onChange: () => onBackground(compositeUrl(analysis, kind)),
          }),
        );
      }
      onBackground(compositeUrl(analysis, selected));
    },

    /** Una casilla por capa; las que el resultado no trae quedan deshabilitadas. */
    showLayers(available) {
      reset(layerRoot, "Capas");
      for (const [name, label] of Object.entries(LAYER_LABELS)) {
        const usable = Boolean(available[name]);
        layerRoot.append(
          option({
            type: "checkbox",
            label: usable ? label : `${label} (No detectado)`,
            checked: usable,
            disabled: !usable,
            onChange: (checked) => onLayer(name, checked),
          }),
        );
        onLayer(name, usable);
      }
    },
  };
}

function reset(root, legendText) {
  root.replaceChildren();
  const legend = document.createElement("legend");
  legend.textContent = legendText;
  root.append(legend);
}

function option({ type, name, label, checked, disabled = false, onChange }) {
  const wrapper = document.createElement("label");
  wrapper.className = "option";
  const input = document.createElement("input");
  input.type = type;
  if (name) input.name = name;
  input.checked = checked;
  input.disabled = disabled;
  input.addEventListener("change", () => onChange(input.checked));
  wrapper.append(input, document.createTextNode(` ${label}`));
  return wrapper;
}
