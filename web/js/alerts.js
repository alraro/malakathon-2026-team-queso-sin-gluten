// Pestaña Poblaciones: poblaciones cercanas por distancia, con su alerta. La alerta se
// calcula solo por distancia; la insignia lleva color y forma, nunca solo color.

import { text } from "./card.js";
import { formatNumber } from "./describe.js";

const LEVELS = {
  high: { tag: "alta", label: "◆ Alta" },
  medium: { tag: "media", label: "■ Media" },
  watch: { tag: "vigilancia", label: "○ Vigilancia" },
};
const SOURCES = { active_fire: "un foco activo", burned_area: "la superficie quemada" };
const CRITERIA =
  "Alta: dentro del perímetro o a menos de 2 km de un foco · Media: menos de 5 km · " +
  "Vigilancia: menos de 10 km. Solo por distancia: no modela humo ni propagación. " +
  "Poblaciones: GeoNames, CC BY 4.0.";

export function createAlertPanel({ panel }) {
  return {
    show(result) {
      const alerts = [...result.alerts].sort((a, b) => a.distance_km - b.distance_km);
      const rows = alerts.map((alert) => {
        const row = text("div", "", "prow");
        const head = text("div", "", "prow__head");
        const level = LEVELS[alert.level];
        head.append(text("b", alert.settlement), text("span", level.label, `tag tag--${level.tag}`));
        const population =
          alert.population > 0 ? `${formatNumber(alert.population)} habitantes` : "Habitantes: sin dato en GeoNames";
        row.append(
          head,
          text("div", population, "prow__hab"),
          text("div", `${formatNumber(alert.distance_km, 1)} km de ${SOURCES[alert.nearest_to]}`, "prow__dist num"),
        );
        return row;
      });
      const empty = alerts.length
        ? []
        : [text("div", "No hay poblaciones del conjunto de datos dentro de los umbrales de alerta.", "empty")];
      panel.replaceChildren(...empty, ...rows, text("div", CRITERIA, "criteria"));
    },
  };
}
