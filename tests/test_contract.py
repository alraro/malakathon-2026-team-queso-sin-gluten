import json

import jsonschema
import pytest

from conftest import CONTRACT


def test_example_validates_against_schema(validate_result):
    example = json.loads((CONTRACT / "example.json").read_text())
    validate_result(example)


def test_example_covers_what_the_frontend_needs():
    example = json.loads((CONTRACT / "example.json").read_text())
    assert len(example["zones"]["features"]) == 2
    fires = [f["properties"] for f in example["active_fires"]["features"]]
    assert {f["source"] for f in fires} == {"wildfires", "swir"}
    assert len({f["level"] for f in fires if f["source"] == "wildfires"}) > 1
    assert example["scene"]["georeference"] is not None
    assert {a["level"] for a in example["alerts"]} == {"high", "medium", "watch"}


def test_schema_rejects_unknown_confidence(validate_result):
    example = json.loads((CONTRACT / "example.json").read_text())
    example["summary"]["confidence"]["burned_area"] = "medium"
    with pytest.raises(jsonschema.ValidationError):
        validate_result(example)
