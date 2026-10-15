// Resumen del análisis: los chips de la barra superior, el resumen en texto que lee el
// lector de pantalla y la pestaña Resumen, con el titular, la procedencia de la escala,
// los avisos, las cifras globales y sus confianzas.

import { factRow, infoButton, text } from "./card.js";
import { describeConfidence, describeFigures, formatNumber, headline, screenReaderSummary } from "./describe.js";

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

/** De qué depende la escala de las cifras: `{text, warn}`. */
export function scaleProvenance({ scene }) {
  if (!scene.georeference) return { text: "Sin escala: cifras en píxeles", warn: true };
  const source = GEOREFERENCE_SOURCES[scene.georeference.source].toLowerCase();
  const metres = scene.metres_per_pixel ? ` · ${formatNumber(scene.metres_per_pixel, 1)} m/px` : "";
  return { text: `Escala: ${source}${metres}`, warn: false };
}

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

/** `onFit()` entra en el encaje desde el botón «Situar en el mapa». */
export function createSummary({ chips, status, panel, onFit }) {
  function showChips(result, options) {
    chips.replaceChildren(
      ...sceneChips(result, options).map(({ text: content, tone }) =>
        text("span", content, tone ? `chip chip--${tone}` : "chip"),
      ),
    );
  }

  return {
    /** Chips de la barra superior; `{fitting: true}` mientras se encaja. */
    showChips,

    /** Pinta el resumen de `result`. */
    show(result) {
      showChips(result);
      status.textContent = [screenReaderSummary(result), describeScene(result)].join(" ");

      const body = text("div", "", "res");
      const provenance = scaleProvenance(result);
      body.append(
        text("h2", headline(result)),
        text("div", provenance.text, provenance.warn ? "res__prov is-warn" : "res__prov"),
      );

      const { warnings } = result.summary;
      if (warnings.length > 0) {
        const notice = text("div", "", "notice");
        notice.setAttribute("role", "note");
        notice.setAttribute("aria-label", "Avisos");
        notice.append(...warnings.map((warning) => text("div", warning)));
        body.append(notice);
      }

      if (!result.scene.georeference) {
        const note = text("div", "", "geo-note");
        const button = text("button", "Situar en el mapa", "btn btn--primary");
        button.type = "button";
        button.style.alignSelf = "flex-start";
        button.addEventListener("click", onFit);
        note.append(
          text("div", "Las cifras están en píxeles. Sitúa la escena en el mapa para obtener hectáreas y poblaciones."),
          button,
        );
        body.append(note);
      }

      const rows = text("div", "", "rows");
      rows.append(...describeFigures(result).map((fact) => factRow(fact)));
      for (const { label, high, value, note } of describeConfidence(result)) {
        const row = text("div", "", "conf");
        const right = text("span", "", "conf__r");
        right.append(
          text("span", `${high ? "✓" : "▼"} ${value}`, high ? "tag tag--ok" : "tag tag--baja"),
          infoButton(note, `Motivo de la confianza: ${label}`),
        );
        row.append(text("span", `Confianza · ${label}`), right);
        rows.append(row);
      }
      body.append(rows);
      panel.replaceChildren(body);
    },
  };
}
