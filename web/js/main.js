// Montaje de la aplicación: une subida, visor, controles, resumen y panel de zonas.
// Cada pieza vive en su fichero para que otros tickets añadan las suyas sin pisarse.

import { analyseScene, fetchExample } from "./api.js";
import { createControls } from "./controls.js";
import { createSummary } from "./status.js";
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
  onAnalyse: async (composites, onProgress) => {
    const { result, analysis } = await analyseScene(composites, onProgress);
    show(result, analysis);
    controls.showBackgrounds(result.scene.composites, analysis);
  },
});

element("example-button").addEventListener("click", async () => {
  try {
    const example = await fetchExample();
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
  zonePanel.show(result);
}

function selectZone(id, { reveal = false } = {}) {
  viewer.selectZone(id, { reveal });
  zonePanel.showSelected(id);
}
