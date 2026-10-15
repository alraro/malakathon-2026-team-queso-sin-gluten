// Visor Leaflet en coordenadas de píxel (CRS simple): la escena es el "mundo".
//
// El contrato da las geometrías en píxeles [x, y] con origen arriba a la izquierda,
// así que el visor mapea el píxel (x, y) a L.latLng(-y, x) y la escena queda al
// derecho sin georreferencia de por medio.

import { layerUrl } from "./api.js";
import { zoneCard } from "./card.js";

/**
 * Colores aptos para daltonismo, sin rojo frente a verde: la superficie quemada y su
 * severidad las pinta el motor en naranja y vino (`layers.py`); aquí, cian para el
 * perímetro y ámbar para los focos, que además tienen forma propia (triángulo).
 */
const PERIMETER = "#22c7e0";
const HIDDEN_ZONE = { stroke: false, fill: true, fillOpacity: 0 };
const HOVERED_ZONE = { stroke: true, color: "#ffffff", weight: 3, fill: true, fillColor: PERIMETER, fillOpacity: 0.12 };
const SELECTED_ZONE = { ...HOVERED_ZONE, weight: 4, fillOpacity: 0.2 };
const FIRE_BY_LEVEL = { 1: "#ffd34d", 2: "#ffa600", 3: "#e06a00", 4: "#a83d00" };
const ESTIMATED_FIRE = "#9bb4cc";

/** Capas del visor, con el nombre del dominio (CONTEXT.md). */
export const LAYERS = ["burned_area", "relative_severity", "perimeter", "active_fire"];

const pixelToLatLng = ([x, y]) => L.latLng(-y, x);

/**
 * `onZoneSelect(id)` se llama al hacer clic en una zona del visor; el resalte al pasar
 * el ratón y su tarjeta flotante los lleva el propio visor.
 */
