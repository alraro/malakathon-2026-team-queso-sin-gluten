import numpy as np
from PIL import Image

from fire_engine.cli import main
from fire_engine.validation import validate_scene

PREFIX = "2026-08-08-00_00_2026-08-08-23_59_Sentinel-2_L2A"


def synthetic_scene():
    """Cicatriz con un foco dentro y otro fuera; la Wildfires marca solo el de dentro."""
    swir = np.zeros((120, 160, 3), dtype=np.uint8)
    swir[...] = (60, 150, 40)
    swir[20:60, 20:60] = (90, 40, 70)  # cicatriz con B12 < 0.15: el detector SWIR no crece en ella
    true_color = swir.copy()  # mismo brillo relativo: ni humo ni nube
    swir[38:41, 38:41] = (255, 90, 60)
    swir[90:93, 120:123] = (255, 90, 60)
    rng = np.random.default_rng(0)
    blue = rng.integers(30, 110, size=swir.shape[:2])
    wildfires = np.stack([blue + 50, blue + 40, blue], axis=-1).astype(np.uint8)
    wildfires[38:41, 38:41, 0] = 250
    return swir, true_color, wildfires


def write_scene(directory, swir, true_color=None, wildfires=None):
    directory.mkdir(parents=True)
    for kind, image in (("SWIR", swir), ("True_color", true_color), ("Wildfires", wildfires)):
        if image is not None:
            Image.fromarray(image).save(directory / f"{PREFIX}_{kind}.png")


def test_scene_metrics():
    swir, true_color, wildfires = synthetic_scene()

    metrics = validate_scene(swir, true_color, wildfires)

    assert metrics.fire_source == "wildfires"
    assert metrics.fire_count == 1
    assert metrics.fires_in_zone == 1.0
    assert metrics.fires_inside_burned_px == 1.0
    assert metrics.fires_with_negative_nbr_px == 1.0
    assert metrics.burned_area_px[0.0] == 40 * 40
    assert set(metrics.burned_area_px) == {-0.02, 0.0, 0.02}
    assert metrics.smoke_leakage == 0.0
    assert metrics.cloud_leakage == 0.0
    assert metrics.swir_precision == 0.5  # el foco de fuera no está en la Wildfires
    assert metrics.swir_recall == 1.0


def test_swir_only_scene_has_no_leakage_nor_agreement():
    swir, _, _ = synthetic_scene()

    metrics = validate_scene(swir)

    assert metrics.fire_source == "swir"
    assert metrics.fire_count == 2
    assert metrics.fires_in_zone == 0.5
    assert metrics.fires_inside_burned_px == 0.5
    assert metrics.smoke_leakage is None
    assert metrics.swir_precision is None


def test_validate_command_writes_report_for_every_scene(tmp_path, capsys):
    swir, true_color, wildfires = synthetic_scene()
    write_scene(tmp_path / "data" / "con-todo", swir, true_color, wildfires)
    write_scene(tmp_path / "data" / "solo-swir", swir)
    report = tmp_path / "validacion.md"

    exit_code = main(["validate", "--data", str(tmp_path / "data"), "--out", str(report)])

    assert exit_code == 0
    text = report.read_text(encoding="utf-8")
    assert text == capsys.readouterr().out
    for heading in (
        "Focos activos dentro de la superficie quemada",
        "Estabilidad del área",
        "Fuga de humo y nube",
        "Detector SWIR frente a la Wildfires",
        "EMSR913",
    ):
        assert heading in text
    assert "con-todo" in text and "solo-swir" in text
