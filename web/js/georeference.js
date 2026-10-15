// Coordenadas opcionales del encuadre: son aportadas por la persona, nunca del JPEG.

export function readBbox(form) {
  const names = ["west", "south", "east", "north"];
  const raw = Object.fromEntries(names.map((name) => [name, form.elements[name].value.trim()]));
  if (names.every((name) => raw[name] === "")) return null;
  if (names.some((name) => raw[name] === "")) {
    throw new Error("El bbox necesita norte, sur, este y oeste.");
  }
  const bbox = Object.fromEntries(names.map((name) => [name, Number(raw[name])]));
  if (
    Object.values(bbox).some((value) => !Number.isFinite(value)) ||
    bbox.west < -180 || bbox.east > 180 || bbox.west >= bbox.east ||
    bbox.south <= -85.05112878 || bbox.north >= 85.05112878 || bbox.south >= bbox.north
  ) {
    throw new Error("El bbox debe tener oeste < este y sur < norte dentro de Web Mercator.");
  }
  return bbox;
}
