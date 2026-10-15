// Lista de poblaciones cercanas; la clasificación depende solo de distancia.

const LEVELS = { high: "Alta", medium: "Media", watch: "Vigilancia" };
const SOURCES = { active_fire: "foco activo", burned_area: "superficie quemada" };
const number = new Intl.NumberFormat("es-ES", { maximumFractionDigits: 1 });

export function createAlertPanel({ root, list, note }) {
  return {
    show(result) {
      root.hidden = false;
      list.replaceChildren();
      if (!result.scene.georeference) {
        note.textContent = "Sin bbox no se pueden localizar poblaciones. Añade las coordenadas del encuadre y vuelve a analizar la escena.";
        return;
      }
      if (result.alerts.length === 0) {
        note.textContent = "No hay poblaciones del dataset dentro de los umbrales de alerta configurados alrededor de la superficie quemada o de los focos activos.";
        return;
      }
      note.textContent = "Alertas calculadas solo por distancia desde puntos de referencia de GeoNames. No indican la dirección del humo ni predicen la propagación.";
      for (const alert of result.alerts) {
        const item = document.createElement("li");
        item.className = `alert-item alert-${alert.level}`;
        const title = document.createElement("strong");
        title.textContent = alert.settlement;
        const level = document.createElement("span");
        level.className = "alert-level";
        level.textContent = `Alerta ${LEVELS[alert.level]}`;
        const detail = document.createElement("span");
        const population = alert.population > 0
          ? `${number.format(alert.population)} habitantes`
          : "Habitantes sin dato en GeoNames";
        detail.textContent = `${population} · ${number.format(alert.distance_km)} km de ${SOURCES[alert.nearest_to]}`;
        item.append(title, level, detail);
        list.append(item);
      }
    },
  };
}