export function createViewer(element, { onZoneSelect = () => {} } = {}) {
  const map = L.map(element, {
    crs: L.CRS.Simple,
    minZoom: -6,
    maxZoom: 4,
    zoomSnap: 0,
    attributionControl: false,
  });
  map.setView([0, 0], 0);

  const groups = Object.fromEntries(LAYERS.map((name) => [name, L.layerGroup().addTo(map)]));
  // Las zonas reciben el ratón aunque el perímetro esté apagado: van en su propia capa,
  // transparente salvo cuando se resaltan.
  const zoneGroup = L.layerGroup().addTo(map);
  const zoneLayers = new Map();
  let hovered = null;
  let selected = null;
  let bounds = null;
  let background = null;
  let shown = null;

  function restyleZones() {
    for (const [id, layer] of zoneLayers) {
      if (id === hovered) layer.setStyle(HOVERED_ZONE);
      else if (id === selected) layer.setStyle(SELECTED_ZONE);
      else layer.setStyle(HIDDEN_ZONE);
    }
    zoneLayers.get(selected)?.bringToFront();
    zoneLayers.get(hovered)?.bringToFront();
  }

  return {
    /** Encaja el visor en el tamaño de la escena. */
    showScene(scene) {
      bounds = L.latLngBounds([-scene.height, 0], [0, scene.width]);
      map.setMaxBounds(bounds.pad(0.25));
      map.fitBounds(bounds);
    },

    /** Pone (o quita, con `null`) la composición de fondo. */
    showBackground(url) {
      if (background) {
        map.removeLayer(background);
        background = null;
      }
      if (!url || !bounds) return;
      background = L.imageOverlay(url, bounds, {
        alt: "Composición de la escena",
        className: "scene-background",
      }).addTo(map);
      background.bringToBack();
    },

    /**
     * Dibuja las capas del resultado. `analysis` es la ruta del análisis en la API, de
     * donde cuelgan las capas PNG; sin ella (resultado de ejemplo) solo hay geometrías.
     */
    showResult(result, analysis = null) {
      shown = { result, analysis };
      for (const group of Object.values(groups)) group.clearLayers();
      zoneGroup.clearLayers();
      zoneLayers.clear();
      hovered = null;
      selected = null;
      if (!bounds) this.showScene(result.scene);

      // La superficie quemada son los píxeles de la máscara, no el polígono del
      // perímetro: dentro del perímetro quedan islas sin quemar.
      addMask(groups.burned_area, layerUrl(analysis, result.layers.burned_mask), 0.55, bounds);
      addMask(
        groups.relative_severity,
        layerUrl(analysis, result.layers.severity_mask),
        0.7,
        bounds,
      );

      L.geoJSON(result.zones, {
        coordsToLatLng: pixelToLatLng,
        style: { color: PERIMETER, weight: 2, fill: false },
        interactive: false,
      }).addTo(groups.perimeter);

      L.geoJSON(result.zones, {
        coordsToLatLng: pixelToLatLng,
        style: HIDDEN_ZONE,
        onEachFeature: (feature, layer) => {
          const { id } = feature.properties;
          zoneLayers.set(id, layer);
          layer.bindTooltip(() => zoneCard(feature.properties, result.scene), {
            sticky: true,
            direction: "auto",
            offset: [12, 0],
            className: "zone-tooltip",
          });
          layer.on("mouseover", () => {
            hovered = id;
            restyleZones();
          });
          layer.on("mouseout", () => {
            hovered = null;
            restyleZones();
          });
          layer.on("click", () => onZoneSelect(id));
        },
      }).addTo(zoneGroup);

      L.geoJSON(result.active_fires, {
        coordsToLatLng: pixelToLatLng,
        pointToLayer: fireMarker,
        style: (feature) => fireStyle(appearanceOf(feature.properties)),
        onEachFeature: (feature, layer) => layer.bindTooltip(appearanceOf(feature.properties).label),
      }).addTo(groups.active_fire);
    },

    /** Qué capas tienen algo que mostrar con el resultado que se está viendo. */
    availableLayers() {
      const { result, analysis } = shown;
      return {
        burned_area: Boolean(layerUrl(analysis, result.layers.burned_mask)),
        relative_severity: Boolean(layerUrl(analysis, result.layers.severity_mask)),
        perimeter: result.zones.features.length > 0,
        active_fire: result.active_fires.features.length > 0,
      };
    },

    /**
     * Resalta la zona `id` (o ninguna, con `null`). Con `reveal`, si no se ve entera,
     * mueve el visor hasta ella.
     */
    selectZone(id, { reveal = false } = {}) {
      selected = id;
      restyleZones();
      const layer = zoneLayers.get(id);
      if (reveal && layer && !map.getBounds().contains(layer.getBounds())) {
        const animate = !window.matchMedia("(prefers-reduced-motion: reduce)").matches;
        map.fitBounds(layer.getBounds().pad(0.3), { animate });
      }
    },

    setLayerVisible(name, visible) {
      if (visible) groups[name].addTo(map);
      else map.removeLayer(groups[name]);
    },
  };
}

function addMask(group, url, opacity, bounds) {
  if (url && bounds) L.imageOverlay(url, bounds, { opacity }).addTo(group);
}

/** Color, relleno y texto de un foco activo, según su fuente y su nivel. */
function appearanceOf({ level, source }) {
  if (source === "swir") {
    return {
      colour: ESTIMATED_FIRE,
      filled: false,
      label: "Foco activo estimado desde la SWIR (sin nivel, confianza baja)",
    };
  }
  return {
    colour: FIRE_BY_LEVEL[level],
    filled: true,
    label: `Foco activo de nivel ${level} de 4 (composición Wildfires)`,
    level,
  };
}

/** Triángulo SVG: forma distinta de la superficie quemada, no solo otro color. */
function fireMarker(feature, latlng) {
  const { colour, filled, label, level } = appearanceOf(feature.properties);
  const side = 12 + 3 * (level ?? 1);
  const icon = L.divIcon({
    className: "active-fire",
    iconSize: [side, side],
    iconAnchor: [side / 2, side / 2],
    html: `<svg viewBox="0 0 12 12" width="${side}" height="${side}" aria-hidden="true">
        <polygon points="6,0.7 11.3,11.3 0.7,11.3"
          fill="${filled ? colour : "none"}" stroke="${colour}"
          stroke-width="${filled ? 1.2 : 2}" stroke-dasharray="${filled ? "none" : "2 1.5"}" />
      </svg>`,
  });
  return L.marker(latlng, { icon, title: label, alt: label, keyboard: false });
}

function fireStyle({ colour }) {
  return { color: colour, weight: 2, fillColor: colour, fillOpacity: 0.5, dashArray: "3 2" };
}
