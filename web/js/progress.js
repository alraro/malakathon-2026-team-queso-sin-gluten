// Pantalla «Análisis en curso»: progreso real de la subida y, después, barra
// indeterminada, porque el motor no informa de su avance. Nada de pasos inventados.

export function createProgress({ text, percent, bar, note }) {
  return {
    /** `update` es lo que da `analyseScene`: `{phase: "upload", ratio}` o `{phase: "analysis"}`. */
    show(update) {
      if (update.phase === "upload") {
        const value = Math.round(update.ratio * 100);
        text.textContent = "Subiendo composiciones…";
        percent.textContent = `${value} %`;
        bar.className = "bar__fill";
        bar.style.width = `${value}%`;
        note.hidden = true;
      } else {
        text.textContent = "Analizando la escena…";
        percent.textContent = "";
        bar.className = "bar__slide";
        bar.style.width = "";
        note.hidden = false;
      }
    },
  };
}
