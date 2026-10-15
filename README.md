# Detección de incendios en composiciones Sentinel-2

Aplicación web y CLI para delimitar **superficie quemada** y **focos activos** a partir de composiciones JPEG ya renderizadas del Copernicus Browser. La composición SWIR es obligatoria; True Color y Wildfires son opcionales. El motor delimita zonas y perímetros, descarta humo y nubes cuando recibe True Color y detecta focos activos. Las cifras geográficas siguen en desarrollo.

## Arranque con Docker

Desde la raíz del repositorio, con Docker Compose disponible:

```sh
docker compose up --build
```

Abrir <http://localhost:8000>. El servicio monta `data/` como solo lectura en `/data` y `out/` en `/out` para el CLI; la API guarda sus análisis temporalmente dentro del contenedor. Para parar, pulsar `Ctrl+C`.

El contenedor sirve la web en `/` y la API en `/api/analyses`. Tras actualizar el repositorio, reconstruir la imagen con el comando anterior para incluir la versión actual de la web.

### La web

La página sube las composiciones en **tres casillas con nombre** (SWIR obligatoria; True Color y Wildfires opcionales): la composición se identifica por la casilla, nunca por el nombre del archivo. Mientras analiza hay barra de progreso, y el resultado se dibuja sobre la imagen con Leaflet en coordenadas de píxel: se puede cambiar la imagen de fondo entre las composiciones subidas (True Color por defecto si se aportó) y encender o apagar cada capa (superficie quemada, severidad relativa, perímetro y focos activos). Las capas ausentes se muestran deshabilitadas.

El botón «Ver resultado de ejemplo» carga [`contract/example.json`](contract/example.json), útil para ver el visor con zonas, focos y alertas de demostración. Las alertas geográficas aún no se generan en los análisis reales.

### CLI dentro del contenedor

```sh
docker compose run --rm app fire-engine analyse \
  --swir /data/huelva/2026-08-08-00_00_2026-08-08-23_59_Sentinel-2_L2A_SWIR.jpg \
  --true-color /data/huelva/2026-08-08-00_00_2026-08-08-23_59_Sentinel-2_L2A_True_color.jpg \
  --wildfires /data/huelva/2026-08-08-00_00_2026-08-08-23_59_Sentinel-2_L2A_Wildfires.jpg \
  --out /out/huelva
```

La salida es `out/huelva/result.json`, `burned_mask.png`, `severity_mask.png`, `active_fire_mask.png` y `preview.png`. Para otras escenas, sustituir las rutas; `--true-color` y `--wildfires` son opcionales. Para pasar un bbox WGS84, añadir `--bbox LON_MIN LAT_MIN LON_MAX LAT_MAX` antes de `--out`. Ejemplo: `--bbox -7.5 37.0 -6.8 37.5`. Las coordenadas deben corresponder al encuadre de la escena; **no se pueden deducir del JPEG**. Por ahora el bbox queda registrado en el JSON, pero no produce hectáreas ni kilómetros.

En PowerShell, el mismo comando se puede escribir en una sola línea. Otra opción es instalar el paquete con `python -m pip install -e .` y ejecutar `fire-engine analyse --swir … --out out/huelva` en el equipo local.

## Entradas y resultado

| Composición | Obligatoria | Uso actual |
| --- | --- | --- |
| SWIR (`--swir`) | Sí | Superficie quemada, zonas, perímetros, severidad relativa y estimación de focos activos de confianza baja si falta Wildfires. |
| True Color (`--true-color`) | No | Descarte de humo y nubes e imagen de fondo para `preview.png`. |
| Wildfires (`--wildfires`) | No | Focos activos QuickFire en cuatro niveles, con confianza alta. |

