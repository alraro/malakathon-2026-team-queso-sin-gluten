// Línea de estado del visor: qué escena se está viendo.
//
// Deliberadamente no resume las cifras del análisis (superficie quemada, zonas, focos,
// confianza, avisos): ese resumen, con su versión para lector de pantalla, es el ticket
// del resalte de zonas y el resumen accesible.

const COMPOSITE_LABELS = {
  swir: "SWIR",
  true_color: "True Color",
  wildfires: "Wildfires",
};

export function describeScene({ scene }) {
  const size = `${scene.width.toLocaleString("es")} × ${scene.height.toLocaleString("es")} px`;
  const composites = scene.composites.map((kind) => COMPOSITE_LABELS[kind]).join(", ");
  return `Escena de ${size}. Composiciones aportadas: ${composites}.`;
}

export const EXAMPLE_NOTICE =
  "Resultado de ejemplo del contrato: sirve para ver el visor mientras el motor " +
  "todavía no devuelve zonas ni focos.";
