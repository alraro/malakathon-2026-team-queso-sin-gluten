"""Métricas de autoconsistencia: justificar la calidad del resultado sin ground truth.

Ver docs/research/sentinel2-rgb-fire-sota.md §4.6 y §5.4. Para cada escena de ``data/``:

1. **Focos dentro de la superficie quemada**: fracción de píxeles de foco activo que caen en
   la máscara quemada y, como en §4.6, fracción con NBR < 0.
2. **Estabilidad del área**: área quemada con el umbral NBR desplazado ±0.02.
3. **Fuga de humo y nube**: fracción de la superficie quemada que cumple el test de humo
   (con el corte del motor, D > 2, y con el de §4.3, D > 1) o el de nube.
4. **Detector SWIR frente a la Wildfires**: precisión y exhaustividad de Murphy-partial
   tomando la decodificación Wildfires como referencia.
"""

from dataclasses import dataclass
from pathlib import Path

import numpy as np

from fire_engine.active_fire import detect_active_fires, murphy_partial
from fire_engine.burned_area import detect_burned_area, swir_nbr
from fire_engine.false_positives import cloud_mask, smoke_mask
from fire_engine.io import load_composite

NBR_THRESHOLD_OFFSETS = (-0.02, 0.0, 0.02)
# Corte de humo de §4.3, más laxo que el del motor: mide el humo fino que se deja pasar.
THIN_SMOKE_MIN_BRIGHTNESS_GAP = 1.0

_COMPOSITE_SUFFIXES = {"swir": "SWIR", "true_color": "True_color", "wildfires": "Wildfires"}

EMSR913_NOTE = [
    "No incluida. Los productos existen (la API de CEMS, consultada el 2026-10-15, lista",
    "9 productos y 1 AOI con centroide −6,69, 37,48), pero los JPEG de `data/` no llevan",
    "georreferencia y la escena de Huelva no tiene un bbox verificado: el perímetro solo existe",
    "en coordenadas de píxel y no se puede superponer a los vectores de EMSR913 (WGS84).",
    "Cuando la escena tenga georreferencia (#7),",
    "la comparación será de presencia y ubicación, no IoU píxel a píxel: EMSR913 se activó el",
    "2026-08-07 y la escena es del 2026-08-08.",
]


@dataclass(frozen=True)
class SceneMetrics:
    """Métricas de autoconsistencia de una escena. ``None`` = no aplicable a sus composiciones."""

    fire_source: str  # "wildfires" o "swir": de dónde salen los focos del motor
    fire_count: int  # focos activos (grupos conexos), como en el resultado del motor
    fires_in_zone: float | None  # fracción de focos con zone_id: los demás disparan el aviso
    fire_px: int
    fires_inside_burned_px: float | None  # None si no hay focos
    fires_with_negative_nbr_px: float | None
    burned_area_px: dict[float, int]  # desplazamiento del umbral NBR → área quemada
    smoke_leakage: float | None  # None sin True Color
    thin_smoke_leakage: float | None
    cloud_leakage: float | None
    swir_precision: float | None  # None sin Wildfires
    swir_recall: float | None

    @property
    def area_uncertainty(self) -> float | None:
        """Semiamplitud de la banda de área, relativa al área con el umbral del motor."""
        base = self.burned_area_px[0.0]
        if base == 0:
            return None
        areas = self.burned_area_px.values()
        return (max(areas) - min(areas)) / 2 / base


def validate_scene(
    swir: np.ndarray,
    true_color: np.ndarray | None = None,
    wildfires: np.ndarray | None = None,
) -> SceneMetrics:
    """Calcula las cuatro métricas con las mismas composiciones que recibe ``analyse_scene``."""
    burned_by_offset = {
        offset: detect_burned_area(swir, true_color, nbr_threshold_offset=offset)
        for offset in NBR_THRESHOLD_OFFSETS
    }
    burned = burned_by_offset[0.0].mask
    detected = detect_active_fires(
        swir, true_color, wildfires, zone_labels=burned_by_offset[0.0].labels
    )
    fires = detected.mask
    fire_px = int(fires.sum())
    in_zone = [f["properties"]["zone_id"] is not None for f in detected.features]

    smoke = thin_smoke = cloud = None
    if true_color is not None:
        smoke = _share(smoke_mask(swir, true_color), burned)
        thin_smoke = _share(
            smoke_mask(swir, true_color, min_brightness_gap=THIN_SMOKE_MIN_BRIGHTNESS_GAP), burned
        )
        cloud = _share(cloud_mask(swir, true_color), burned)

    precision = recall = None
    if wildfires is not None:
        reference = detect_active_fires(swir, None, wildfires).mask
        candidate = murphy_partial(swir)
        precision = _share(reference, candidate)
        recall = _share(candidate, reference)

    return SceneMetrics(
        fire_source="wildfires" if wildfires is not None else "swir",
        fire_count=len(in_zone),
        fires_in_zone=sum(in_zone) / len(in_zone) if in_zone else None,
        fire_px=fire_px,
        fires_inside_burned_px=_share(burned, fires),
        fires_with_negative_nbr_px=_share(swir_nbr(swir) < 0, fires),
        burned_area_px={offset: b.area_px for offset, b in burned_by_offset.items()},
        smoke_leakage=smoke,
        thin_smoke_leakage=thin_smoke,
        cloud_leakage=cloud,
        swir_precision=precision,
        swir_recall=recall,
    )


