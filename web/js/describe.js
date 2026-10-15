// Textos del resultado para personas: tarjeta de zona, resumen global y su versión para
// lector de pantalla. Nada de esto sabe de Leaflet ni del DOM.
//
// Cada cifra es un «dato» `{label, value, note, unavailable}`: `value` lleva la unidad y
// `note` el supuesto del que depende. Lo que el resultado no trae (sin georreferencia
// no hay hectáreas ni poblaciones) sale como «no disponible» con la forma de obtenerlo;
// nunca se rellena con una cifra inventada.

const UNAVAILABLE = "no disponible";
const HOW_TO_GEOREFERENCE =
  "Georreferencia la escena (las coordenadas de sus esquinas) y vuelve a analizarla para obtener el dato.";

const CONFIDENCE_LABELS = { high: "alta", low: "baja" };

/** Zonas que el resumen para lector de pantalla describe una a una. */
const SPOKEN_ZONES = 3;

/** Por qué la confianza es la que es, en lenguaje llano y con cómo mejorarla. */
const CONFIDENCE_REASONS = {
  burned_area: {
    high: "Se aportó la True Color, que permite descartar el humo y las nubes que la SWIR sola confundiría con quemado.",
    low: "Solo se ha usado la SWIR: algo de humo o de nube podría haberse contado como quemado. Añade la True Color para mejorarla.",
  },
  active_fire: {
    high: "Los focos salen de la composición Wildfires, que trae el fuego ya clasificado por niveles.",
    low: "Sin la composición Wildfires, los focos se estiman desde la SWIR y puede faltar o sobrar alguno. Añade la Wildfires para mejorarla.",
  },
};

export function formatNumber(value, decimals = 0) {
  return value.toLocaleString("es", {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  });
}

/** Fracción 0–1 como porcentaje entero; lo que no llega al 1 % no se redondea a cero. */
export function formatShare(fraction) {
  if (fraction > 0 && fraction < 0.01) return "menos del 1 %";
  return `${formatNumber(Math.round(fraction * 100))} %`;
}

function plural(count, singular, pluralForm) {
  return `${formatNumber(count)} ${count === 1 ? singular : pluralForm}`;
}

const fireCount = (count) =>
  count === 0 ? "ningún foco activo" : plural(count, "foco activo", "focos activos");
const zoneCount = (count) => plural(count, "zona quemada", "zonas quemadas");

function unavailable(label, note) {
  return { label, value: UNAVAILABLE, note, unavailable: true };
}

function scaleNote({ metres_per_pixel: metresPerPixel }) {
  return metresPerPixel
    ? `Calculado a ${formatNumber(metresPerPixel, 1)} m por píxel, según la georreferencia.`
    : "Calculado con la georreferencia de la escena.";
}

/** Área en hectáreas si hay georreferencia; si no, en píxeles y diciendo por qué. */
function areaFact(label, areaPx, areaHa, scene, meaning) {
  if (areaHa != null) {
    return {
      label,
      value: `${formatNumber(areaHa, 1)} ha`,
      note: `${meaning} ${scaleNote(scene)}`,
    };
  }
  return {
    label,
    value: `${formatNumber(areaPx)} px`,
    note: `${meaning} En píxeles de la imagen: las hectáreas no están disponibles. ${HOW_TO_GEOREFERENCE}`,
  };
}

function settlementFact(settlement, scene) {
  const label = "Población más cercana";
  if (settlement) {
    return {
      label,
      value: `${settlement.name}, a ${formatNumber(settlement.distance_km, 1)} km`,
      note: "Distancia en línea recta desde la zona, según la georreferencia.",
    };
  }
  if (!scene.georeference) {
    return unavailable(label, `Sin georreferencia no se sabe dónde está la escena. ${HOW_TO_GEOREFERENCE}`);
  }
  return unavailable(label, "El análisis no ha encontrado ninguna población cercana en el dataset local.");
}

/** Título corto de una zona, para listas y tarjetas. */
export function zoneTitle({ id }) {
  return `Zona ${id}`;
}

/** Resumen de una línea de una zona, para la lista del panel. */
export function zoneLine(zone) {
  const area = zone.area_ha != null ? `${formatNumber(zone.area_ha, 1)} ha` : `${formatNumber(zone.area_px)} px`;
  return `${area} · ${formatShare(zone.share_of_burned)} del total quemado · ${fireCount(zone.active_fire_count)}`;
}

/** Datos de la tarjeta de una zona (`zone` son las `properties` del contrato). */
export function describeZone(zone, scene) {
  const { affected, severely_affected: severelyAffected } = zone.relative_severity;
  return [
    areaFact("Área", zone.area_px, zone.area_ha, scene, "Píxeles quemados de la zona."),
    {
      label: "Parte del total quemado",
      value: formatShare(zone.share_of_burned),
      note: "Qué parte de toda la superficie quemada de la escena cae en esta zona.",
    },
    {
      label: "Focos activos",
      value: fireCount(zone.active_fire_count),
      note: "Fuego ardiendo dentro de la zona en el momento de la imagen.",
    },
    {
      label: "Severidad relativa a la escena",
      value: `${formatShare(affected)} afectado · ${formatShare(severelyAffected)} muy afectado`,
      note: "Compara las zonas de esta imagen entre sí, no con otros incendios.",
    },
    settlementFact(zone.nearest_settlement, scene),
  ];
}

