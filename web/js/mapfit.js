// Encaje de la imagen sobre un mapa real: la persona mueve y estira la composición
// semitransparente hasta que ríos y carreteras coinciden, y el recuadro resultante es el bbox.

import { reproject } from "./basemap.js";

const HANDLE = (name) =>
  L.divIcon({ className: `fit-handle fit-handle-${name}`, iconSize: [18, 18], iconAnchor: [9, 9] });

/** Esquinas movibles; cada una fija la opuesta y conserva la proporción original. */
const CORNERS = {
  nw: { fixed: "se", x: -1, y: -1, pick: (bounds) => bounds.getNorthWest() },
  ne: { fixed: "sw", x: 1, y: -1, pick: (bounds) => bounds.getNorthEast() },
  se: { fixed: "nw", x: 1, y: 1, pick: (bounds) => bounds.getSouthEast() },
  sw: { fixed: "ne", x: -1, y: 1, pick: (bounds) => bounds.getSouthWest() },
};
const MIN_WIDTH_PX = 48;

/**
 * Abre el encaje sobre `map`, el mapa del visor ya vacío. Devuelve `{ opacity(value), done(), cancel(), finished }`:
 * `finished` se resuelve con el bbox `{west, south, east, north}` al confirmar o con `null`
 * al cancelar. `aspect` es ancho / alto de la imagen en píxeles.
 */
export function startMapFit(map, imageUrl, aspect) {
  reproject(map, true, { center: [40.2, -3.7], zoom: 6 });
  // Todo lo del encaje va en un grupo, para quitarlo de una vez al terminar.
  const layers = L.layerGroup().addTo(map);

  // Arranca ocupando la mitad del ancho visible, con la proporción de la imagen.
  const size = map.getSize();
  let width = Math.min(size.x / 2, size.y * 0.8 * aspect);
  const height = width / aspect;
  const left = (size.x - width) / 2;
  const top = (size.y - height) / 2;
  let bounds = L.latLngBounds(
    map.containerPointToLatLng([left, top + height]),
    map.containerPointToLatLng([left + width, top]),
  );

  const overlay = L.imageOverlay(imageUrl, bounds, {
    opacity: 0.55,
    alt: "Composición de la escena sobre el mapa",
    interactive: false,
  }).addTo(layers);
  const outline = L.rectangle(bounds, { color: "#22c7e0", weight: 2, fill: false, interactive: false }).addTo(layers);

  const handles = Object.fromEntries(
    Object.entries(CORNERS).map(([name, { pick }]) => [
      name,
      L.marker(pick(bounds), { icon: HANDLE("corner"), draggable: true, keyboard: false, title: "Arrastra para estirar" }).addTo(layers),
    ]),
  );
  const mover = L.marker(bounds.getCenter(), {
    icon: HANDLE("move"),
    draggable: true,
    keyboard: false,
    title: "Arrastra para mover la imagen",
  }).addTo(layers);

  function apply(next) {
    bounds = next;
    overlay.setBounds(bounds);
    outline.setBounds(bounds);
    for (const [name, { pick }] of Object.entries(CORNERS)) handles[name].setLatLng(pick(bounds));
    mover.setLatLng(bounds.getCenter());
  }

  // El tamaño del encaje se mide en píxeles de pantalla: al hacer zoom cambia el mapa
  // que queda debajo, pero la composición conserva el mismo tamaño visible.
  function boundsAround(center) {
    const point = map.latLngToContainerPoint(center);
    const halfHeight = width / aspect / 2;
    return L.latLngBounds(
      map.containerPointToLatLng([point.x - width / 2, point.y + halfHeight]),
      map.containerPointToLatLng([point.x + width / 2, point.y - halfHeight]),
    );
  }

  const keepScreenSize = () => apply(boundsAround(bounds.getCenter()));
  map.on("zoomend", keepScreenSize);

  for (const [name, { fixed, x, y }] of Object.entries(CORNERS)) {
    handles[name].on("drag", () => {
      const anchor = map.latLngToContainerPoint(CORNERS[fixed].pick(bounds));
      const pointer = map.latLngToContainerPoint(handles[name].getLatLng());
      const alongWidth = (pointer.x - anchor.x) * x;
      const alongHeight = (pointer.y - anchor.y) * y;
      // Proyección del arrastre sobre la diagonal permitida (ancho : alto = aspect : 1).
      width = Math.max(MIN_WIDTH_PX, (alongWidth * aspect + alongHeight) * aspect / (aspect * aspect + 1));
      const corner = [anchor.x + x * width, anchor.y + y * width / aspect];
      apply(L.latLngBounds(
        map.containerPointToLatLng(anchor),
        map.containerPointToLatLng(corner),
      ));
    });
  }

  let lastCenter = mover.getLatLng();
  mover.on("dragstart", () => {
    lastCenter = mover.getLatLng();
  });
  mover.on("drag", () => {
    const center = mover.getLatLng();
    const dLat = center.lat - lastCenter.lat;
    const dLng = center.lng - lastCenter.lng;
    lastCenter = center;
    apply(L.latLngBounds(
      [bounds.getSouth() + dLat, bounds.getWest() + dLng],
      [bounds.getNorth() + dLat, bounds.getEast() + dLng],
    ));
  });

  let settle;
  const finished = new Promise((resolve) => {
    settle = (value) => {
      map.off("zoomend", keepScreenSize);
      layers.remove();
      resolve(value);
    };
  });

  return {
    opacity: (value) => overlay.setOpacity(value),
    /** Confirma el encaje actual. */
    done: () =>
      settle({
        west: bounds.getWest(),
        south: bounds.getSouth(),
        east: bounds.getEast(),
        north: bounds.getNorth(),
      }),
    cancel: () => settle(null),
    finished,
  };
}
