// Visor Leaflet en coordenadas de píxel (CRS simple): la escena es el "mundo".
//
// El contrato da las geometrías en píxeles [x, y] con origen arriba a la izquierda,
// así que el visor mapea el píxel (x, y) a L.latLng(-y, x) y la escena queda al
// derecho sin georreferencia de por medio.

/** Colores aptos para daltonismo: morado (quemado), cian (perímetro), ámbar (focos). */
const BURNED = "#8a4fd3";
const PERIMETER = "#22c7e0";
const FIRE_BY_LEVEL = { 1: "#ffd34d", 2: "#ffa600", 3: "#e06a00", 4: "#a83d00" };
const FIRE_ESTIMATED = "#9bb4cc";

/** Nombres de capa del visor → claves de `layers` del contrato. */
export const LAYER_NAMES = ["burned", "severity", "perimeter", "fires"];

const pixelToLatLng = ([x, y]) => L.latLng(-y, x);

export function createViewer(element) {
  const map = L.map(element, {
    crs: L.CRS.Simple,
    minZoom: -6,
    maxZoom: 4,
    zoomSnap: 0,
    attributionControl: false,
  });
  map.setView([0, 0], 0);

  const groups = Object.fromEntries(LAYER_NAMES.map((name) => [name, L.layerGroup().addTo(map)]));
  let bounds = null;
  let background = null;

  function sceneBounds(scene) {
    return L.latLngBounds([-scene.height, 0], [0, scene.width]);
  }

  return {
    /** Encaja el visor en el tamaño de la escena. */
    showScene(scene) {
      bounds = sceneBounds(scene);
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
        className: "fondo-escena",
      }).addTo(map);
      background.bringToBack();
    },

    /** Dibuja las capas del resultado; las que el motor no haya devuelto quedan vacías. */
    showResult(result) {
      for (const group of Object.values(groups)) group.clearLayers();
      if (!bounds) this.showScene(result.scene);

      L.geoJSON(result.zones, {
        coordsToLatLng: pixelToLatLng,
        style: { stroke: false, fillColor: BURNED, fillOpacity: 0.35 },
      }).addTo(groups.burned);
      addMask(groups.burned, result.layers.burned_mask, 0.55, bounds);
      addMask(groups.severity, result.layers.severity_mask, 0.7, bounds);


      L.geoJSON(result.zones, {
        coordsToLatLng: pixelToLatLng,
        style: { color: PERIMETER, weight: 2, fill: false },
        onEachFeature: (feature, layer) => layer.bindTooltip(describeZone(feature.properties)),
      }).addTo(groups.perimeter);

      L.geoJSON(result.active_fires, {
        coordsToLatLng: pixelToLatLng,
        pointToLayer: fireMarker,
        style: (feature) => fireStyle(feature.properties),
        onEachFeature: (feature, layer) => layer.bindTooltip(describeFire(feature.properties)),
      }).addTo(groups.fires);
    },

    /** Qué capas tienen algo que mostrar con este resultado. */
    availableLayers(result) {
      const zones = result.zones.features.length > 0;
      return {
        burned: zones || servedMask(result.layers.burned_mask),
        severity: servedMask(result.layers.severity_mask),
        perimeter: zones,
        fires: result.active_fires.features.length > 0,
      };
    },

    setLayerVisible(name, visible) {
      if (visible) groups[name].addTo(map);
      else map.removeLayer(groups[name]);
    },
  };
}

/**
 * El contrato da las capas como rutas relativas al directorio de salida del motor; solo
 * son dibujables cuando la API las ha reescrito a una URL suya (así el ejemplo del
 * contrato, cuyos PNG no existen en el servidor, no deja overlays rotos ni capas vacías).
 */
function servedMask(path) {
  return typeof path === "string" && path.startsWith("/");
}

function addMask(group, url, opacity, bounds) {
  if (servedMask(url) && bounds) L.imageOverlay(url, bounds, { opacity }).addTo(group);
}

/** Triángulo SVG: forma distinta de la superficie quemada, no solo otro color. */
function fireMarker(feature, latlng) {
  const { level, source } = feature.properties;
  const side = 12 + 3 * (level ?? 1);
  const estimated = source === "swir";
  const colour = estimated ? FIRE_ESTIMATED : FIRE_BY_LEVEL[level];
  const icon = L.divIcon({
    className: "foco",
    iconSize: [side, side],
    iconAnchor: [side / 2, side / 2],
    html: `<svg viewBox="0 0 12 12" width="${side}" height="${side}" aria-hidden="true">
        <polygon points="6,0.7 11.3,11.3 0.7,11.3"
          fill="${estimated ? "none" : colour}" stroke="${colour}"
          stroke-width="${estimated ? 2 : 1.2}" stroke-dasharray="${estimated ? "2 1.5" : "none"}" />
      </svg>`,
  });
  const label = describeFire(feature.properties);
  return L.marker(latlng, { icon, title: label, alt: label, keyboard: false });
}

function fireStyle({ level, source }) {
  const colour = source === "swir" ? FIRE_ESTIMATED : FIRE_BY_LEVEL[level];
  return { color: colour, weight: 2, fillColor: colour, fillOpacity: 0.5, dashArray: "3 2" };
}

function describeFire({ level, source }) {
  if (source === "swir") return "Foco activo estimado desde la SWIR (sin nivel, confianza baja)";
  return `Foco activo de nivel ${level} de 4 (composición Wildfires)`;
}

function describeZone({ id, area_px, area_ha, share_of_burned }) {
  const area = area_ha === null ? `${area_px.toLocaleString("es")} píxeles` : `${area_ha} ha`;
  return `Zona ${id}: ${area} · ${Math.round(share_of_burned * 100)} % de lo quemado`;
}
