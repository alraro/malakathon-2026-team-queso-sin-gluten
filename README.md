# Detección de incendios en composiciones Sentinel-2

Aplicación web y CLI para delimitar **superficie quemada** y **focos activos** a partir de composiciones JPEG ya renderizadas del Copernicus Browser. La composición SWIR es obligatoria; True Color y Wildfires son opcionales. El motor delimita zonas y perímetros, descarta humo y nubes cuando recibe True Color y detecta focos activos. Con un bbox aportado por el usuario calcula hectáreas y kilómetros.

## Arranque con Docker

Desde la raíz del repositorio, con Docker Compose disponible:

```sh
docker compose up --build
```

Abrir <http://localhost:8000>. El servicio monta `data/` como solo lectura en `/data` y `out/` en `/out` para el CLI; la API guarda sus análisis temporalmente dentro del contenedor. Para parar, pulsar `Ctrl+C`.

El contenedor sirve la web en `/` y la API en `/api/analyses`. Tras actualizar el repositorio, reconstruir la imagen con el comando anterior para incluir la versión actual de la web.

### La web

La página sube las composiciones en **tres casillas con nombre** (SWIR obligatoria; True Color y Wildfires opcionales): la composición se identifica por la casilla, nunca por el nombre del archivo. Mientras analiza hay barra de progreso. Sin bbox, Leaflet dibuja el resultado sobre la imagen en coordenadas de píxel. Con norte, sur, este y oeste WGS84, sitúa la imagen, las zonas y los focos sobre el mapa topográfico OpenTopoMap y muestra las cifras en hectáreas y kilómetros, siempre con el supuesto «calculado con el bbox aportado por el usuario». El mapa base requiere conexión a Internet. En ambos modos se puede cambiar la composición de fondo (True Color por defecto si se aportó) y encender o apagar las capas. En el modo de encaje, las esquinas conservan la proporción de la composición y el zoom del mapa mantiene constante su tamaño en pantalla.

El botón «Ver resultado de ejemplo» carga [`contract/example.json`](contract/example.json), útil para ver el visor con zonas, focos y alertas de demostración. Con bbox, los análisis reales muestran las poblaciones dentro del umbral de vigilancia (10 km por defecto) de la superficie quemada o de un foco activo, con nivel de alerta, habitantes y distancia. La tarjeta de cada zona indica su población más cercana. Sin bbox, la lista explica por qué no hay alertas.

### CLI dentro del contenedor

```sh
docker compose run --rm app fire-engine analyse \
  --swir /data/huelva/2026-08-08-00_00_2026-08-08-23_59_Sentinel-2_L2A_SWIR.jpg \
  --true-color /data/huelva/2026-08-08-00_00_2026-08-08-23_59_Sentinel-2_L2A_True_color.jpg \
  --wildfires /data/huelva/2026-08-08-00_00_2026-08-08-23_59_Sentinel-2_L2A_Wildfires.jpg \
  --out /out/huelva
```

La salida es `out/huelva/result.json`, `burned_mask.png`, `severity_mask.png`, `active_fire_mask.png` y `preview.png`. Para otras escenas, sustituir las rutas; `--true-color` y `--wildfires` son opcionales. Para pasar un bbox WGS84, añadir `--bbox LON_MIN LAT_MIN LON_MAX LAT_MAX` antes de `--out`. Ejemplo: `--bbox -7.5 37.0 -6.8 37.5`. Las coordenadas deben corresponder al encuadre de la escena; **no se pueden deducir del JPEG**. Con bbox, el JSON incluye hectáreas de superficie quemada y por zona, área encerrada por el perímetro (incluidas islas sin quemar), kilómetros de perímetro y geometrías lon/lat.

En PowerShell, el mismo comando se puede escribir en una sola línea. Otra opción es instalar el paquete con `python -m pip install -e .` y ejecutar `fire-engine analyse --swir … --out out/huelva` en el equipo local.

