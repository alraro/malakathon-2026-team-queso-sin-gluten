// Resumen del análisis: los chips de la barra superior, el resumen en texto que lee el
// lector de pantalla y el bloque de cifras globales con su confianza y sus avisos.

import { factList } from "./card.js";
import { describeSummary, screenReaderSummary } from "./describe.js";

const COMPOSITE_LABELS = {
  swir: "SWIR",
  true_color: "True Color",
  wildfires: "Wildfires",
};

export function describeScene({ scene }) {
  const size = `${scene.width.toLocaleString("es")} × ${scene.height.toLocaleString("es")} px`;
  const composites = scene.composites.map((kind) => COMPOSITE_LABELS[kind]).join(", ");
  return `Escena de ${size}. Composiciones aportadas: ${composites}.`;
}

const GEOREFERENCE_SOURCES = {
  geotiff: "GeoTIFF",
  manual: "Coordenadas manuales",
  map_fit: "Encaje sobre el mapa",
};

const scale = new Intl.NumberFormat("es-ES", { minimumFractionDigits: 1, maximumFractionDigits: 1 });

/**
 * Chips de la barra superior: `{text, tone}`, con `tone` «tx», «ac», «warn» o nada.
 * Dimensiones, composiciones aportadas y georreferencia con su procedencia y su escala;
 * mientras se encaja (`fitting`), en lugar de la georreferencia, «Encaje en curso».
 */
export function sceneChips({ scene }, { fitting = false } = {}) {
  const georeference = fitting
    ? "Encaje en curso"
    : scene.georeference
    ? [
        `⌖ ${GEOREFERENCE_SOURCES[scene.georeference.source]}`,
        scene.metres_per_pixel ? `${scale.format(scene.metres_per_pixel)} m/px` : null,
      ].filter(Boolean).join(" · ")
    : "⌖ Sin georreferencia";
  return [
    { text: `${scene.width}×${scene.height} px`, tone: "tx" },
    { text: scene.composites.map((kind) => COMPOSITE_LABELS[kind]).join(" · ") },
    { text: georeference, tone: fitting || scene.georeference ? "ac" : "warn" },
  ];
}

export function createSummary({ chips, status, facts, warnings }) {
  function showChips(result, options) {
    chips.replaceChildren(
      ...sceneChips(result, options).map(({ text, tone }) => {
        const chip = document.createElement("span");
        chip.className = tone ? `chip chip--${tone}` : "chip";
        chip.textContent = text;
        return chip;
      }),
    );
  }

  return {
    /** Chips de la barra superior; `{fitting: true}` mientras se encaja. */
    showChips,

    /** Pinta el resumen de `result`. */
    show(result) {
      showChips(result);
      status.textContent = [screenReaderSummary(result), describeScene(result)].join(" ");

      facts.replaceChildren(factList(describeSummary(result)));
      warnings.replaceChildren(
        ...result.summary.warnings.map((warning) => {
          const item = document.createElement("li");
          item.textContent = warning;
          return item;
        }),
      );
      warnings.hidden = result.summary.warnings.length === 0;
    },
  };
}
