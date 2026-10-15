import io
import json

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from conftest import CONTRACT, scene_composite
from fire_engine.api import create_app


@pytest.fixture
def client(tmp_path):
    return TestClient(create_app(work_dir=tmp_path))


def png(width: int, height: int, colour: tuple[int, int, int] = (20, 60, 30)) -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (width, height), colour).save(buffer, format="PNG")
    return buffer.getvalue()


def upload(name: str, data: bytes = b"", filename: str = "composicion.png") -> dict:
    return {name: (filename, data or png(40, 30), "image/png")}


def test_uploading_only_the_swir_returns_a_valid_result(client, validate_result):
    with scene_composite("huelva", "SWIR").open("rb") as swir:
        response = client.post("/api/analyses", files={"swir": ("swir.jpg", swir, "image/jpeg")})

    assert response.status_code == 201
    result = response.json()
    validate_result(result)
    assert result["scene"]["composites"] == ["swir"]
    assert (result["scene"]["width"], result["scene"]["height"]) == (2500, 1546)


def test_each_composite_is_identified_by_its_field_not_by_the_filename(client, validate_result):
    response = client.post(
        "/api/analyses",
        files={
            "swir": ("True_color.jpg", png(40, 30), "image/png"),
            "true_color": ("cualquier-cosa.bin", png(40, 30), "image/png"),
            "wildfires": ("SWIR.jpg", png(40, 30), "image/png"),
        },
    )

    assert response.status_code == 201
    result = response.json()
    validate_result(result)
    assert result["scene"]["composites"] == ["swir", "true_color", "wildfires"]


def test_a_missing_swir_is_rejected_with_a_message_naming_it(client):
    response = client.post("/api/analyses", files=upload("true_color"))

    assert response.status_code == 400
    assert "SWIR" in response.json()["detail"]


def test_an_empty_swir_box_is_rejected_like_a_missing_one(client):
    # Un navegador manda la casilla vacía como una parte con filename="".
    response = client.post(
        "/api/analyses",
        files={"swir": ("", b"", "application/octet-stream"), **upload("true_color")},
    )

    assert response.status_code == 400
    assert "SWIR" in response.json()["detail"]


def test_composites_of_different_size_are_rejected_with_a_clear_message(client):
    response = client.post(
        "/api/analyses",
        files={
            "swir": ("swir.png", png(40, 30), "image/png"),
            "true_color": ("tc.png", png(41, 30), "image/png"),
        },
    )

    assert response.status_code == 400
    assert "mismo tamaño" in response.json()["detail"]


def test_a_file_that_is_not_an_image_is_rejected_naming_the_composite(client):
    response = client.post(
        "/api/analyses",
        files={"wildfires": ("notas.txt", b"no soy una imagen", "text/plain"), **upload("swir")},
    )

    assert response.status_code == 400
    detail = response.json()["detail"]
    assert "Wildfires" in detail and "no es una imagen válida" in detail


def test_the_uploaded_composites_are_served_back_for_the_viewer(client):
    with scene_composite("huelva", "SWIR").open("rb") as swir:
        response = client.post(
            "/api/analyses",
            files={"swir": ("swir.jpg", swir, "image/jpeg"), **upload("true_color", png(2500, 1546))},
        )
    analysis = response.headers["location"]

    for kind in ("swir", "true_color"):
        view = client.get(f"{analysis}/composites/{kind}")
        assert view.status_code == 200
        assert view.headers["content-type"] == "image/jpeg"
        with Image.open(io.BytesIO(view.content)) as image:
            assert image.size == (2500, 1546)

    assert client.get(f"{analysis}/composites/wildfires").status_code == 404


def test_a_composite_too_large_for_the_browser_is_served_reduced(client):
    response = client.post("/api/analyses", files=upload("swir", png(4000, 2000)))
    analysis = response.headers["location"]

    view = client.get(f"{analysis}/composites/swir")

    with Image.open(io.BytesIO(view.content)) as image:
        width, height = image.size
        assert width < 4000
        assert width / height == 2.0  # el encuadre no cambia, solo el tamaño


