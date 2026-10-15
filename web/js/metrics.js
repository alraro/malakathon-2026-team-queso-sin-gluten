// Resumen y tarjetas: las unidades métricas solo aparecen con georreferencia.

const number = new Intl.NumberFormat("es-ES", { maximumFractionDigits: 1 });

export function renderMetrics(summaryRoot, zonesRoot, result) {
  const { scene, summary } = result;
  const assumption = scene.georeference?.source === "manual"
    ? "Calculado con el bbox aportado por el usuario."
    : "Calculado con la georreferencia de la escena.";

  summaryRoot.replaceChildren();
  zonesRoot.replaceChildren();
  const heading = document.createElement("h3");
  heading.textContent = "Resumen";
  summaryRoot.append(heading);

  if (scene.georeference) {
    summaryRoot.append(
      metric("Superficie quemada", `${number.format(summary.burned_area_ha)} ha`, assumption),
      metric("Área dentro del perímetro", `${number.format(summary.perimeter_enclosed_ha)} ha`, assumption),
      metric("Longitud del perímetro", `${number.format(summary.perimeter_km)} km`,
        `${assumption} Tolerancia de simplificación aproximada: ${number.format(summary.perimeter_tolerance_m)} m.`),
    );
  } else {
    summaryRoot.append(metric(
      "Superficie quemada", `${number.format(summary.burned_area_px)} px`,
      "Hectáreas y kilómetros no disponibles: añade un bbox del encuadre para calcularlos.",
    ));
  }
  summaryRoot.append(metric("Zonas", String(summary.zone_count)));
  summaryRoot.append(metric("Focos activos", String(summary.active_fire_count)));

  const zonesHeading = document.createElement("h3");
  zonesHeading.textContent = "Zonas";
  zonesRoot.append(zonesHeading);
  if (result.zones.features.length === 0) {
    const empty = document.createElement("p");
    empty.textContent = "No se han detectado zonas de superficie quemada.";
    zonesRoot.append(empty);
  }
  for (const zone of result.zones.features) {
    const { id, area_px, area_ha } = zone.properties;
    zonesRoot.append(metric(
      `Zona ${id}`,
      scene.georeference ? `${number.format(area_ha)} ha` : `${number.format(area_px)} px`,
      scene.georeference ? assumption : "Hectáreas no disponibles sin bbox.",
    ));
  }
}

function metric(label, value, note = "") {
  const card = document.createElement("div");
  card.className = "metric-card";
  const title = document.createElement("strong");
  title.textContent = label;
  const amount = document.createElement("span");
  amount.textContent = value;
  card.append(title, amount);
  if (note) {
    const hint = document.createElement("small");
    hint.textContent = note;
    card.append(hint);
  }
  return card;
}
