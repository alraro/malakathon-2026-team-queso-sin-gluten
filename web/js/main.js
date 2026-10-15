// Montaje de la aplicación: une pantallas, subida, visor, «Fondo y capas» y la columna
// de resultados (Resumen, Zonas y Poblaciones).
// Cada pieza vive en su fichero para que otros tickets añadan las suyas sin pisarse.

import { analyseScene, compositeUrl } from "./api.js";
import { createAlertPanel } from "./alerts.js";
import { createLayerPanel } from "./layers.js";
import { createSummary } from "./status.js";
import { startMapFit } from "./mapfit.js";
import { createProgress } from "./progress.js";
import { showScreen } from "./screens.js";
import { createTabs } from "./tabs.js";
import { setUpThemeToggles } from "./theme.js";
import { createUploadForm } from "./upload.js";
import { createViewer } from "./viewer.js";
import { createZonePanel } from "./zones.js";

const element = (id) => document.getElementById(id);

setUpThemeToggles();

// Un clic en una zona del mapa la despliega en la pestaña Zonas.
const viewer = createViewer(element("map"), {
  onZoneSelect: (id) => {
    selectZone(id);
    if (id !== null) tabs.show("zones");
  },
});

const tabs = createTabs(element("result-tabs"));

const zonePanel = createZonePanel({ panel: element("panel-zones"), onSelect: selectZone });

const summary = createSummary({
  chips: element("scene-chips"),
  status: element("status"),
  panel: element("panel-summary"),
  onFit: fitOnMap,
});

const alertPanel = createAlertPanel({ panel: element("panel-settlements") });

const layerPanel = createLayerPanel({
  panel: element("layers-panel"),
  openButton: element("layers-open"),
  closeButton: element("layers-close"),
  backgroundRoot: element("background-controls"),
  layerRoot: element("layer-controls"),
  onBackground: (url) => viewer.showBackground(url),
  onLayer: (name, visible) => viewer.setLayerVisible(name, visible),
});

const progress = createProgress({
  text: element("progress-text"),
  percent: element("progress-percent"),
  bar: element("progress-bar"),
  note: element("progress-note"),
});

const form = createUploadForm({
  form: element("scene-form"),
  error: element("error"),
  onAnalyse: async (composites, bbox) => {
    const { result, analysis } = await analyse(composites, bbox, "manual", "new");
    showAnalysis(result, analysis, composites);
  },
});

// Lo último analizado: el encaje sobre el mapa relanza el cálculo con los mismos archivos.
let current = null;
// El encaje abierto, si lo hay: «Nueva escena» lo abandona.
let openFit = null;

/**
 * Analiza con la pantalla «Análisis en curso» delante. Si falla, vuelve a `fallback` y
 * deja que quien llama enseñe el error.
 */
async function analyse(composites, bbox, source, fallback) {
  progress.show({ phase: "upload", ratio: 0 });
  showScreen("load");
  try {
    return await analyseScene(composites, bbox, progress.show, source);
  } catch (failure) {
    showScreen(fallback);
    throw failure;
  }
}

function showWorkError(message) {
  element("work-error").textContent = message;
  element("work-error").hidden = !message;
}

function showAnalysis(result, analysis, composites) {
  current = { result, analysis, composites };
  // El visor tiene que estar a la vista antes de encajar la escena: Leaflet mide su tamaño.
  showScreen("work");
  viewer.showScene(result.scene);
  viewer.showResult(result, analysis);
  const fires = result.active_fires.features;
  layerPanel.showLayers(viewer.availableLayers(), {
    estimated: fires.length > 0 && fires.every((fire) => fire.properties.source === "swir"),
  });
  layerPanel.showBackgrounds(result.scene.composites, analysis);
  summary.show(result);
  zonePanel.show(result);
  alertPanel.show(result);
  const zoneCount = result.zones.features.length;
  tabs.set("zones", { count: zoneCount });
  // Sin georreferencia no se sabe dónde está la escena: no hay poblaciones que buscar.
  tabs.set("settlements", { count: result.alerts.length, available: Boolean(result.scene.georeference) });
  tabs.show("summary");
  element("map-empty").hidden = zoneCount > 0;
}

/** Mientras se encaja, el mapa se queda solo con la imagen y el panel del encaje. */
function showFitMode(fitting) {
  element("fit-panel").hidden = !fitting;
  element("results").hidden = fitting;
  layerPanel.setFitting(fitting);
  if (fitting) element("map-empty").hidden = true;
}

async function fitOnMap() {
  const { result, analysis, composites } = current;
  const opacity = element("fit-opacity");
  const opacityValue = element("fit-opacity-value");
  opacity.value = 60;
  showWorkError("");
  showFitMode(true);
  summary.showChips(result, { fitting: true });
  viewer.clear();
  const fit = (openFit = startMapFit(
    viewer.map(),
    compositeUrl(analysis, "swir"),
    result.scene.width / result.scene.height,
  ));
  const onOpacity = () => {
    fit.opacity(Number(opacity.value) / 100);
    opacityValue.textContent = `${opacity.value} %`;
  };
  onOpacity();
  opacity.addEventListener("input", onOpacity);
  element("fit-done").onclick = () => fit.done();
  element("fit-cancel").onclick = () => fit.cancel();

  const bbox = await fit.finished;
  openFit = null;
  opacity.removeEventListener("input", onOpacity);
  showFitMode(false);
  // Se ha abandonado con «Nueva escena»: no hay escena a la que volver.
  if (current === null) return;
  if (!bbox) {
    showAnalysis(result, analysis, composites);
    return;
  }
  try {
    const next = await analyse({ ...composites, geotiff: null }, bbox, "map_fit", "work");
    showAnalysis(next.result, next.analysis, composites);
  } catch (failure) {
    showAnalysis(result, analysis, composites);
    showWorkError(failure.message);
  }
}

element("new-scene").addEventListener("click", () => {
  current = null;
  openFit?.cancel();
  viewer.clear();
  showWorkError("");
  form.reset();
  showScreen("new");
});

function selectZone(id, { reveal = false } = {}) {
  viewer.selectZone(id, { reveal });
  zonePanel.showSelected(id);
}
