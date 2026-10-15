// Visor Leaflet en píxeles (CRS simple) o en lon/lat (Web Mercator) con bbox.
//
// El contrato da las geometrías en píxeles [x, y] con origen arriba a la izquierda,
// así que el visor mapea el píxel (x, y) a L.latLng(-y, x) y la escena queda al
// derecho sin georreferencia de por medio.

import { layerUrl } from "./api.js";
import { createMap, reproject } from "./basemap.js";
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
 * `onZoneSelect(id)` se llama al hacer clic en una zona del visor (`null` al volver a
 * hacer clic en la seleccionada o en un hueco del mapa); el resalte al pasar el ratón y
 * su tarjeta flotante los lleva el propio visor.
 */
export function createViewer(element, { onZoneSelect = () => {} } = {}) {
  let map = null;
  let groups = null;
  // Las zonas reciben el ratón aunque el perímetro esté apagado: van en su propia capa,
  // transparente salvo cuando se resaltan.
  let zoneGroup = null;
  const zoneLayers = new Map();
  const zoneByElement = new Map();
  const zoneCards = new Map();
  // Una sola tarjeta flotante para todo el visor: nunca puede haber dos abiertas.
  const card = L.tooltip({ direction: "auto", offset: [14, 0], className: "zone-tooltip", opacity: 1 });
  let hovered = null;
  let selected = null;
  let pointer = null; // última posición del ratón dentro del visor
  let bounds = null;
  let background = null;
  let shown = null;
  let geographic = false;

  /** El mapa se crea la primera vez que hace falta (con el visor ya visible) y nunca más. */
  function ensureMap() {
    if (!map) {
      map = createMap(element);
      bindMapEvents();
    }
    return map;
  }

  /** Quita todo lo que el visor ha puesto en el mapa; el mapa sigue vivo. */
  function clear() {
    if (!map) return;
    for (const group of Object.values(groups ?? {})) map.removeLayer(group);
    if (zoneGroup) map.removeLayer(zoneGroup);
    if (background) map.removeLayer(background);
    map.closeTooltip(card);
    groups = null;
    zoneGroup = null;
    background = null;
    bounds = null;
    shown = null;
    zoneLayers.clear();
    zoneByElement.clear();
    zoneCards.clear();
    hovered = null;
    selected = null;
  }

  /** Como mucho una zona resaltada: la que está bajo el cursor, o si no la seleccionada. */
  function restyleZones() {
    const lit = hovered ?? selected;
    for (const [id, layer] of zoneLayers) {
      if (id !== lit) layer.setStyle(HIDDEN_ZONE);
    }
    const layer = zoneLayers.get(lit);
    if (layer) {
      layer.setStyle(lit === hovered ? HOVERED_ZONE : SELECTED_ZONE);
      layer.bringToFront();
    }
  }

  function setHovered(id, latlng) {
    if (id !== hovered) {
      hovered = id;
      restyleZones();
      if (id === null) map.closeTooltip(card);
      else card.setContent(zoneCards.get(id));
    }
    if (id !== null) {
      card.setLatLng(latlng);
      if (!map.hasLayer(card)) map.openTooltip(card);
    }
  }

  // La zona bajo el cursor se recalcula a partir del elemento que hay debajo, en vez de
  // fiarse de que llegue cada mouseout: se pierden al arrastrar, al hacer zoom o al hacer
  // clic. Se recalcula al mover el ratón y también cuando se mueve el mapa con el ratón
  // quieto (la inercia de un arrastre, un zoom con la rueda).
  function refreshHovered() {
    if (!map) return;
    if (!pointer) {
      setHovered(null);
      return;
    }
    const under = document.elementFromPoint(pointer.clientX, pointer.clientY);
    setHovered(zoneByElement.get(under) ?? null, map.mouseEventToLatLng(pointer));
  }
  element.addEventListener("mousemove", ({ clientX, clientY }) => {
    pointer = { clientX, clientY };
    refreshHovered();
  });
  element.addEventListener("mouseleave", () => {
    pointer = null;
    refreshHovered();
  });

  function bindMapEvents() {
    map.on("move zoomend moveend", refreshHovered);
    // Un clic en un hueco del mapa (ni zona ni foco) suelta la selección.
    map.on("click", ({ originalEvent }) => {
      const target = originalEvent.target;
      if (!zoneByElement.has(target) && !target.closest(".leaflet-marker-icon")) onZoneSelect(null);
    });
  }

  return {
    /** Encaja el visor en el tamaño de la escena. */
    showScene(scene) {
      ensureMap();
      clear();
      geographic = Boolean(scene.georeference);
      if (geographic) {
        const [west, south, east, north] = scene.georeference.bbox;
        bounds = L.latLngBounds([south, west], [north, east]);
      } else {
        bounds = L.latLngBounds([-scene.height, 0], [0, scene.width]);
      }
      reproject(map, geographic, { bounds });
      if (!geographic) map.setMaxBounds(bounds.pad(0.25));
      groups = Object.fromEntries(LAYERS.map((name) => [name, L.layerGroup().addTo(map)]));
      zoneGroup = L.layerGroup().addTo(map);
    },

    /** Deja el mapa vacío, p. ej. para el encaje o para una escena nueva. */
    clear,

    /** El mapa Leaflet del visor, para que el encaje lo use sin crear otro. */
    map: ensureMap,

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
        opacity: geographic ? 0.6 : 1,
      }).addTo(map);
      background.bringToBack();
    },

    /**
     * Dibuja las capas del resultado. `analysis` es la ruta del análisis en la API, de
     * donde cuelgan las capas PNG.
     */
    showResult(result, analysis = null) {
      if (!bounds) this.showScene(result.scene);
      shown = { result, analysis };
      for (const group of Object.values(groups)) group.clearLayers();
      zoneGroup.clearLayers();
      zoneLayers.clear();
      zoneByElement.clear();
      zoneCards.clear();
      map.closeTooltip(card);
      hovered = null;
      selected = null;

      // La superficie quemada son los píxeles de la máscara, no el polígono del
      // perímetro: dentro del perímetro quedan islas sin quemar.
      addMask(groups.burned_area, layerUrl(analysis, result.layers.burned_mask), 0.55, bounds);
      addMask(
        groups.relative_severity,
        layerUrl(analysis, result.layers.severity_mask),
        0.7,
        bounds,
      );

      const sceneIsGeographic = Boolean(result.scene.georeference);
      L.geoJSON(displayFeatures(result.zones, sceneIsGeographic), {
        coordsToLatLng: sceneIsGeographic ? undefined : pixelToLatLng,
        style: { color: PERIMETER, weight: 2, fill: false },
        interactive: false,
      }).addTo(groups.perimeter);

      L.geoJSON(displayFeatures(result.zones, sceneIsGeographic), {
        coordsToLatLng: sceneIsGeographic ? undefined : pixelToLatLng,
        style: HIDDEN_ZONE,
        onEachFeature: (feature, layer) => {
          const { id } = feature.properties;
          zoneLayers.set(id, layer);
          zoneCards.set(id, zoneCard(feature.properties, result.scene));
          // Volver a hacer clic en la zona seleccionada la suelta.
          layer.on("click", () => onZoneSelect(id === selected ? null : id));
        },
      }).addTo(zoneGroup);
      // Los elementos SVG existen ya que la capa está en el mapa.
      for (const [id, layer] of zoneLayers) zoneByElement.set(layer.getElement(), id);

      L.geoJSON(displayFeatures(result.active_fires, sceneIsGeographic), {
        coordsToLatLng: sceneIsGeographic ? undefined : pixelToLatLng,
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

function displayFeatures(collection, geographic) {
  if (!geographic) return collection;
  return {
    type: "FeatureCollection",
    features: collection.features.map((feature) => ({
      ...feature,
      geometry: feature.properties.geo_geometry,
    })),
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
    html: `<svg viewBox="0 0 12 12" width="${side}" height="${side}" role="img" aria-label="${label}">
        <polygon points="6,0.7 11.3,11.3 0.7,11.3"
          fill="${filled ? colour : "none"}" stroke="${colour}"
          stroke-width="${filled ? 1.2 : 2}" stroke-dasharray="${filled ? "none" : "2 1.5"}" />
      </svg>`,
  });
  // Sin `title`: el navegador sacaría su propio tooltip encima del de Leaflet.
  return L.marker(latlng, { icon, keyboard: false });
}

function fireStyle({ colour }) {
  return { color: colour, weight: 2, fillColor: colour, fillOpacity: 0.5, dashArray: "3 2" };
}
