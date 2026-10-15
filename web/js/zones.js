// Pestaña Zonas: la lista de zonas del resultado, de mayor a menor, con la seleccionada
// desplegada en acordeón.
//
// La lista es un único control (listbox): Tab entra en ella, las flechas (e Inicio/Fin)
// mueven el cursor, Enter selecciona la zona del cursor y Escape quita la selección.
// Elegir una zona avisa a `onSelect`, que la resalta también en el visor.

import { factRow, text } from "./card.js";
import { fireCount, formatArea, formatShare, zoneFields, zoneSeverity, zoneTitle } from "./describe.js";

const STEPS = { ArrowDown: 1, ArrowUp: -1 };

export function createZonePanel({ panel, onSelect }) {
  let zones = [];
  let scene = null;
  let selected = null;
  let cursor = -1;
  const list = text("div", "", "zone-listbox");
  list.setAttribute("role", "listbox");
  list.tabIndex = 0;
  list.setAttribute("aria-label", "Zonas quemadas");

  list.addEventListener("keydown", (event) => {
    if (zones.length === 0) return;
    if (event.key in STEPS) cursor = Math.min(zones.length - 1, Math.max(0, cursor + STEPS[event.key]));
    else if (event.key === "Home") cursor = 0;
    else if (event.key === "End") cursor = zones.length - 1;
    else if (event.key === "Enter" && cursor >= 0) {
      event.preventDefault();
      onSelect(zones[cursor].id, { reveal: true });
      return;
    } else if (event.key === "Escape") {
      event.preventDefault();
      onSelect(null);
      return;
    } else return;
    event.preventDefault();
    render();
  });

  list.addEventListener("click", (event) => {
    // Los ⓘ del detalle no pliegan la zona.
    if (event.target.closest(".zdetail")) return;
    const row = event.target.closest("[data-zone-id]");
    if (!row) return;
    const id = Number(row.dataset.zoneId);
    cursor = zones.findIndex((zone) => zone.id === id);
    onSelect(id === selected ? null : id, { reveal: true });
  });

  function detail(zone) {
    const box = text("div", "", "zdetail");
    const grid = text("div", "", "zgrid");
    grid.append(...zoneFields(zone, scene).map((fact) => factRow(fact, "zfield")));

    const severity = zoneSeverity(zone);
    const sev = text("div", "", "sev");
    const bar = text("div", "", "sev__bar");
    bar.setAttribute("role", "img");
    bar.setAttribute("aria-label", `Severidad relativa: ${severity.labels.join(", ")}`);
    const affected = text("div", "", "sev__a");
    affected.style.width = `${severity.affected * 100}%`;
    const severe = text("div", "", "sev__m");
    severe.style.width = `${severity.severelyAffected * 100}%`;
    bar.append(affected, severe);
    const labels = text("div", "", "sev__labels");
    labels.append(...severity.labels.map((label) => text("span", label)));
    sev.append(text("div", "Severidad relativa", "float__label"), bar, labels, text("small", severity.note));

    box.append(grid, sev);
    return box;
  }

  function render() {
    list.replaceChildren(
      ...zones.map((zone, index) => {
        const on = zone.id === selected;
        const row = text("div", "", `zrow${on ? " is-selected" : ""}${index === cursor && !on ? " is-kb" : ""}`);
        row.id = `zone-option-${zone.id}`;
        row.dataset.zoneId = zone.id;
        row.setAttribute("role", "option");
        row.setAttribute("aria-selected", String(on));
        const head = text("div", "", "zrow__head");
        head.append(text("b", zoneTitle(zone)), text("span", formatArea(zone.area_px, zone.area_ha)));
        row.append(
          head,
          text("div", `${formatShare(zone.share_of_burned)} del total · ${fireCount(zone.active_fire_count)}`, "zrow__sub"),
        );
        if (on) row.append(detail(zone));
        return row;
      }),
    );
    const active = zones[cursor];
    if (active) {
      list.setAttribute("aria-activedescendant", `zone-option-${active.id}`);
      document.getElementById(`zone-option-${active.id}`).scrollIntoView({ block: "nearest" });
    } else {
      list.removeAttribute("aria-activedescendant");
    }
  }

  return {
    show(result) {
      zones = result.zones.features
        .map((feature) => feature.properties)
        .sort((a, b) => b.area_px - a.area_px);
      scene = result.scene;
      selected = null;
      cursor = -1;
      if (zones.length === 0) {
        panel.replaceChildren(text("div", "No se ha detectado superficie quemada en esta escena.", "empty"));
        return;
      }
      render();
      panel.replaceChildren(list);
    },

    /** Despliega la zona `id` (o ninguna, con `null`). */
    showSelected(id) {
      selected = id;
      if (id !== null) cursor = zones.findIndex((zone) => zone.id === id);
      if (zones.length > 0) render();
    },
  };
}
