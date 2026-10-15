"""Motor de análisis de escena.

Única interfaz pública: :func:`analyse_scene` (composiciones → resultado conforme a
``contract/result.schema.json``) y :func:`load_composite` para leer una composición
desde disco. Todo lo demás del paquete es interno.
"""

from fire_engine.engine import Georeference, analyse_scene
from fire_engine.io import load_composite

__all__ = ["Georeference", "analyse_scene", "load_composite"]
