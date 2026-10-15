// Resumen del análisis: la línea de estado bajo el visor, con el resumen en texto que lee
// el lector de pantalla, y el bloque de cifras globales con su confianza y sus avisos.

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

export const EXAMPLE_NOTICE =
  "Resultado de ejemplo del contrato, con cifras inventadas para enseñar el visor: " +
  "no corresponde a ninguna escena analizada.";

export function createSummary({ root, status, facts, warnings }) {
  return {
    /** Pinta el resumen de `result`; `example` avisa de que las cifras no son reales. */
    show(result, { example = false } = {}) {
      const parts = [screenReaderSummary(result), describeScene(result)];
      if (example) parts.unshift(EXAMPLE_NOTICE);
      status.textContent = parts.join(" ");

      facts.replaceChildren(factList(describeSummary(result)));
      warnings.replaceChildren(
        ...result.summary.warnings.map((warning) => {
          const item = document.createElement("li");
          item.textContent = warning;
          return item;
        }),
      );
      warnings.hidden = result.summary.warnings.length === 0;
      root.hidden = false;
    },
  };
}
