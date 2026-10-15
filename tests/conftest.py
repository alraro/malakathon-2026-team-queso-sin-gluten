import json
from pathlib import Path

import jsonschema
import pytest

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
CONTRACT = ROOT / "contract"


def scene_composite(scene: str, kind: str) -> Path:
    """Path to a composite of a scene in data/ ("SWIR", "True_color", "Wildfires")."""
    matches = sorted((DATA / scene).glob(f"*_{kind}.jpg"))
    assert matches, f"{scene} has no {kind} composite in data/ (git lfs pull?)"
    return matches[0]


@pytest.fixture(scope="session")
def validate_result():
    schema = json.loads((CONTRACT / "result.schema.json").read_text())
    jsonschema.Draft202012Validator.check_schema(schema)
    validator = jsonschema.Draft202012Validator(schema)

    def validate(result: dict) -> None:
        # Round-trip through JSON so non-serialisable values (numpy scalars) fail too.
        validator.validate(json.loads(json.dumps(result)))

    return validate