El dataset local por defecto es [`settlements/ES.csv`](settlements/ES.csv), derivado de [GeoNames](https://download.geonames.org/export/dump/) bajo [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). Para usar otro país, pasa `--settlements ruta/al/archivo.csv` al CLI o define `FIRE_ENGINE_SETTLEMENTS_FILE` al iniciar la API o Docker; el CSV debe tener `name,longitude,latitude,population`. Los umbrales se cambian con `--high-fire-km`, `--medium-km` y `--watch-km` en la CLI o con `FIRE_ENGINE_HIGH_FIRE_KM`, `FIRE_ENGINE_MEDIUM_KM` y `FIRE_ENGINE_WATCH_KM` en la API. Véase [la procedencia y regeneración del dataset](settlements/README.md).

## Entradas y resultado

| Composición | Obligatoria | Uso actual |
| --- | --- | --- |
| SWIR (`--swir`) | Sí | Superficie quemada, zonas, perímetros, severidad relativa y estimación de focos activos de confianza baja si falta Wildfires. |
| True Color (`--true-color`) | No | Descarte de humo y nubes e imagen de fondo para `preview.png`. |
| Wildfires (`--wildfires`) | No | Focos activos QuickFire en cuatro niveles, con confianza alta. |

Las composiciones de una escena deben tener el mismo tamaño y estar co-registradas. El JSON sigue [`contract/result.schema.json`](contract/result.schema.json); [`contract/example.json`](contract/example.json) muestra la estructura de zonas, focos, alertas y capas. Sin bbox, todas las hectáreas, kilómetros y geometrías lon/lat son `null`, y `alerts` queda vacío.

## Método

1. En la composición SWIR, el motor calcula NBR como `(G − R)/(G + R)`; ambas bandas están en el mismo JPEG con la misma ganancia. Multi-Otsu de **cuatro clases**, estimado para cada escena, aísla la clase inferior como candidata quemada. Una segunda separación de dos clases dentro de esa superficie distingue afectado de muy afectado. Limpieza morfológica y componentes conexas forman zonas; los contornos se simplifican para dibujar el perímetro. La severidad es **relativa a la propia escena**.
2. El descarte de humo y nubes compara el brillo de True Color y SWIR; también contempla vegetación, agua y sombra. Sin True Color, el análisis usa solo señales de SWIR y comunica menor confianza para la superficie quemada.
3. Con Wildfires, el detector decodifica los colores QuickFire ya pintados por Copernicus Browser para localizar focos activos y su nivel 1–4. Sin ella, recurre a una estimación parcial basada en B12 y B8A de la SWIR, de menor confianza.
4. El bbox transforma las coordenadas de píxel mediante Web Mercator. El área real de cada píxel se corrige por latitud; solo las zonas de unas 30 ha o más se conservan. La longitud del perímetro se calcula sobre su geometría simplificada y se acompaña de la tolerancia aproximada en metros.
5. Con bbox, las distancias geodésicas a la superficie quemada y a los focos activos se comparan con el CSV local de poblaciones. Una población dentro del perímetro o a menos de 2 km de un foco recibe alerta alta; a menos de 5 km, media; a menos de 10 km, vigilancia. El criterio usa **solo distancia**: no modela humo ni propagación. Las coordenadas del núcleo y los habitantes provienen de GeoNames, y la exactitud depende también del bbox indicado.

El fundamento, las mediciones y los casos problemáticos están en [`docs/research/sentinel2-rgb-fire-sota.md`](docs/research/sentinel2-rgb-fire-sota.md).

## Validación sin ground truth

```sh
fire-engine validate --data data --out docs/results/validacion.md
```

Calcula cuatro métricas de autoconsistencia sobre cada escena de `data/` y escribe el informe en [`docs/results/validacion.md`](docs/results/validacion.md) (≈ 50 s, ≈ 3 GB de RAM por Madrid-Ávila). Cifras actuales:

| Métrica | Guadalajara | Huelva | Madrid-Ávila |
| --- | ---: | ---: | ---: |
| Focos activos que tocan una zona | 37 de 51 (72,5 %) | 50 de 55 (90,9 %) | 85 de 203 (41,9 %) ¹ |
| Píxeles de foco con NBR < 0 (referencia §4.6: 99 % / 91 %) | 100 % | 100 % | 100 % ¹ |
| Píxeles de foco dentro de la superficie quemada | 56,8 % | 96,8 % | 74,8 % ¹ |
| Área con umbral NBR ±0,02 (banda de incertidumbre) | ±4,9 % | ±7,6 % | ±6,1 % |
| Superficie quemada con humo, corte del motor D > 2 / corte §4.3 D > 1 | 0 % / 19,3 % | 0 % / 16,9 % | 0 % / 14,6 % |
| Superficie quemada con nube | 0 % | 0 % | 0 % |
| Detector SWIR frente a la Wildfires: precisión / exhaustividad | 27,9 % / 77,1 % | 62,7 % / 98,3 % | — |

¹ Sin Wildfires: focos del detector SWIR (confianza baja).

Cómo leerlas:

- **Focos dentro de la superficie quemada.** En Huelva cae dentro de la cicatriz el 96,8 % de los píxeles de foco; en Guadalajara, el 56,8 %, y eso no es un fallo del cálculo. Los focos que quedan fuera **pasan las dos pruebas de Murphy disponibles en la SWIR**: 14 de 14 en Guadalajara y 5 de 5 en Huelva, así que ahí hay combustión real. Lo que los deja fuera de la máscara no son los filtros de falsos positivos, sino los de fragmentación: la limpieza morfológica y el área mínima de 30 ha explican el 59 % de esos píxeles en Guadalajara (114 de 193 vuelven a entrar si se desactivan las dos), mientras que el umbral NBR solo descarta el 0,5 % — el frente tiene NBR de cicatriz, lo que no tiene es 30 hectáreas. La distancia mediana de un foco de fuera al borde quemado es de 5 px. Estas cifras de atribución se midieron aparte, una vez; no salen del comando. Por eso el resultado del motor añade un aviso en `summary.warnings` cuando hay focos fuera de la superficie quemada; en escenas con el incendio en marcha, el aviso es lo esperado (ver [ADR-0001](docs/adr/0001-focos-fuera-de-la-cicatriz.md)).
- **Banda de incertidumbre.** Desplazar el umbral ±0,02 en NBR mueve el área entre un ±4,9 % (Guadalajara) y un ±7,6 % (Huelva). Antes de modelar el suelo desnudo, Huelva llegaba a ±21 %: el corte caía en la ladera del histograma. Aun así, las hectáreas conviene leerlas como rango, no como cifra exacta.
- **Humo y nube.** El motor ya excluye el humo con D > 2 y la nube, así que esas columnas solo miden lo que reintroduce la limpieza morfológica. Un 15–19 % de la superficie cumple el corte más laxo D > 1: es cicatriz bajo humo fino que la SWIR atraviesa, y por eso el motor usa D > 2 (ver `false_positives.py`).
- **EMSR913.** No se compara: la escena de Huelva no tiene georreferencia (ver §5 del informe).

## Límites

- Estos JPEG **no incluyen B11**, por lo que el detector QuickFire no se puede reconstruir íntegramente sin la composición Wildfires.
- No hay imagen anterior al incendio: no se calcula dNBR ni severidad absoluta, y una superficie oscura previa podría confundirse con quemado.
- Los JPEG de `data/` no llevan escala ni coordenadas. Sin bbox no se publican hectáreas, kilómetros ni alertas; incluso con bbox, su precisión depende del encuadre aportado. Las alertas identifican proximidad, no confirman daños ni necesidad de evacuación.
- Humo, nubes, agua, sombras, suelo desnudo y zonas urbanas pueden provocar errores; la confianza refleja qué composiciones respaldan cada resultado. Un foco activo fuera de una zona quemada requiere revisión.
- La captura Sentinel-2 muestra el estado en el momento de adquisición; no es seguimiento en tiempo real.

## Trabajo futuro

Dirección del humo y propagación para mejorar las alertas; refinamiento opcional de contornos con SAM2; despliegue público. El criterio actual de alerta se basa en distancias y **no** predice la evolución del incendio.

**Deuda técnica pendiente.** `_corroborated()` (`active_fire.py`) importa `bare_soil_mask`
dentro de la función: `false_positives` ya toma `potentially_burning` de `active_fire`, así
que al nivel de módulo el import sería circular. El arreglo limpio es mover
`potentially_burning` y las constantes de banda de la SWIR a un módulo común por debajo de
los dos; hasta entonces el import diferido queda anotado en el sitio.

**Límite conocido.** La limpieza morfológica y el área mínima de 30 ha son lo que mantiene el
frente activo fuera de la superficie quemada (ver [ADR-0001](docs/adr/0001-focos-fuera-de-la-cicatriz.md)).
Exentar de ese filtro a las zonas que contienen un foco corroborado admitiría la cicatriz
recién creada, pero redefine *zona* y mueve áreas y alertas: no se ha hecho.
