// Tarjetas de datos en el DOM: cada cifra con su unidad y el supuesto del que depende.
// La tarjeta flotante del visor lleva el supuesto debajo; la columna de resultados, en un ⓘ.

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

let tips = 0;

/** ⓘ que explica una cifra; se abre al pasar el ratón y con el foco (solo CSS). */
export function infoButton(note, label) {
  const id = `info-tip-${++tips}`;
  const wrapper = text("span", "", "info");
  const button = text("button", "i", "info__btn");
  button.type = "button";
  button.setAttribute("aria-label", label);
  button.setAttribute("aria-describedby", id);
  const tip = text("span", note, "info__tip");
  tip.id = id;
  tip.setAttribute("role", "tooltip");
  wrapper.append(button, tip);
  return wrapper;
}

/**
 * Una cifra con su ⓘ, con el marcado del diseño: `block` es «fact» en el resumen y
 * «zfield» en el detalle de una zona. Lo no disponible sale atenuado y su ⓘ dice cómo
 * obtenerlo.
 */
export function factRow({ label, value, note, unavailable }, block = "fact") {
  const row = text("div", "", unavailable ? `${block} is-na` : block);
  const head = text("div", "", `${block}__head`);
  head.append(text("span", label), infoButton(note, `De dónde sale: ${label}`));
  row.append(head, text("div", value, unavailable ? `${block}__na` : `${block}__val`));
  return row;
}

export function text(tag, content, className) {
  const node = document.createElement(tag);
  node.textContent = content;
  if (className) node.className = className;
  return node;
}