Las composiciones de una escena deben tener el mismo tamaño y estar co-registradas. El JSON sigue [`contract/result.schema.json`](contract/result.schema.json); [`contract/example.json`](contract/example.json) muestra la estructura de zonas, focos, alertas y capas. Las alertas y áreas geográficas siguen vacías o en `null` hasta integrar la georreferencia y las poblaciones (#7 y #9).

## Método

1. En la composición SWIR, el motor calcula NBR como `(G − R)/(G + R)`; ambas bandas están en el mismo JPEG con la misma ganancia. Multi-Otsu de **cuatro clases**, estimado para cada escena, aísla la clase inferior como candidata quemada. Una segunda separación de dos clases dentro de esa superficie distingue afectado de muy afectado. Limpieza morfológica y componentes conexas forman zonas; los contornos se simplifican para dibujar el perímetro. La severidad es **relativa a la propia escena**.
2. El descarte de humo y nubes compara el brillo de True Color y SWIR; también contempla vegetación, agua y sombra. Sin True Color, el análisis usa solo señales de SWIR y comunica menor confianza para la superficie quemada.
3. Con Wildfires, el detector decodifica los colores QuickFire ya pintados por Copernicus Browser para localizar focos activos y su nivel 1–4. Sin ella, recurre a una estimación parcial basada en B12 y B8A de la SWIR, de menor confianza.
4. La georreferencia prevista transformará las coordenadas de píxel en hectáreas y kilómetros (#7). Las poblaciones cercanas y sus alertas por distancia requieren coordenadas fiables y llegarán con #9.

El fundamento, las mediciones y los casos problemáticos están en [`docs/research/sentinel2-rgb-fire-sota.md`](docs/research/sentinel2-rgb-fire-sota.md).

## Validación sin ground truth

```sh
fire-engine validate --data data --out docs/results/validacion.md
```

Calcula cuatro métricas de autoconsistencia sobre cada escena de `data/` y escribe el informe en [`docs/results/validacion.md`](docs/results/validacion.md) (≈ 50 s, ≈ 3 GB de RAM por Madrid-Ávila). Cifras actuales:

| Métrica | Guadalajara | Huelva | Madrid-Ávila |
| --- | ---: | ---: | ---: |
| Focos activos que tocan una zona | 36 de 56 (64,3 %) | 47 de 106 (44,3 %) | 80 de 203 (39,4 %) ¹ |
| Píxeles de foco con NBR < 0 (referencia §4.6: 99 % / 91 %) | 99,9 % | 91,1 % | 100 % ¹ |
| Píxeles de foco dentro de la superficie quemada | 64,1 % | 58,7 % | 73,5 % ¹ |
| Área con umbral NBR ±0,02 (banda de incertidumbre) | ±6,1 % | ±21,3 % | ±9,7 % |
| Superficie quemada con humo, corte del motor D > 2 / corte §4.3 D > 1 | 0 % / 18,7 % | 0 % / 14,7 % | 0 % / 13,6 % |
| Superficie quemada con nube | 0 % | 0,3 % | 0 % |
| Detector SWIR frente a la Wildfires: precisión / exhaustividad | 27,9 % / 75,7 % | 62,7 % / 59,8 % | — |

¹ Sin Wildfires: focos del detector SWIR (confianza baja).

Cómo leerlas:

- **Focos dentro de la superficie quemada.** El NBR < 0 reproduce la referencia medida. Que solo el 59–64 % de los píxeles caiga dentro de la máscara no es un fallo del cálculo. En Huelva hay 3 590 píxeles de foco fuera, y 3 371 de ellos tienen un NBR entre el umbral de la escena (−0,05) y 0. Casi todos son de nivel 1–2: es el **frente activo**, que aún no tiene NBR de cicatriz. El test de nube de la superficie quemada también marca 3 318 de esos píxeles, porque una llama es brillante en las dos composiciones. Pero aunque no los recortara, solo entrarían unos 220. Estas cifras de diagnóstico se midieron aparte, una vez; no salen del comando. Por eso el resultado del motor añade un aviso en `summary.warnings` cuando hay focos fuera de la superficie quemada; en escenas con el incendio en marcha, el aviso es lo esperado.
- **Banda de incertidumbre.** En Huelva, el umbral cae en la ladera del histograma: ±0,02 en NBR mueve el área un ±21 %. Las hectáreas de esa escena deben darse como rango.
- **Humo y nube.** El motor ya excluye el humo con D > 2 y la nube, así que esas columnas solo miden lo que reintroduce la limpieza morfológica. Un 14–19 % de la superficie cumple el corte más laxo D > 1: es cicatriz bajo humo fino que la SWIR atraviesa, y por eso el motor usa D > 2 (ver `false_positives.py`).
- **EMSR913.** No se compara: la escena de Huelva no tiene georreferencia (ver §5 del informe).

## Límites

- Estos JPEG **no incluyen B11**, por lo que el detector QuickFire no se puede reconstruir íntegramente sin la composición Wildfires.
- No hay imagen anterior al incendio: no se calcula dNBR ni severidad absoluta, y una superficie oscura previa podría confundirse con quemado.
- Los JPEG de `data/` no llevan escala ni coordenadas. Sin bbox o GeoTIFF no se deben publicar hectáreas, kilómetros ni poblaciones afectadas.
- Humo, nubes, agua, sombras, suelo desnudo y zonas urbanas pueden provocar errores; la confianza refleja qué composiciones respaldan cada resultado. Un foco activo fuera de una zona quemada requiere revisión.
- La captura Sentinel-2 muestra el estado en el momento de adquisición; no es seguimiento en tiempo real.

## Trabajo futuro

Dirección del humo y propagación para mejorar las alertas; refinamiento opcional de contornos con SAM2; despliegue público. El criterio de alerta previsto se basa en distancias y **no** predice la evolución del incendio.
