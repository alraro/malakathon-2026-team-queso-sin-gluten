// Montaje de la aplicación: une subida, visor, controles y estado.
// Cada pieza vive en su fichero para que otros tickets añadan las suyas sin pisarse.

import { analyseScene, fetchExample } from "./api.js";
import { createControls } from "./controls.js";
import { EXAMPLE_NOTICE, describeScene } from "./status.js";
import { renderMetrics } from "./metrics.js";
import { createUploadForm } from "./upload.js";
import { createViewer } from "./viewer.js";

const element = (id) => document.getElementById(id);

const viewer = createViewer(element("map"));
const status = element("status");

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
    show(result, analysis);
    controls.showBackgrounds(result.scene.composites, analysis);
    status.textContent = describeScene(result);
  },
});

element("example-button").addEventListener("click", async () => {
  try {
    const example = await fetchExample();
    show(example);
    status.textContent = `${EXAMPLE_NOTICE} ${describeScene(example)}`;
  } catch (failure) {
    form.showError(failure.message);
  }
});

function show(result, analysis = null) {
  viewer.showScene(result.scene);
  viewer.showResult(result, analysis);
  controls.showLayers(viewer.availableLayers());
  renderMetrics(element("metric-summary"), element("zone-cards"), result);
}
