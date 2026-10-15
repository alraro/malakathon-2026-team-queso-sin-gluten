// El mapa Leaflet de la app se crea una sola vez y se reutiliza: el visor lo usa en
// píxeles (CRS simple) o en lon/lat sobre OpenStreetMap, y el encaje siempre en lon/lat.
// Aquí se cambia de una proyección a otra sin volver a crearlo.

const OSM = L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
  maxZoom: 19,
  attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
});

/** El mapa único, sobre `element`. Hay que llamarlo con el elemento ya visible. */
export function createMap(element) {
  const map = L.map(element, { crs: L.CRS.Simple, zoomSnap: 0 });
  map.attributionControl.setPrefix(false);
  return map;
}

/**
 * Pasa `map` a lon/lat con el mapa base (`geographic`) o a píxeles sin él, y encuadra
 * `view`: `{bounds}` o `{center, zoom}`. Las capas que hubiera en el mapa se proyectaron
 * con la proyección anterior: hay que quitarlas antes.
 */
export function reproject(map, geographic, view) {
  OSM.remove();
  map.setMaxBounds(null);
  map.options.crs = geographic ? L.CRS.EPSG3857 : L.CRS.Simple;
  map.options.minZoom = geographic ? 0 : -6;
  map.options.maxZoom = geographic ? 19 : 4;
  // Las coordenadas del encuadre cambian de significado con la proyección: hay que
  // recalcular el origen de la vista (`reset`), no animar desde la anterior.
  map.invalidateSize({ pan: false });
  if (view.bounds) map.fitBounds(view.bounds, { reset: true });
  else map.setView(view.center, view.zoom, { reset: true });
  if (geographic) OSM.addTo(map);
}
