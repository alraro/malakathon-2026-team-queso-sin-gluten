// Formulario de subida: las tres casillas, el progreso y los mensajes de error.

export function createUploadForm({
  form,
  button,
  progress,
  progressBar,
  progressText,
  error,
  onAnalyse,
}) {
  const fields = {
    swir: form.elements.swir,
    true_color: form.elements.true_color,
    wildfires: form.elements.wildfires,
  };

  function showError(message) {
    error.textContent = message;
    error.hidden = !message;
  }

  function showProgress(update) {
    progress.hidden = false;
    if (update.phase === "upload") {
      const percent = Math.round(update.ratio * 100);
      progressBar.style.width = `${percent}%`;
      progressText.textContent = `Subiendo composiciones… ${percent} %`;
    } else {
      progressBar.style.width = "100%";
      progressText.textContent = "Analizando la escena… puede tardar en imágenes grandes.";
    }
  }

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    showError("");

    const composites = Object.fromEntries(
      Object.entries(fields).map(([field, input]) => [field, input.files[0] ?? null]),
    );
    if (!composites.swir) {
      showError("Falta la composición SWIR: es la única obligatoria.");
      fields.swir.focus();
      return;
    }

    button.disabled = true;
    showProgress({ phase: "upload", ratio: 0 });
    try {
      await onAnalyse(composites, showProgress);
    } catch (failure) {
      showError(failure.message);
    } finally {
      progress.hidden = true;
      progressBar.style.width = "0%";
      button.disabled = false;
    }
  });

  return { showError };
}
