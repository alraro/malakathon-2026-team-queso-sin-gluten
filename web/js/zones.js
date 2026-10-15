// Panel de zonas: la lista de zonas del resultado y la tarjeta de la seleccionada.
//
// La lista se recorre con el teclado como un único control: Tab entra en la zona
// seleccionada, las flechas (e Inicio/Fin) pasan de una a otra y Escape quita la
// selección. Elegir una zona avisa a `onSelect`, que la resalta también en el visor.

import { zoneCard } from "./card.js";
import { zoneLine, zoneTitle } from "./describe.js";

const STEPS = { ArrowDown: 1, ArrowRight: 1, ArrowUp: -1, ArrowLeft: -1 };

export function createZonePanel({ list, card, onSelect }) {
  let zones = [];
  let scene = null;
  let buttons = [];

  list.addEventListener("keydown", (event) => {
    const current = buttons.indexOf(document.activeElement);
    if (current === -1) return;
    let next = null;
    if (event.key in STEPS) next = (current + STEPS[event.key] + buttons.length) % buttons.length;
    else if (event.key === "Home") next = 0;
    else if (event.key === "End") next = buttons.length - 1;
    else if (event.key === "Escape") {
      event.preventDefault();
      onSelect(null);
      return;
    } else return;
    event.preventDefault();
    buttons[next].focus();
    onSelect(zones[next].id, { reveal: true });
  });

  return {
    show(result) {
      zones = result.zones.features.map((feature) => feature.properties);
      scene = result.scene;
      buttons = zones.map((zone) => {
        const button = document.createElement("button");
        button.type = "button";
        button.className = "zone-item";
        button.dataset.zoneId = zone.id;
        const title = document.createElement("strong");
        title.textContent = zoneTitle(zone);
        const line = document.createElement("span");
        line.textContent = zoneLine(zone);
        button.append(title, line);
        button.addEventListener("click", () => onSelect(zone.id, { reveal: true }));
        return button;
      });
      list.replaceChildren(
        ...buttons.map((button) => {
          const item = document.createElement("li");
          item.append(button);
          return item;
        }),
      );
      this.showSelected(null);
    },

    /** Marca la zona `id` (o ninguna, con `null`) y enseña su tarjeta. */
    showSelected(id) {
      const index = zones.findIndex((zone) => zone.id === id);
      buttons.forEach((button, i) => {
        button.setAttribute("aria-pressed", String(i === index));
        // Solo un botón es tabulable: el seleccionado, o el primero si no hay ninguno.
        button.tabIndex = i === Math.max(index, 0) ? 0 : -1;
      });
      if (index === -1) {
        card.replaceChildren(hint(zones.length ? "Elige una zona para ver su tarjeta." : "No hay zonas que mostrar."));
      } else {
        card.replaceChildren(zoneCard(zones[index], scene));
      }
    },
  };
}

function hint(message) {
  const paragraph = document.createElement("p");
  paragraph.className = "hint";
  paragraph.textContent = message;
  return paragraph;
}
