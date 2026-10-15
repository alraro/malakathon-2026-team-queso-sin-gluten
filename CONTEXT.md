# Detección de incendios sobre composiciones Sentinel-2

Herramienta que, a partir de imágenes Sentinel-2 ya renderizadas (JPEG) de un episodio de incendio, delimita la superficie quemada y los focos activos y los presenta de forma comprensible para cualquier usuario.

## Language

El dominio se habla en español; entre paréntesis, el identificador en inglés que se usa en código y en el JSON de salida.

### Entradas

**Escena** (`scene`):
Un único instante de adquisición Sentinel-2 sobre una zona, representado por una o varias composiciones co-registradas (mismo encuadre, mismo píxel).
_Avoid_: imagen (cuando se refiere al conjunto), captura

**Composición** (`composite`):
Un render RGB de 8 bits de la escena con una receta de bandas concreta. Hay tres tipos: SWIR, True Color y Wildfires.
_Avoid_: capa, banda, filtro

**Composición SWIR** (`swir`):
Composición `[B12, B8A, B04]` con ganancia lineal. Es la única obligatoria: de ella sale la superficie quemada.
_Avoid_: imagen infrarroja, cámara SWIR

**Composición True Color** (`true_color`):
Composición en color visible `[B04, B03, B02]`. Opcional; su papel es descartar humo y nubes.
_Avoid_: RGB, foto

**Composición Wildfires** (`wildfires`):
Composición del Copernicus Browser (QuickFire de Markuse) que lleva pintada una clasificación de focos activos en 4 niveles. Opcional; cuando existe, es la fuente preferente de focos activos.
_Avoid_: imagen de fuego, capa de incendios

### Resultados

**Superficie quemada** (`burned_area`):
Conjunto de píxeles con evidencia de haber ardido (cicatriz), con o sin fuego en el momento de la adquisición.
_Avoid_: zona afectada (en código), área quemada, burn scar

**Foco activo** (`active_fire`):
Píxel o grupo de píxeles con evidencia de fuego ardiendo en el instante de la adquisición. Es un subconjunto conceptual distinto de la superficie quemada y se representa por separado.
_Avoid_: fuego, hotspot, frente

**Zona** (`zone`):
Una mancha conexa de superficie quemada que supera el área mínima cartografiable (~30 ha). Es la unidad que se resalta, describe y compara; una escena puede tener varias (p. ej. dos incendios distintos).
_Avoid_: cluster, componente, incendio (una zona no tiene por qué ser un incendio completo)

**Severidad relativa** (`relative_severity`):
Clasificación de la superficie quemada en "afectado" / "muy afectado" relativa a la propia escena. No es comparable entre escenas ni equivale a las clases dNBR.
_Avoid_: severidad (a secas), daño

**Perímetro** (`perimeter`):
Contorno vectorial simplificado de la superficie quemada. Su longitud depende de la tolerancia de simplificación y siempre se da junto a ella.
_Avoid_: borde, límite

**Confianza** (`confidence`):
Indicador ordinal de lo fiable que es un resultado según qué composiciones se aportaron (p. ej. focos activos sin composición Wildfires = confianza baja).
_Avoid_: probabilidad, score

### Georreferencia

**Georreferencia** (`georeference`):
La extensión geográfica de la escena (coordenadas de sus esquinas) aportada por el usuario o leída de un GeoTIFF. Sin ella no se dan hectáreas ni pueblos.
_Avoid_: posición, altura, ubicación de la cámara

### Impacto

**Población** (`settlement`):
Un núcleo habitado (municipio o localidad) con nombre, coordenadas y número de habitantes, tomado de un dataset local por país.
_Avoid_: pueblo, ciudad, localidad (en código)

**Alerta** (`alert`):
Nivel de riesgo (alta / media / vigilancia) asignado a una población según su distancia a la superficie quemada o a un foco activo.
_Avoid_: aviso, riesgo, peligro