def test_the_layers_the_engine_writes_are_served_from_the_analysis(client):
    with scene_composite("huelva", "SWIR").open("rb") as swir:
        response = client.post("/api/analyses", files={"swir": ("swir.jpg", swir, "image/jpeg")})
    analysis = response.headers["location"]

    # El contrato da las capas como rutas relativas al directorio de salida, y ese
    # directorio es la carpeta del análisis, así que el cliente las resuelve contra ella.
    layers = response.json()["layers"]
    assert layers["burned_mask"] == "burned_mask.png"
    for path in filter(None, layers.values()):
        served = client.get(f"{analysis}/layers/{path}")
        assert served.status_code == 200, path
        assert served.headers["content-type"] == "image/png"


def test_a_scene_the_engine_rejects_leaves_no_analysis_behind(client, tmp_path):
    response = client.post(
        "/api/analyses",
        files={
            "swir": ("swir.png", png(40, 30), "image/png"),
            "true_color": ("tc.png", png(41, 30), "image/png"),
        },
    )

    assert response.status_code == 400
    assert list(tmp_path.iterdir()) == []


def test_an_unknown_analysis_or_composite_is_not_found(client):
    assert client.get("/api/analyses/0123456789abcdef/composites/swir").status_code == 404
    assert client.get("/api/analyses/no-es-un-id/composites/swir").status_code == 404

    response = client.post("/api/analyses", files=upload("swir"))
    analysis = response.headers["location"]

    assert client.get(f"{analysis}/composites/humo").status_code == 404
    assert client.get(f"{analysis}/layers/..%2f..%2fexample.json").status_code == 404


def test_the_example_result_is_served_for_developing_the_viewer(client, validate_result):
    response = client.get("/api/example")

    assert response.status_code == 200
    validate_result(response.json())
    assert response.json() == json.loads((CONTRACT / "example.json").read_text(encoding="utf-8"))


def test_the_project_root_can_be_pointed_elsewhere(tmp_path, monkeypatch):
    # Es lo que necesita una instalación no editable, como la de la imagen Docker:
    # el paquete vive en site-packages y de __file__ no se deduce dónde está `web/`.
    (tmp_path / "web").mkdir()
    (tmp_path / "web" / "index.html").write_text("<p>otra raíz</p>", encoding="utf-8")
    (tmp_path / "contract").mkdir()
    (tmp_path / "contract" / "example.json").write_text('{"desde": "otra raíz"}', encoding="utf-8")
    monkeypatch.setenv("FIRE_ENGINE_ROOT", str(tmp_path))

    client = TestClient(create_app(work_dir=tmp_path / "analyses"))

    assert client.get("/").text == "<p>otra raíz</p>"
    assert client.get("/api/example").json() == {"desde": "otra raíz"}


def test_the_frontend_is_served_at_the_root(client):
    response = client.get("/")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert "composiciones" in response.text
    assert client.get("/vendor/leaflet/leaflet.js").status_code == 200


def test_upload_with_bbox_returns_metric_result_and_geo_features(client, validate_result):
    response = client.post(
        "/api/analyses",
        data={"west": "-0.016", "south": "-0.012", "east": "0.016", "north": "0.012"},
        files=upload("swir"),
    )

    assert response.status_code == 201
    result = response.json()
    validate_result(result)
    assert result["scene"]["georeference"] == {
        "bbox": [-0.016, -0.012, 0.016, 0.012], "source": "manual"
    }
    assert result["scene"]["metres_per_pixel"] > 0
    assert result["summary"]["burned_area_ha"] is not None


def test_upload_rejects_incomplete_or_inverted_bbox(client):
    for bbox in (
        {"west": "-1"},
        {"west": "1", "south": "0", "east": "-1", "north": "1"},
        {"west": "-1", "south": "0", "east": "1", "north": "90"},
        {"west": "abc", "south": "0", "east": "1", "north": "1"},
    ):
        response = client.post("/api/analyses", data=bbox, files=upload("swir"))
        assert response.status_code == 400
        assert "bbox" in response.json()["detail"]
