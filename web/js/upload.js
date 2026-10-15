// Formulario de subida: composiciones, bbox opcional y errores. El progreso lo pinta la
// pantalla «Análisis en curso» (progress.js).

import { readBbox } from "./georeference.js";

export function createUploadForm({ form, error, onAnalyse }) {
  const fields = {
    swir: form.elements.swir,
    true_color: form.elements.true_color,
    wildfires: form.elements.wildfires,
    geotiff: form.elements.geotiff,
  };

  function showError(message) {
    error.textContent = message;
    error.hidden = !message;
  }

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    showError("");

    const composites = Object.fromEntries(
      Object.entries(fields).map(([field, input]) => [field, input.files[0] ?? null]),
    );
    if (!composites.swir) {
      showError("Falta la composición SWIR: es la única obligatoria.");
      fields.swir.focus();
      return;
    }
    let bbox;
    try {
      bbox = readBbox(form);
    } catch (failure) {
      showError(failure.message);
      return;
    }

    try {
      await onAnalyse(composites, bbox);
    } catch (failure) {
      showError(failure.message);
    }
  });

  return {
    showError,
    /** Deja el formulario vacío para una escena nueva. */
    reset() {
      form.reset();
      showError("");
    },
  };
}