function fireSources(features) {
  const estimated = features.filter((fire) => fire.properties.source === "swir").length;
  const decoded = features.length - estimated;
  if (estimated === 0) return "Todos salen de la composición Wildfires.";
  if (decoded === 0) return "Todos estimados desde la SWIR.";
  const swir = estimated === 1 ? "estimado" : "estimados";
  return `${formatNumber(decoded)} de la composición Wildfires y ${formatNumber(estimated)} ${swir} desde la SWIR (confianza baja).`;
}

function enclosedFact({ summary }) {
  const label = "Dentro del perímetro frente a quemado";
  if (summary.perimeter_enclosed_ha == null || summary.burned_area_ha == null) {
    return unavailable(label, `Necesita las hectáreas. ${HOW_TO_GEOREFERENCE}`);
  }
  return {
    label,
    value: `${formatNumber(summary.perimeter_enclosed_ha, 1)} ha frente a ${formatNumber(summary.burned_area_ha, 1)} ha`,
    note: "La diferencia son islas sin quemar que quedan dentro del perímetro.",
  };
}

function perimeterFact({ summary }) {
  const label = "Longitud del perímetro";
  if (summary.perimeter_km == null) {
    return unavailable(label, `Necesita la escala del terreno. ${HOW_TO_GEOREFERENCE}`);
  }
  const tolerance =
    summary.perimeter_tolerance_m == null
      ? "Contorno simplificado; la tolerancia usada no consta, así que tómala como aproximada."
      : `Contorno simplificado con una tolerancia de ${formatNumber(summary.perimeter_tolerance_m)} m: con otra tolerancia, la longitud cambia.`;
  return { label, value: `${formatNumber(summary.perimeter_km, 1)} km`, note: tolerance };
}

function confidenceFact(label, kind, level) {
  return { label, value: CONFIDENCE_LABELS[level], note: CONFIDENCE_REASONS[kind][level] };
}

/** Datos del resumen global de la escena. */
export function describeSummary(result) {
  const { summary, scene } = result;
  return [
    areaFact(
      "Superficie quemada",
      summary.burned_area_px,
      summary.burned_area_ha,
      scene,
      "Píxeles con evidencia de haber ardido; las islas sin quemar no cuentan.",
    ),
    {
      label: "Zonas",
      value: zoneCount(summary.zone_count),
      note: "Manchas de superficie quemada de al menos unas 30 ha; las más pequeñas no se cuentan como zona.",
    },
    {
      label: "Focos activos",
      value: fireCount(summary.active_fire_count),
      note: summary.active_fire_count > 0 ? fireSources(result.active_fires.features) : "No se ha visto fuego ardiendo en la imagen.",
    },
    enclosedFact(result),
    perimeterFact(result),
    confidenceFact("Confianza en la superficie quemada", "burned_area", summary.confidence.burned_area),
    confidenceFact("Confianza en los focos activos", "active_fire", summary.confidence.active_fire),
  ];
}

/** Párrafo que resume el resultado para quien no ve la imagen (lector de pantalla). */
export function screenReaderSummary(result) {
  const { summary } = result;
  const zones = result.zones.features.map((feature) => feature.properties);
  const sentences = [];

  const burned =
    summary.burned_area_ha != null
      ? `unas ${formatNumber(summary.burned_area_ha)} ha quemadas en total`
      : `${formatNumber(summary.burned_area_px)} píxeles quemados en total (sin georreferencia no hay hectáreas)`;
  sentences.push(
    summary.zone_count === 0
      ? `No se ha detectado ninguna zona quemada, y ${fireCount(summary.active_fire_count)}.`
      : `Se han detectado ${zoneCount(summary.zone_count)}, ${burned}, y ${fireCount(summary.active_fire_count)}.`,
  );

  // Solo las zonas más grandes, con detalle: con decenas de zonas el párrafo sería inescuchable.
  const largest = [...zones].sort((a, b) => b.share_of_burned - a.share_of_burned);
  for (const zone of largest.slice(0, SPOKEN_ZONES)) {
    const settlement = zone.nearest_settlement
      ? `; población más cercana: ${zone.nearest_settlement.name}, a ${formatNumber(zone.nearest_settlement.distance_km, 1)} km`
      : "";
    sentences.push(
      `${zoneTitle(zone)}: ${formatShare(zone.share_of_burned)} del total quemado, ${fireCount(zone.active_fire_count)}${settlement}.`,
    );
  }
  const rest = largest.slice(SPOKEN_ZONES);
  if (rest.length > 0) {
    const restShare = rest.reduce((total, zone) => total + zone.share_of_burned, 0);
    const restFires = rest.reduce((total, zone) => total + zone.active_fire_count, 0);
    const others = rest.length === 1 ? "La zona restante suma" : `Las ${formatNumber(rest.length)} zonas restantes suman`;
    sentences.push(
      `${others} ${formatShare(restShare)} del total quemado y ${fireCount(restFires)}; el detalle está en el panel de zonas.`,
    );
  }

  const { burned_area: burnedConfidence, active_fire: fireConfidence } = summary.confidence;
  sentences.push(
    `Confianza ${CONFIDENCE_LABELS[burnedConfidence]} en la superficie quemada y ${CONFIDENCE_LABELS[fireConfidence]} en los focos activos.`,
  );
  for (const warning of summary.warnings) sentences.push(`Aviso: ${warning}`);
  return sentences.join(" ");
}
