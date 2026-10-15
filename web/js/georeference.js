// Coordenadas opcionales del encuadre: son aportadas por la persona, nunca del JPEG.

const NAMES = ["north", "south", "east", "west"];
// Web Mercator no llega a los polos: el motor rechaza latitudes fuera de ±85,05°.
const MAX_LATITUDE = 85.05112878;

/**
 * Comprueba lo escrito en los campos Norte, Sur, Este y Oeste.
 *
 * @param {{north: string, south: string, east: string, west: string}} raw el texto de
 *   cada campo; se admite coma decimal.
 * @returns {{bbox: {west, south, east, north}|null, error: string, bad: string[],
 *   incomplete: boolean}} `bbox` es `null` si no hay nada escrito o hay error; `bad`
 *   nombra los campos que hay que marcar. Un recuadro a medio escribir solo es
 *   `incomplete`: no se marca mientras se escribe, pero no se puede enviar.
 */
export function checkBbox(raw) {
  const text = Object.fromEntries(NAMES.map((name) => [name, (raw[name] ?? "").trim()]));
  const fail = (error, bad, incomplete = false) => ({ bbox: null, error, bad, incomplete });

  // Un signo o una coma sueltos son un número a medio escribir, no un error.
  const empty = NAMES.filter((name) => /^[-+]?[.,]?$/.test(text[name]));
  if (NAMES.every((name) => text[name] === "")) return { bbox: null, error: "", bad: [], incomplete: false };

  const value = Object.fromEntries(
    NAMES.map((name) => [name, /^[-+]?(\d+([.,]\d*)?|[.,]\d+)$/.test(text[name])
      ? Number(text[name].replace(",", "."))
      : NaN]),
  );
  const written = NAMES.filter((name) => !empty.includes(name));
  const notNumbers = written.filter((name) => !Number.isFinite(value[name]));
  if (notNumbers.length) {
    return fail("Las coordenadas tienen que ser números en grados decimales.", notNumbers);
  }
  const outOfRange = written.filter((name) => (
    name === "north" || name === "south"
      ? Math.abs(value[name]) >= MAX_LATITUDE
      : Math.abs(value[name]) > 180
  ));
  if (outOfRange.length) {
    return fail(
      "Coordenadas fuera de rango: la latitud va de −85 a 85 y la longitud de −180 a 180.",
      outOfRange,
    );
  }
  // Se avisa de la incoherencia en cuanto están los dos campos de un eje, aunque falten otros.
  const both = (a, b) => written.includes(a) && written.includes(b);
  if (both("north", "south") && value.north <= value.south) {
    return fail("Coordenadas incoherentes: el norte tiene que ser mayor que el sur.", ["north", "south"]);
  }
  if (both("east", "west") && value.east <= value.west) {
    return fail("Coordenadas incoherentes: el este tiene que ser mayor que el oeste.", ["east", "west"]);
  }
  if (empty.length) {
    return fail("Faltan coordenadas: hacen falta norte, sur, este y oeste.", empty, true);
  }
  const { west, south, east, north } = value;
  return { bbox: { west, south, east, north }, error: "", bad: [], incomplete: false };
}
