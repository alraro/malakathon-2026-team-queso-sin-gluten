// Tarjetas de datos en el DOM: cada cifra con su unidad y, debajo, el supuesto del que
// depende. Las usan la tarjeta flotante del visor, el panel de zonas y el resumen.

import { describeZone, zoneTitle } from "./describe.js";

/** Lista de definiciones a partir de los datos de `describe.js`. */
export function factList(facts) {
  const list = document.createElement("dl");
  list.className = "facts";
  for (const { label, value, note, unavailable } of facts) {
    const detail = document.createElement("dd");
    if (unavailable) detail.className = "unavailable";
    detail.append(text("span", value, "value"));
    if (note) detail.append(text("span", note, "note"));
    list.append(text("dt", label), detail);
  }
  return list;
}

/** Tarjeta de una zona (`zone` son las `properties` del contrato). */
export function zoneCard(zone, scene) {
  const card = document.createElement("article");
  card.className = "zone-card";
  card.append(text("h3", zoneTitle(zone)), factList(describeZone(zone, scene)));
  return card;
}

function text(tag, content, className) {
  const node = document.createElement(tag);
  node.textContent = content;
  if (className) node.className = className;
  return node;
}
