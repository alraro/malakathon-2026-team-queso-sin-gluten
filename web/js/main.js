// Montaje de la aplicación: une subida, visor, controles, resumen y panel de zonas.
// Cada pieza vive en su fichero para que otros tickets añadan las suyas sin pisarse.

import { analyseScene, compositeUrl, fetchExample } from "./api.js";
import { createControls } from "./controls.js";
import { createSummary } from "./status.js";
import { startMapFit } from "./mapfit.js";
import { createUploadForm } from "./upload.js";
import { createViewer } from "./viewer.js";
import { createZonePanel } from "./zones.js";

const element = (id) => document.getElementById(id);

const viewer = createViewer(element("map"), { onZoneSelect: (id) => selectZone(id) });

const zonePanel = createZonePanel({
  list: element("zone-list"),
  card: element("zone-card"),
  onSelect: selectZone,
});

const summary = createSummary({
  root: element("results"),
  status: element("status"),
  facts: element("summary-facts"),
  warnings: element("summary-warnings"),
});

const controls = createControls({
  backgroundRoot: element("background-controls"),
  layerRoot: element("layer-controls"),
  onBackground: (url) => viewer.showBackground(url),
  onLayer: (name, visible) => viewer.setLayerVisible(name, visible),
});

const form = createUploadForm({
  form: element("scene-form"),
  button: element("analyse-button"),
  progress: element("progress"),
  progressBar: element("progress-bar"),
  progressText: element("progress-text"),
  error: element("error"),
  onAnalyse: async (composites, bbox, onProgress) => {
    const { result, analysis } = await analyseScene(composites, bbox, onProgress);
    showAnalysis(result, analysis, composites);
  },
});

// Lo último analizado: el encaje sobre el mapa relanza el cálculo con los mismos archivos.
let current = null;

function showAnalysis(result, analysis, composites) {
  current = { result, analysis, composites };
  show(result, analysis);
  controls.showBackgrounds(result.scene.composites, analysis);
}

element("fit-button").addEventListener("click", fitOnMap);

async function fitOnMap() {
  const { result, analysis, composites } = current;
  const opacity = element("fit-opacity");
  element("results").hidden = true;
  element("fit-panel").hidden = false;
  viewer.release();
  const fit = startMapFit(
    element("map"),
    compositeUrl(analysis, "swir"),
    result.scene.width / result.scene.height,
  );
  const onOpacity = () => fit.opacity(Number(opacity.value) / 100);
  opacity.addEventListener("input", onOpacity);
  element("fit-done").onclick = () => fit.done();
  element("fit-cancel").onclick = () => fit.cancel();

  const bbox = await fit.finished;
  opacity.removeEventListener("input", onOpacity);
  element("fit-panel").hidden = true;
  if (!bbox) {
    showAnalysis(result, analysis, composites);
    return;
  }
  form.showError("");
  try {
    const next = await analyseScene({ ...composites, geotiff: null }, bbox, () => {}, "map_fit");
    showAnalysis(next.result, next.analysis, composites);
  } catch (failure) {
    form.showError(failure.message);
    showAnalysis(result, analysis, composites);
  }
}

element("example-button").addEventListener("click", async () => {
  try {
    const example = await fetchExample();
    current = null;
    show(example, null, { example: true });
  } catch (failure) {
    form.showError(failure.message);
  }
});

function show(result, analysis = null, { example = false } = {}) {
  viewer.showScene(result.scene);
  viewer.showResult(result, analysis);
  controls.showLayers(viewer.availableLayers());
  summary.show(result, { example });
  element("georef-offer").hidden = example || Boolean(result.scene.georeference);
  zonePanel.show(result);
}

function selectZone(id, { reveal = false } = {}) {
  viewer.selectZone(id, { reveal });
  zonePanel.showSelected(id);
}
