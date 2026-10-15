// Montaje de la aplicación: une subida, visor y controles.
// Cada pieza vive en su fichero para que otros tickets añadan las suyas sin pisarse.

import { analyseScene, fetchExample } from "./api.js";
import { createControls } from "./controls.js";
import { createUploadForm } from "./upload.js";
import { createViewer } from "./viewer.js";

const element = (id) => document.getElementById(id);

const viewer = createViewer(element("mapa"));
const resumen = element("resumen");

const controls = createControls({
  backgroundRoot: element("controles-fondo"),
  layerRoot: element("controles-capas"),
  onBackground: (url) => viewer.showBackground(url),
  onLayer: (name, visible) => viewer.setLayerVisible(name, visible),
});

const form = createUploadForm({
  form: element("formulario-escena"),
  button: element("boton-analizar"),
  progress: element("progreso"),
  progressBar: element("barra-relleno"),
  progressText: element("progreso-texto"),
  error: element("error"),
  onAnalyse: async (composites, onProgress) => {
    const { result, analysis } = await analyseScene(composites, onProgress);
    show(result);
    controls.showBackgrounds(result.scene.composites, analysis);
  },
});

element("boton-ejemplo").addEventListener("click", async () => {
  try {
    show(await fetchExample());
    resumen.textContent = `Resultado de ejemplo del contrato. ${resumen.textContent}`;
  } catch (failure) {
    form.showError(failure.message);
  }
});

function show(result) {
  viewer.showScene(result.scene);
  viewer.showResult(result);
  controls.showLayers(viewer.availableLayers(result));
  resumen.textContent = describe(result);
}

/** Resumen mínimo; el resumen completo y accesible llega en su propio ticket. */
function describe({ scene, summary }) {
  const area =
    summary.burned_area_ha === null
      ? `${summary.burned_area_px.toLocaleString("es")} píxeles quemados (sin georreferencia, no hay hectáreas)`
      : `${summary.burned_area_ha.toLocaleString("es")} ha quemadas`;
  const zones = `${summary.zone_count} ${summary.zone_count === 1 ? "zona" : "zonas"}`;
  const fires = `${summary.active_fire_count} focos activos`;
  const confidence = `confianza de la superficie quemada ${summary.confidence.burned_area === "high" ? "alta" : "baja"}, de los focos ${summary.confidence.active_fire === "high" ? "alta" : "baja"}`;
  const composites = `composiciones aportadas: ${scene.composites.join(", ")}`;
  return [`${zones}, ${area}`, fires, confidence, composites, ...summary.warnings].join(". ") + ".";
}
