"""API HTTP: envoltorio fino del motor que además sirve las capas y el frontend.

Cada análisis deja en disco una carpeta propia con las vistas web (reducidas) de las
composiciones subidas y, cuando el motor las genere, sus capas. La respuesta es el JSON
del contrato tal como lo devuelve el motor: las rutas de `layers` siguen siendo relativas
al directorio de salida, y la cabecera `Location` dice cuál es, de modo que el cliente
resuelve `<Location>/layers/<ruta>` y `<Location>/composites/<composición>`.
"""

import json
import os
import re
import shutil
import tempfile
from pathlib import Path
from typing import Annotated, Any
from uuid import uuid4

import numpy as np
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from PIL import Image, UnidentifiedImageError

from fire_engine import analyse_scene, load_composite

#: Campo del formulario → etiqueta de la composición en los mensajes al usuario.
COMPOSITE_LABELS = {"swir": "SWIR", "true_color": "True Color", "wildfires": "Wildfires"}

#: Lado máximo de las vistas que viajan al navegador; el análisis va a resolución completa.
WEB_VIEW_MAX_SIDE = 2500

_ANALYSIS_ID = re.compile(r"\A[0-9a-f]{32}\Z")
_LAYER_FILE = re.compile(r"\A[\w.-]+\.png\Z")


def create_app(work_dir: Path | None = None) -> FastAPI:
    """Crea la aplicación.

    `work_dir` es la carpeta donde se guardan los análisis (por omisión, una temporal).
    """
    app = FastAPI(title="Detección de incendios sobre composiciones Sentinel-2")
    analyses = _Analyses(work_dir)
    root = _project_root()

    @app.post("/api/analyses", status_code=201)
    def post_analysis(
        swir: Annotated[UploadFile | None, File()] = None,
        true_color: Annotated[UploadFile | None, File()] = None,
        wildfires: Annotated[UploadFile | None, File()] = None,
    ) -> JSONResponse:
        """Analiza una escena a partir de las composiciones subidas en sus tres campos."""
        uploads = {"swir": swir, "true_color": true_color, "wildfires": wildfires}
        if uploads["swir"] is None:
            raise HTTPException(400, "Falta la composición SWIR: es la única obligatoria.")
        composites = {
            field: _decode(field, upload) for field, upload in uploads.items() if upload is not None
        }

        analysis_id = uuid4().hex
        directory = analyses.create(analysis_id)
        try:
            result = analyse_scene(
                composites["swir"],
                true_color=composites.get("true_color"),
                wildfires=composites.get("wildfires"),
                out_dir=directory / "layers",
            )
        except ValueError as error:
            shutil.rmtree(directory, ignore_errors=True)
            raise HTTPException(400, str(error)) from error
        _write_web_views(directory, composites)
        return JSONResponse(
            result,
            status_code=201,
            headers={"Location": f"/api/analyses/{analysis_id}"},
        )

    @app.get("/api/analyses/{analysis_id}/composites/{kind}")
    def get_composite_view(analysis_id: str, kind: str) -> FileResponse:
        """Vista web (reducida) de una de las composiciones subidas."""
        if kind not in COMPOSITE_LABELS:
            raise HTTPException(404, f"No existe la composición «{kind}».")
        return _serve(analyses.locate(analysis_id) / "composites" / f"{kind}.jpg")

    @app.get("/api/analyses/{analysis_id}/layers/{name}")
    def get_layer(analysis_id: str, name: str) -> FileResponse:
        """Capa PNG generada por el motor para este análisis."""
        if not _LAYER_FILE.match(name):
            raise HTTPException(404, f"No existe la capa «{name}».")
        return _serve(analyses.locate(analysis_id) / "layers" / name)

    @app.get("/api/example")
    def get_example() -> dict[str, Any]:
        """Resultado de ejemplo del contrato, para ver el visor sin analizar nada."""
        return json.loads((root / "contract" / "example.json").read_text(encoding="utf-8"))

    frontend = root / "web"
    if frontend.is_dir():
        app.mount("/", StaticFiles(directory=frontend, html=True), name="web")
    return app


def _project_root() -> Path:
    """Raíz donde viven `web/` y `contract/`.

    Con el paquete instalado de forma editable es la raíz del repo. Con una instalación
    normal (la imagen Docker) el paquete vive en `site-packages` y de `__file__` no se
    deduce nada, así que quien la construya define `FIRE_ENGINE_ROOT`.
    """
    override = os.environ.get("FIRE_ENGINE_ROOT")
    return Path(override) if override else Path(__file__).resolve().parents[2]


class _Analyses:
    """Carpeta de los análisis. La temporal se crea al primer análisis, no al importar."""

    def __init__(self, root: Path | None) -> None:
        self._root = root

    def create(self, analysis_id: str) -> Path:
        if self._root is None:
            self._root = Path(tempfile.mkdtemp(prefix="fire-engine-"))
        directory = self._root / analysis_id
        directory.mkdir(parents=True, exist_ok=True)
        return directory

    def locate(self, analysis_id: str) -> Path:
        """Carpeta de un análisis ya hecho; 404 si el identificador no es uno nuestro."""
        if self._root is None or not _ANALYSIS_ID.match(analysis_id):
            raise HTTPException(404, "No existe ese análisis.")
        return self._root / analysis_id


def _decode(field: str, upload: UploadFile) -> np.ndarray:
    try:
        return load_composite(upload.file)
    except (UnidentifiedImageError, OSError) as error:
        label = COMPOSITE_LABELS[field]
        raise HTTPException(
            400, f"El archivo de la composición {label} no es una imagen válida."
        ) from error


def _write_web_views(directory: Path, composites: dict[str, np.ndarray]) -> None:
    views = directory / "composites"
    views.mkdir(parents=True, exist_ok=True)
    for field, image in composites.items():
        view = Image.fromarray(image)
        view.thumbnail((WEB_VIEW_MAX_SIDE, WEB_VIEW_MAX_SIDE))
        view.save(views / f"{field}.jpg", quality=85)


def _serve(path: Path) -> FileResponse:
    if not path.is_file():
        raise HTTPException(404, f"No existe «{path.name}» en este análisis.")
    return FileResponse(path)


app = create_app()