def validate_data(data_dir: Path) -> dict[str, SceneMetrics]:
    """Métricas de cada escena de ``data_dir`` (una subcarpeta por escena)."""
    metrics = {}
    for scene_dir in sorted(p for p in data_dir.iterdir() if p.is_dir()):
        composites = _scene_composites(scene_dir)
        if "swir" in composites:
            metrics[scene_dir.name] = validate_scene(**composites)
    return metrics


def render_report(metrics: dict[str, SceneMetrics]) -> str:
    lines = [
        "# Validación por autoconsistencia",
        "",
        "Generado con `fire-engine validate`. Sin ground truth: estas cifras comprueban que el",
        "resultado es coherente consigo mismo (ver `docs/research/sentinel2-rgb-fire-sota.md` §5.4).",
        "",
        "## 1. Focos activos dentro de la superficie quemada",
        "",
        "Focos activos (grupos conexos) que tocan una zona; los demás disparan el aviso del",
        "motor. Por píxel: fracción dentro de la superficie quemada y con NBR < 0.",
        "Referencia medida (§4.6, NBR < 0 en los focos Wildfires): 91 % Huelva, 99 % Guadalajara.",
        "",
        "| Escena | Fuente | Focos | Focos en una zona | Píxeles de foco "
        "| Píxeles en la superficie quemada | Píxeles con NBR < 0 |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for scene, m in metrics.items():
        lines.append(
            f"| {scene} | {m.fire_source} | {m.fire_count} | {_pct(m.fires_in_zone)} "
            f"| {m.fire_px} | {_pct(m.fires_inside_burned_px)} "
            f"| {_pct(m.fires_with_negative_nbr_px)} |"
        )
    lines += [
        "",
        "## 2. Estabilidad del área ante el umbral NBR (±0,02)",
        "",
        "Área quemada en píxeles con el umbral adaptativo desplazado. La banda es la semiamplitud",
        "relativa al área del motor.",
        "",
        "| Escena | Umbral −0,02 | Umbral del motor | Umbral +0,02 | Banda de incertidumbre |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for scene, m in metrics.items():
        areas = [m.burned_area_px[offset] for offset in NBR_THRESHOLD_OFFSETS]
        lines.append(
            f"| {scene} | {areas[0]} | {areas[1]} | {areas[2]} | ±{_pct(m.area_uncertainty)} |"
        )
    lines += [
        "",
        "## 3. Fuga de humo y nube en la superficie quemada",
        "",
        "Fracción de la superficie quemada que cumple el test de humo (corte del motor D > 2 y",
        "corte de §4.3 D > 1) o el de nube. Requiere True Color. El motor ya excluye D > 2 y",
        "nube, así que esas columnas solo miden lo que reintroduce la limpieza morfológica;",
        "la de D > 1 mide el humo fino que se deja pasar a propósito.",
        "",
        "| Escena | Humo (D > 2) | Humo fino (D > 1) | Nube |",
        "| --- | ---: | ---: | ---: |",
    ]
    for scene, m in metrics.items():
        lines.append(
            f"| {scene} | {_pct(m.smoke_leakage)} | {_pct(m.thin_smoke_leakage)} "
            f"| {_pct(m.cloud_leakage)} |"
        )
    lines += [
        "",
        "## 4. Detector SWIR frente a la Wildfires",
        "",
        "Precisión y exhaustividad por píxel del detector SWIR (Murphy-partial) tomando como",
        "referencia la decodificación de la Wildfires. Requiere Wildfires.",
        "",
        "| Escena | Precisión | Exhaustividad |",
        "| --- | ---: | ---: |",
    ]
    for scene, m in metrics.items():
        lines.append(f"| {scene} | {_pct(m.swir_precision)} | {_pct(m.swir_recall)} |")
    lines += ["", "## 5. Comparación con Copernicus EMS EMSR913 (Huelva)", "", *EMSR913_NOTE, ""]
    return "\n".join(lines)


def _scene_composites(scene_dir: Path) -> dict[str, np.ndarray]:
    composites = {}
    for name, suffix in _COMPOSITE_SUFFIXES.items():
        matches = sorted(scene_dir.glob(f"*_{suffix}.*"))
        if matches:
            composites[name] = load_composite(matches[0])
    return composites


def _share(mask: np.ndarray, of: np.ndarray) -> float | None:
    """Fracción de los píxeles de ``of`` que están en ``mask``."""
    total = int(of.sum())
    if total == 0:
        return None
    return int((mask & of).sum()) / total


def _pct(value: float | None) -> str:
    return "—" if value is None else f"{value:.1%}".replace(".", ",")
