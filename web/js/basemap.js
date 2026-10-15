// El mapa Leaflet de la app se crea una sola vez y se reutiliza: el visor lo usa en
// píxeles (CRS simple) o en lon/lat sobre el mapa satelital, y el encaje siempre en lon/lat.
// Aquí se cambia de una proyección a otra sin volver a crearlo.

const SATELLITE = L.tileLayer("https://services.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}", {
  maxNativeZoom: 19,
  maxZoom: 19,
  attribution: 'Imágenes: &copy; <a href="https://www.esri.com/">Esri</a>, Maxar, Earthstar Geographics y la comunidad GIS',
});

/** El mapa único, sobre `element`. Hay que llamarlo con el elemento ya visible. */
export function createMap(element) {
  // Evita que Leaflet escale temporalmente la composición durante el zoom del encaje.
  const map = L.map(element, { crs: L.CRS.Simple, zoomSnap: 0, zoomAnimation: false });
  map.attributionControl.setPrefix(false);
  return map;
}

/**
 * Pasa `map` a lon/lat con el mapa base (`geographic`) o a píxeles sin él, y encuadra
 * `view`: `{bounds}` o `{center, zoom}`. Las capas que hubiera en el mapa se proyectaron
 * con la proyección anterior: hay que quitarlas antes.
 */
export function reproject(map, geographic, view) {
  SATELLITE.remove();
  map.setMaxBounds(null);
  map.options.crs = geographic ? L.CRS.EPSG3857 : L.CRS.Simple;
  map.options.minZoom = geographic ? 0 : -6;
  map.options.maxZoom = geographic ? 19 : 4;
  // Las coordenadas del encuadre cambian de significado con la proyección: hay que
  // recalcular el origen de la vista (`reset`), no animar desde la anterior.
  map.invalidateSize({ pan: false });
  if (view.bounds) map.fitBounds(view.bounds, { reset: true });
  else map.setView(view.center, view.zoom, { reset: true });
  if (geographic) SATELLITE.addTo(map);
}
