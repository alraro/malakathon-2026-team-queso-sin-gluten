import csv
import io
import json

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from fire_engine import Georeference, analyse_scene
from fire_engine.api import create_app
from fire_engine.cli import main
from test_engine import scene_with_scar


def settlements_file(tmp_path, rows):
    path = tmp_path / "settlements.csv"
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(("name", "longitude", "latitude", "population"))
        writer.writerows(rows)
    return path


def test_three_settlements_get_ordered_alert_levels_and_zone_nearest(tmp_path, validate_result):
    # La zona termina cerca de 0,015° E. Los puntos siguientes quedan dentro,
    # a ~3 km y ~7 km de su superficie, respectivamente.
    dataset = settlements_file(tmp_path, [
        ("Vigilancia", 0.078, 0.005, 80),
        ("Dentro", 0.010, 0.005, 120),
        ("Media", 0.042, 0.005, 250),
    ])
    result = analyse_scene(
        scene_with_scar(),
        georeference=Georeference((0, -0.015, 0.04, 0.015), "manual"),
        settlements_path=dataset,
    )

    validate_result(result)
    alerts = result["alerts"]
    assert [(item["settlement"], item["level"]) for item in alerts] == [
        ("Dentro", "high"), ("Media", "medium"), ("Vigilancia", "watch")
    ]
    assert [item["distance_km"] for item in alerts] == sorted(item["distance_km"] for item in alerts)
    assert [item["population"] for item in alerts] == [120, 250, 80]
    assert all(item["nearest_to"] == "burned_area" for item in alerts)
    assert result["zones"]["features"][0]["properties"]["nearest_settlement"] == {
        "name": "Dentro", "distance_km": 0.0
    }


def test_without_georeference_has_no_alerts_even_with_dataset(tmp_path):
    dataset = settlements_file(tmp_path, [("Dentro", 0.010, 0.005, 120)])

    result = analyse_scene(scene_with_scar(), settlements_path=dataset)

    assert result["alerts"] == []
    assert result["zones"]["features"][0]["properties"]["nearest_settlement"] is None


def test_replacing_dataset_file_changes_settlements_without_code_changes(tmp_path):
    first = settlements_file(tmp_path, [("Primera", 0.010, 0.005, 120)])
    second = tmp_path / "other-country.csv"
    second.write_text("name,longitude,latitude,population\nSegunda,0.010,0.005,320\n", encoding="utf-8")
    kwargs = {"georeference": Georeference((0, -0.015, 0.04, 0.015), "manual")}

    one = analyse_scene(scene_with_scar(), settlements_path=first, **kwargs)
    two = analyse_scene(scene_with_scar(), settlements_path=second, **kwargs)

    assert one["alerts"][0]["settlement"] == "Primera"
    assert two["alerts"][0]["settlement"] == "Segunda"


def test_configurable_distances_change_alert_level(tmp_path):
    from fire_engine import AlertDistances

    dataset = settlements_file(tmp_path, [("Media", 0.042, 0.005, 250)])
    kwargs = {
        "georeference": Georeference((0, -0.015, 0.04, 0.015), "manual"),
        "settlements_path": dataset,
    }

    ordinary = analyse_scene(scene_with_scar(), **kwargs)
    expanded = analyse_scene(scene_with_scar(), alert_distances=AlertDistances(2, 2.5, 4), **kwargs)

    assert ordinary["alerts"][0]["level"] == "medium"
    assert expanded["alerts"][0]["level"] == "watch"


def test_fire_within_two_kilometres_produces_high_alert(tmp_path):
    swir = scene_with_scar()
    swir[90:94, 100:104] = (255, 90, 60)
    dataset = settlements_file(tmp_path, [("Cerca del foco", 0.039, -0.008, 90)])

    result = analyse_scene(
        swir,
        georeference=Georeference((0, -0.015, 0.04, 0.015), "manual"),
        settlements_path=dataset,
    )

    assert result["alerts"][0]["level"] == "high"
    assert result["alerts"][0]["nearest_to"] == "active_fire"
    assert result["alerts"][0]["distance_km"] < 2


def test_inside_perimeter_is_high_even_in_an_unburned_island(tmp_path):
    swir = scene_with_scar()
    swir[32:43, 32:43] = (60, 150, 40)
    dataset = settlements_file(tmp_path, [("Isla", 0.0095, 0.0055, 60)])

    result = analyse_scene(
        swir,
        georeference=Georeference((0, -0.015, 0.04, 0.015), "manual"),
        settlements_path=dataset,
    )

    assert result["alerts"][0]["level"] == "high"
    assert result["alerts"][0]["nearest_to"] == "burned_area"
    assert result["alerts"][0]["distance_km"] > 0


def test_cli_accepts_another_country_csv_and_thresholds(tmp_path, validate_result):
    dataset = settlements_file(tmp_path, [("Media", 0.042, 0.005, 250)])
    image = tmp_path / "swir.png"
    Image.fromarray(scene_with_scar()).save(image)
    output = tmp_path / "out"

    assert main([
        "analyse", "--swir", str(image), "--bbox", "0", "-0.015", "0.04", "0.015",
        "--settlements", str(dataset), "--medium-km", "2.5", "--watch-km", "4",
        "--out", str(output),
    ]) == 0

    result = json.loads((output / "result.json").read_text(encoding="utf-8"))
    validate_result(result)
    assert result["alerts"][0]["level"] == "watch"


def test_api_uses_its_configured_dataset(tmp_path, validate_result):
    dataset = settlements_file(tmp_path, [("Dentro", 0.010, 0.005, 120)])
    buffer = io.BytesIO()
    Image.fromarray(scene_with_scar()).save(buffer, format="PNG")
    client = TestClient(create_app(work_dir=tmp_path / "analyses", settlements_path=dataset))

    response = client.post(
        "/api/analyses",
        files={"swir": ("swir.png", buffer.getvalue(), "image/png")},
        data={"west": "0", "south": "-0.015", "east": "0.04", "north": "0.015"},
    )

    assert response.status_code == 201
    validate_result(response.json())
    assert response.json()["alerts"][0]["settlement"] == "Dentro"
