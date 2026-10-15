// Formulario «Nueva escena»: tarjetas de composición con arrastrar y soltar, sección
// Ubicación con sus dos pestañas y errores. El progreso lo pinta la pantalla «Análisis en
// curso» (progress.js).

import { formatNumber } from "./describe.js";
import { checkBbox } from "./georeference.js";

const COMPOSITES = ["swir", "true_color", "wildfires"];
const COORDS = ["north", "south", "east", "west"];
const MISSING_SWIR = "Falta la composición SWIR: es la única obligatoria.";

const megabytes = (bytes) => `${formatNumber(bytes / (1024 * 1024), 1)} MB`;

/**
 * @param {{form: HTMLFormElement, error: HTMLElement,
 *   onAnalyse: (composites: object, bbox: object|null) => Promise<void>}} options
 *   `onAnalyse` recibe las composiciones por tarjeta más, como mucho, una ubicación: el
 *   GeoTIFF (`composites.geotiff`) o el `bbox`, según la pestaña activa, y ninguna si la
 *   sección está plegada. Si rechaza, su mensaje sale encima del botón.
 */
export function createUploadForm({ form, error, onAnalyse }) {
  const $ = (selector) => form.querySelector(selector);
  const button = $("#analyse-button");
  const hint = $("#analyse-hint");
  const cards = Object.fromEntries(COMPOSITES.map((kind) => [kind, createCard(kind)]));

  const location = {
    toggle: $("#loc-toggle"),
    body: $("#loc-body"),
    tabs: [...form.querySelectorAll("[data-loc-tab]")],
    geotiff: $("#field-geotiff"),
    geotiffName: $("#geotiff-name"),
    geotiffRemove: $("#geotiff-remove"),
    coordError: $("#coord-error"),
    open: false,
    tab: "geotiff",
    // Un recuadro a medio escribir solo se marca tras intentar analizar con él.
    triedCoords: false,
  };
  const coordInputs = Object.fromEntries(COORDS.map((name) => [name, form.elements[name]]));

  function showError(message) {
    error.querySelector("span").textContent = message;
    error.hidden = !message;
  }

  /** Una tarjeta: la composición la da la tarjeta, nunca el nombre del archivo. */
  function createCard(kind) {
    const wrap = form.querySelector(`[data-composite="${kind}"]`);
    const card = wrap.querySelector(".card");
    const input = wrap.querySelector(".card__input");
    const drop = wrap.querySelector(".card__drop");
    const loaded = wrap.querySelector(".card__file");
    const thumb = wrap.querySelector(".card__thumb");
    const fieldError = wrap.querySelector(".field-error");
    const state = { file: null, url: null, pending: 0 };

    function paint() {
      drop.hidden = Boolean(state.file);
      loaded.hidden = !state.file;
      if (state.file) {
        thumb.src = state.url;
        wrap.querySelector(".card__name").textContent = state.file.name;
        wrap.querySelector(".card__name").title = state.file.name;
        wrap.querySelector(".card__size").textContent = megabytes(state.file.size);
      } else {
        thumb.removeAttribute("src");
      }
      card.setAttribute(
        "aria-label",
        `${card.querySelector(".card__title").textContent}: ${
          state.file ? `${state.file.name} cargado; pulsa para cambiarlo` : "elige o arrastra el JPEG"
        }`,
      );
    }

    function setError(message) {
      fieldError.querySelector("span").textContent = message;
      fieldError.hidden = !message;
      card.classList.toggle("card--err", Boolean(message));
    }

    function clear() {
      state.pending += 1;
      if (state.url) URL.revokeObjectURL(state.url);
      state.file = null;
      state.url = null;
      setError("");
      paint();
    }

    /** Se queda con `file` solo si el navegador lo sabe pintar; si no, conserva el anterior. */
    async function accept(file) {
      if (!file) return;
      const attempt = (state.pending += 1);
      const url = URL.createObjectURL(file);
      let valid = file.type.startsWith("image/");
      if (valid) {
        const probe = new Image();
        probe.src = url;
        valid = await probe.decode().then(() => true, () => false);
      }
      if (attempt !== state.pending) {
        URL.revokeObjectURL(url);
        return;
      }
      if (!valid) {
        URL.revokeObjectURL(url);
        setError("No es una imagen válida.");
        return;
      }
      if (state.url) URL.revokeObjectURL(state.url);
      Object.assign(state, { file, url });
      setError("");
      paint();
      refresh();
    }

    card.addEventListener("click", (event) => {
      if (!event.target.closest(".card__remove")) input.click();
    });
    card.addEventListener("keydown", (event) => {
      if (event.target !== card || (event.key !== "Enter" && event.key !== " ")) return;
      event.preventDefault();
      input.click();
    });
    input.addEventListener("change", () => {
      accept(input.files[0]);
      // Para que volver a elegir el mismo archivo tras «Quitar» también avise.
      input.value = "";
    });
    wrap.querySelector(".card__remove").addEventListener("click", () => {
      clear();
      refresh();
      card.focus();
    });

    card.addEventListener("dragenter", (event) => {
      event.preventDefault();
      card.classList.add("is-drag");
    });
    card.addEventListener("dragover", (event) => {
      event.preventDefault();
      event.dataTransfer.dropEffect = "copy";
    });
    card.addEventListener("dragleave", (event) => {
      if (!card.contains(event.relatedTarget)) card.classList.remove("is-drag");
    });
    card.addEventListener("drop", (event) => {
      event.preventDefault();
      card.classList.remove("is-drag");
      accept(event.dataTransfer.files[0]);
    });

    paint();
    return { state, clear, focus: () => card.focus() };
  }

  // Soltar un archivo fuera de las tarjetas no debe abrirlo en la pestaña y perder la escena.
  for (const type of ["dragover", "drop"]) {
    window.addEventListener(type, (event) => {
      if (event.dataTransfer?.types.includes("Files")) event.preventDefault();
    });
  }

  // ----- Ubicación -----

  function setOpen(open) {
    location.open = open;
    location.toggle.setAttribute("aria-expanded", String(open));
    location.toggle.lastElementChild.textContent = open ? "▾" : "▸";
    location.body.hidden = !open;
    refresh();
  }

  function setTab(tab, { focus = false } = {}) {
    location.tab = tab;
    for (const button of location.tabs) {
      const active = button.dataset.locTab === tab;
      button.setAttribute("aria-selected", String(active));
      button.tabIndex = active ? 0 : -1;
      document.getElementById(button.getAttribute("aria-controls")).hidden = !active;
      if (active && focus) button.focus();
    }
    refresh();
  }

  location.toggle.addEventListener("click", () => setOpen(!location.open));
  for (const tab of location.tabs) {
    tab.addEventListener("click", () => setTab(tab.dataset.locTab));
    tab.addEventListener("keydown", (event) => {
      if (event.key !== "ArrowLeft" && event.key !== "ArrowRight") return;
      event.preventDefault();
      const other = location.tabs.find((button) => button !== tab);
      setTab(other.dataset.locTab, { focus: true });
    });
  }

  function paintGeotiff() {
    const file = location.geotiff.files[0];
    location.geotiffName.textContent = file
      ? `${file.name} · ${megabytes(file.size)}`
      : "Ningún archivo seleccionado";
    location.geotiffRemove.hidden = !file;
  }
  $("#geotiff-pick").addEventListener("click", () => location.geotiff.click());
  location.geotiff.addEventListener("change", paintGeotiff);
  location.geotiffRemove.addEventListener("click", () => {
    location.geotiff.value = "";
    paintGeotiff();
    $("#geotiff-pick").focus();
  });

  const coords = () =>
    checkBbox(Object.fromEntries(COORDS.map((name) => [name, coordInputs[name].value])));

  function paintCoords(check) {
    const shown = check.incomplete && !location.triedCoords ? null : check;
    for (const name of COORDS) {
      const bad = Boolean(shown?.bad.includes(name));
      coordInputs[name].classList.toggle("is-bad", bad);
      coordInputs[name].toggleAttribute("aria-invalid", bad);
    }
    location.coordError.querySelector("span").textContent = shown?.error ?? "";
    location.coordError.hidden = !shown?.error;
  }
  for (const input of Object.values(coordInputs)) input.addEventListener("input", refresh);

  const usingCoords = () => location.open && location.tab === "coords";

  /** Repinta lo que depende de varios campos: errores de coordenadas y el botón. */
  function refresh() {
    const check = coords();
    paintCoords(check);
    const badCoords = usingCoords() && check.error && !check.incomplete;
    button.disabled = !cards.swir.state.file || Boolean(badCoords);
    hint.textContent = !cards.swir.state.file
      ? MISSING_SWIR
      : badCoords ? "Corrige las coordenadas para analizar." : "";
    hint.hidden = !hint.textContent;
  }

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    showError("");
    if (!cards.swir.state.file) {
      showError(MISSING_SWIR);
      cards.swir.focus();
      return;
    }
    let bbox = null;
    if (usingCoords()) {
      location.triedCoords = true;
      const check = coords();
      paintCoords(check);
      if (check.error) {
        coordInputs[check.bad[0]].focus();
        return;
      }
      bbox = check.bbox;
    }
    const composites = Object.fromEntries(
      COMPOSITES.map((kind) => [kind, cards[kind].state.file]),
    );
    composites.geotiff =
      location.open && location.tab === "geotiff" ? location.geotiff.files[0] ?? null : null;

    try {
      await onAnalyse(composites, bbox);
    } catch (failure) {
      showError(failure.message);
    }
  });

  refresh();

  return {
    showError,
    /** Deja el formulario vacío para una escena nueva. */
    reset() {
      for (const card of Object.values(cards)) card.clear();
      form.reset();
      paintGeotiff();
      location.triedCoords = false;
      setTab("geotiff");
      setOpen(false);
      showError("");
    },
  };
}
