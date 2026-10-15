// Llamadas a la API del motor. Nada de esto sabe de Leaflet ni del DOM.

/**
 * Sube las composiciones y devuelve el resultado del análisis.
 *
 * @param {{swir: File, true_color?: File, wildfires?: File}} composites
 * @param {(progress: {phase: "upload"|"analysis", ratio?: number}) => void} onProgress
 * @returns {Promise<{result: object, analysis: string}>} el resultado conforme a
 *   `contract/result.schema.json` y la ruta del análisis, de donde cuelgan las vistas
 *   reducidas de las composiciones (`<analysis>/composites/<swir|true_color|wildfires>`).
 */
export function analyseScene(composites, onProgress = () => {}) {
  const body = new FormData();
  for (const [field, file] of Object.entries(composites)) {
    if (file) body.append(field, file, file.name);
  }

  return new Promise((resolve, reject) => {
    const request = new XMLHttpRequest();
    request.open("POST", "/api/analyses");

    request.upload.addEventListener("progress", (event) => {
      if (event.lengthComputable) {
        onProgress({ phase: "upload", ratio: event.loaded / event.total });
      }
    });
    request.upload.addEventListener("load", () => onProgress({ phase: "analysis" }));

    request.addEventListener("load", () => {
      let payload;
      try {
        payload = JSON.parse(request.responseText);
      } catch {
        reject(new Error("La respuesta del servidor no se ha entendido."));
        return;
      }
      if (request.status === 201) {
        resolve({ result: payload, analysis: request.getResponseHeader("Location") });
      } else {
        reject(new Error(payload.detail ?? "No se ha podido analizar la escena."));
      }
    });
    request.addEventListener("error", () =>
      reject(new Error("No se ha podido conectar con el servidor.")),
    );

    request.send(body);
  });
}

/** Resultado de ejemplo del contrato, para ver el visor sin analizar nada. */
export async function fetchExample() {
  const response = await fetch("/api/example");
  if (!response.ok) throw new Error("No se ha podido cargar el resultado de ejemplo.");
  return response.json();
}

/** URL de la vista web de una composición de un análisis. */
export function compositeUrl(analysis, kind) {
  return `${analysis}/composites/${kind}`;
}

/**
 * URL de una capa PNG de un análisis. El contrato da `path` relativo al directorio de
 * salida del motor, y ese directorio es la carpeta del análisis en la API. Devuelve
 * `null` cuando no hay capa, o cuando el resultado no viene de un análisis (el ejemplo
 * del contrato, cuyos PNG no existen en el servidor).
 */
export function layerUrl(analysis, path) {
  return analysis && path ? `${analysis}/layers/${path}` : null;
}
