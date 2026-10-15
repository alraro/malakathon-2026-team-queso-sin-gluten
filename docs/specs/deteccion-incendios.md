# Spec: Detección y caracterización de incendios sobre composiciones Sentinel-2

> Vocabulario según `CONTEXT.md` (términos en español; identificadores en inglés entre paréntesis). Base técnica en `docs/research/sentinel2-rgb-fire-sota.md`.

## Problem Statement

Durante un incendio forestal, quien tiene acceso a imágenes Sentinel-2 descargadas del Copernicus Browser (técnicos de emergencias, periodistas, ayuntamientos, ciudadanos) recibe JPEG renderizados —una composición SWIR, a veces una True Color y a veces una Wildfires— que no saben interpretar. No pueden distinguir a simple vista qué terreno ha ardido, dónde sigue habiendo fuego en el momento de la toma, qué parte es humo o nube, cuántas hectáreas hay afectadas ni qué poblaciones están cerca. Las herramientas profesionales (SIG, índices espectrales, productos multibanda) exigen conocimientos y datos que no tienen; y los propios JPEG no incluyen coordenadas ni escala.

Además, para el reto (Indra Espacio, Malackathon 2026), la solución debe funcionar automáticamente sobre escenas no vistas, reducir falsos positivos (humo, nubes, agua, suelo desnudo, zonas urbanas) y representar claramente el perímetro de la zona afectada y los focos activos sobre una de las imágenes originales.

## Solution

Una aplicación web sencilla, en español, donde el usuario sube las composiciones de una escena (SWIR obligatoria; True Color y Wildfires opcionales) y obtiene en segundos:

- La **superficie quemada** (`burned_area`) dividida en **zonas** (`zone`), con su **perímetro** (`perimeter`) dibujado sobre la imagen y una **severidad relativa** (`relative_severity`) en dos tonos.
- Los **focos activos** (`active_fire`) diferenciados visualmente de la superficie quemada, con su nivel de intensidad.
- Al pasar el ratón sobre una zona, un resalte y una tarjeta con su área, el % que representa del total quemado, sus focos activos y la población más cercana.
- Un resumen global con cifras, **confianza** (`confidence`) según las composiciones aportadas y un texto legible por lectores de pantalla.
- Opcionalmente, si el usuario aporta la **georreferencia** (`georeference`) —encajando la imagen sobre un mapa, escribiendo el bbox o subiendo un GeoTIFF—, las cifras pasan a hectáreas y kilómetros y aparece la lista de **poblaciones** (`settlement`) cercanas con su **alerta** (`alert`).

El mismo motor se expone como comando de línea para que el jurado lo ejecute sobre escenas nuevas, y todo se arranca con un único comando Docker.

## User Stories

### Subida de la escena

1. Como usuario, quiero subir la composición SWIR en una casilla claramente etiquetada, para que la herramienta sepa qué imagen es sin depender del nombre del archivo.
2. Como usuario, quiero poder subir opcionalmente la composición True Color en su propia casilla, para mejorar el descarte de humo y nubes.
3. Como usuario, quiero poder subir opcionalmente la composición Wildfires en su propia casilla, para obtener focos activos más fiables.
4. Como usuario, quiero que la herramienta funcione solo con la SWIR, para poder analizar escenas donde no tengo las otras composiciones.
5. Como usuario, quiero un mensaje claro si las composiciones tienen tamaños distintos, para entender por qué no se pueden analizar juntas.
6. Como usuario, quiero un mensaje claro si falta la SWIR o el archivo no es una imagen válida, para corregirlo sin adivinar.
7. Como usuario, quiero ver una indicación de progreso mientras se analiza la escena, para saber que la herramienta está trabajando.
8. Como usuario con imágenes grandes (p. ej. ~10 000 × 6 000 px), quiero que el análisis termine en un tiempo razonable y que la web siga siendo fluida, para poder usar exportaciones de alta resolución.

### Superficie quemada y zonas

9. Como usuario, quiero ver la superficie quemada pintada en semitransparencia sobre la imagen original, para distinguirla claramente del resto del territorio.
10. Como usuario, quiero ver el perímetro de cada zona dibujado como una línea, para identificar su contorno de un vistazo.
11. Como usuario, quiero que cada mancha quemada separada sea una zona independiente, para poder distinguir incendios distintos en la misma escena.
12. Como usuario, quiero que las manchas muy pequeñas (por debajo de ~30 ha o su equivalente en píxeles) no aparezcan como zonas, para no ver ruido como si fuera incendio.
13. Como usuario, quiero que el humo no se marque como superficie quemada, para no sobrestimar el incendio.
14. Como usuario, quiero que las nubes no se marquen como superficie quemada, para no sobrestimar el incendio.
15. Como usuario, quiero que el agua, las sombras y las zonas urbanas no se marquen como superficie quemada, para confiar en el resultado.
16. Como usuario, quiero ver dentro de la superficie quemada dos tonos ("afectado" / "muy afectado"), para entender qué partes ardieron con más intensidad.
17. Como usuario, quiero que se me aclare que la severidad es relativa a la escena, para no compararla erróneamente con otras escenas.
18. Como evaluador, quiero que los umbrales se calculen automáticamente para cada escena, para que la solución generalice a imágenes que no ha visto.

### Focos activos

19. Como usuario, quiero ver los focos activos con un color y una forma distintos a la superficie quemada, para diferenciar lo que arde ahora de lo que ya ardió.
20. Como usuario, quiero que cada foco activo indique su nivel de intensidad (1–4), para priorizar los más intensos.
21. Como usuario que ha subido la Wildfires, quiero que los focos activos se obtengan de ella y se marquen con confianza alta, para tener el resultado más fiable posible.
22. Como usuario sin Wildfires, quiero obtener igualmente focos activos a partir de la SWIR, marcados con confianza baja, para tener una estimación en vez de nada.
23. Como usuario, quiero un aviso cuando haya nubes que puedan ocultar focos en la Wildfires, para no dar por hecho que no hay fuego bajo ellas.
24. Como usuario, quiero saber de qué fuente sale cada foco (Wildfires o SWIR), para valorar su fiabilidad.
25. Como usuario, quiero que se me avise si aparecen focos fuera de la superficie quemada, para revisar si es un frente que avanza o un error.

### Interacción

26. Como usuario, quiero que al pasar el ratón sobre una zona esta se resalte, para ver claramente qué estoy señalando.
27. Como usuario, quiero que al pasar el ratón sobre una zona aparezca una tarjeta con su área, el % del total quemado, su número de focos activos y la población más cercana, para entenderla sin cálculos.
28. Como usuario, quiero cambiar la imagen de fondo entre las composiciones subidas, para ver el resultado sobre la que mejor entienda.
29. Como usuario, quiero que por defecto el resultado se muestre sobre la True Color si la he subido (si no, sobre la SWIR), para ver el terreno en colores naturales.
30. Como usuario, quiero activar y desactivar las capas (superficie quemada, severidad, perímetro, focos activos), para inspeccionar cada una por separado.
31. Como usuario, quiero hacer zoom y desplazarme por la imagen, para examinar detalles de zonas grandes.
32. Como usuario, quiero ver un panel con la lista de zonas, para recorrerlas sin buscarlas en la imagen.
33. Como usuario de teclado, quiero poder navegar entre las zonas con el teclado y ver su tarjeta, para usar la herramienta sin ratón.

### Resumen y cifras

34. Como usuario, quiero un resumen global con la superficie quemada total, el número de zonas y el número de focos activos, para hacerme una idea rápida del incendio.
35. Como usuario sin georreferencia, quiero ver las cifras en píxeles y porcentajes, para entender las proporciones aunque no haya escala.
36. Como usuario sin georreferencia, quiero que las hectáreas y las poblaciones aparezcan como "no disponibles" con una explicación de cómo obtenerlas, para no recibir cifras inventadas.
37. Como usuario, quiero ver qué parte del área dentro del perímetro está realmente quemada, para entender que quedan islas sin quemar.
38. Como usuario, quiero que la longitud del perímetro se muestre junto a la tolerancia de simplificación usada, para no malinterpretar una cifra que depende de ella.
39. Como usuario, quiero ver el nivel de confianza de la superficie quemada y de los focos activos, para saber cuánto fiarme de cada resultado.
40. Como usuario de lector de pantalla, quiero un resumen en texto ("Se han detectado 2 zonas quemadas, unas 12 400 ha…"), para acceder al resultado sin ver la imagen.
41. Como usuario daltónico, quiero que los colores distingan superficie quemada, severidad y focos sin depender de rojo frente a verde, para leer el mapa correctamente.
42. Como usuario, quiero que todas las cifras lleven su unidad y su supuesto (p. ej. "calculado con el bbox aportado"), para entender de dónde salen.

### Georreferencia

43. Como usuario, quiero encajar la imagen sobre un mapa real moviéndola y estirándola en semitransparencia hasta que coincidan ríos y carreteras, para georreferenciarla sin saber coordenadas.
44. Como usuario técnico, quiero escribir el bbox (norte, sur, este, oeste), para georreferenciar con precisión si ya lo conozco.
45. Como usuario técnico, quiero subir un GeoTIFF exportado del Copernicus Browser y que se lean sus coordenadas, para obtener una georreferencia exacta.
46. Como usuario, quiero poder continuar sin georreferencia, para ver la segmentación aunque no sepa dónde está la imagen.
47. Como usuario, quiero que tras georreferenciar las cifras se recalculen en hectáreas y kilómetros, para conocer la magnitud real del incendio.
48. Como usuario georreferenciado, quiero ver las zonas y focos sobre un mapa base, para situarlos respecto a carreteras y núcleos.

### Poblaciones y alertas

49. Como usuario georreferenciado, quiero ver una lista de poblaciones cercanas al incendio, para saber a quién puede afectar.
50. Como usuario, quiero que cada población tenga un nivel de alerta (alta / media / vigilancia), para priorizar avisos.
51. Como usuario, quiero que una población dentro del perímetro o a menos de 2 km de un foco activo tenga alerta alta, para identificar los casos más urgentes.
52. Como usuario, quiero que una población a menos de 5 km tenga alerta media y a menos de 10 km alerta de vigilancia, para tener una escala clara.
53. Como usuario, quiero que la lista se ordene por distancia y muestre los habitantes, para valorar el impacto potencial.
54. Como usuario, quiero que se indique si la distancia es al foco activo o a la superficie quemada, para entender el motivo de la alerta.
55. Como usuario de otro país, quiero que el dataset de poblaciones sea intercambiable por país, para usar la herramienta fuera de España.
56. Como usuario, quiero que las distancias de alerta sean configurables y se explique que son un criterio por distancia, para no confundirlo con un modelo de propagación.

### Línea de comandos y operación

57. Como evaluador, quiero ejecutar el análisis desde línea de comandos indicando las composiciones y, opcionalmente, el bbox, para probar la solución en escenas nuevas sin la web.
58. Como evaluador, quiero que la línea de comandos genere el JSON de resultado y una imagen con el resultado pintado, para revisar el resultado sin herramientas adicionales.
59. Como evaluador, quiero arrancar toda la aplicación con un único comando Docker, para no tener que instalar dependencias.
60. Como evaluador, quiero un README que explique el método y sus límites (sin B11, sin imagen pre-incendio, sin escala en el JPEG), para valorar las decisiones técnicas.
61. Como desarrollador del frontend, quiero un JSON de ejemplo con el contrato de salida desde el inicio, para construir la web en paralelo al motor.
62. Como equipo, quiero ver métricas de autoconsistencia (focos dentro de la superficie quemada, acuerdo del detector SWIR con la Wildfires, estabilidad del área ante variaciones de umbral), para justificar la calidad sin ground truth.
63. Como equipo, quiero comparar el perímetro de Huelva con el producto Copernicus EMS EMSR913, para presentar una validación externa.

## Implementation Decisions

### Arquitectura y módulos

- **Motor de análisis de escena (Python, numpy + scikit-image/scipy)**: módulo profundo con una única interfaz pública: recibe las composiciones (`swir` obligatoria; `true_color` y `wildfires` opcionales) como arrays RGB de 8 bits, una georreferencia opcional y opcionalmente un dataset de poblaciones y parámetros de alerta; devuelve el resultado conforme al contrato JSON. Todo lo demás es interno.
- Submódulos internos del motor (no expuestos como seams de test):
  - **Superficie quemada**: NBR calculado dentro de la composición SWIR, `(G − R)/(G + R)` (la ganancia 2.5 se cancela). Umbral adaptativo por escena: la superficie quemada es la clase inferior de un multi-Otsu de **4** clases sobre el histograma del NBR, con tope en NBR < 0 (con 3 clases el corte quedaba en NBR ≈ 0–0,07 y se llevaba el 27–35 % de Huelva y Madrid-Ávila: cultivos y suelo); dentro de lo quemado, un Otsu de 2 clases separa afectado / muy afectado (severidad relativa). Se rellenan islas sin quemar < ~3 ha. Limpieza morfológica (apertura, cierre, eliminación de objetos y huecos pequeños). Componentes conexas → zonas; se descartan las menores que el área mínima (~30 ha si hay escala; si no, un umbral en píxeles equivalente asumiendo ~20 m/px).
  - **Rechazo de falsos positivos**: con True Color, discriminador de humo `D = z(mean(TC)) − z(mean(SWIR))` (humo ≈ +2, nube ≈ −0.5) y test de nube (brillante en ambas composiciones); NDVI-proxy `(G − B)/(G + B)` de la SWIR para vegetación; brillo bajo para agua/sombra. Sin True Color, solo los criterios internos de la SWIR.
  - **Perímetro**: `find_contours` sobre la máscara limpia + simplificación Douglas–Peucker; la tolerancia se reporta junto a la longitud.
  - **Focos activos**: si hay Wildfires, decodificación de la firma de QuickFire (R alto, R − B grande) y del nivel 1–4 por el canal verde; fuente `wildfires`, confianza alta. Si no, detector "Murphy-partial" sobre la SWIR (B12 saturado, `B12/B8A ≥ 1.4`, `B12 ≥ 0.15`, crecimiento 3×3), fuente `swir`, confianza baja. En zonas que la Wildfires marca como nube, también se ejecuta el detector SWIR y se emite un aviso.
  - **Georreferencia**: bbox (lon/lat) → posición de cada píxel interpolando en Web Mercator; área por píxel corregida por latitud; metros/píxel derivado. Si llega un GeoTIFF, se lee su geotransform.
  - **Poblaciones y alertas**: dataset GeoNames local por país (nombre, lon/lat, habitantes), cargado una vez; distancia geodésica de cada población a la superficie quemada y a los focos activos; niveles `high` (dentro del perímetro o < 2 km de foco activo), `medium` (< 5 km), `watch` (< 10 km); distancias configurables.
  - **Render de capas**: máscaras PNG (superficie quemada, severidad, focos activos) y una vista previa con el resultado pintado; para la web se reducen a ≤ ~2500 px de lado. El análisis y todas las cifras se calculan a resolución completa.
- **CLI**: envoltorio fino del motor: rutas a las composiciones, bbox opcional y directorio de salida → JSON de resultado + PNG.
- **API HTTP (FastAPI)**: envoltorio fino del motor: endpoint de análisis que recibe las composiciones (multipart) y la georreferencia opcional y devuelve el JSON; sirve las capas generadas y el frontend estático. Errores de validación (falta la SWIR, tamaños distintos, archivo no válido) con mensaje claro en español.
- **Frontend**: HTML + JS sin framework + Leaflet. Las piezas (subida, visor/mapa, panel de zonas, resumen, georreferencia, alertas) van en ficheros JS separados. Sin georreferencia, Leaflet trabaja en coordenadas de píxel (CRS simple); con ella, sobre mapa base. El encaje sobre mapa es un overlay semitransparente movible/escalable cuyo resultado es un bbox.
- **Empaquetado**: imagen Docker única con un solo comando de arranque; dependencias fijadas.

### Contrato de salida del motor

El contrato se acordó explícitamente y encapsula la decisión de forma más precisa que la prosa:

```json
{
  "scene": {
    "width": 2500, "height": 1546,
    "composites": ["swir", "true_color", "wildfires"],
    "georeference": { "bbox": [lon_min, lat_min, lon_max, lat_max], "source": "map_fit|manual|geotiff" } | null,
    "metres_per_pixel": 18.2 | null
  },
  "summary": {
    "burned_area_px": 0, "burned_area_ha": null,
    "perimeter_enclosed_ha": null, "perimeter_km": null, "perimeter_tolerance_m": null,
    "zone_count": 2, "active_fire_count": 14,
    "confidence": { "burned_area": "high|low", "active_fire": "high|low" },
    "warnings": []
  },
  "zones": { "type": "FeatureCollection", "features": [{
    "geometry": "<perimeter polygon, pixel coords>",
    "properties": { "id": 1, "area_px": 0, "area_ha": null, "share_of_burned": 0.85,
                    "relative_severity": { "affected": 0.6, "severely_affected": 0.4 },
                    "active_fire_count": 3, "nearest_settlement": null,
                    "geo_geometry": "<lon/lat polygon> | null" } }] },
  "active_fires": { "type": "FeatureCollection", "features": [{
    "properties": { "level": 1, "source": "wildfires|swir", "zone_id": 1 } }] },
  "alerts": [{ "settlement": "…", "population": 0, "distance_km": 3.2,
               "level": "high|medium|watch", "nearest_to": "active_fire|burned_area" }],
  "layers": { "burned_mask": "…png", "severity_mask": "…png",
              "active_fire_mask": "…png", "preview": "…png" }
}
```

- Las geometrías van siempre en coordenadas de píxel; las versiones lon/lat solo cuando hay georreferencia.
- Sin georreferencia: todos los campos en hectáreas/km y `alerts` quedan `null`/vacíos, nunca estimados.
- El primer entregable es un JSON de ejemplo conforme a este contrato, para desbloquear el frontend.

### Otras decisiones

- Identificadores de código y del JSON en inglés; interfaz de usuario en español.
- Solo la composición SWIR es obligatoria; cada composición opcional mejora un aspecto concreto y la confianza lo refleja.
- Las composiciones se identifican por la casilla en que se suben, nunca por el nombre del archivo.
- Accesibilidad con esfuerzo moderado: paleta apta para daltonismo, forma distinta para los focos, resumen en texto accesible, navegación de zonas con teclado, cifras siempre con unidad y supuesto.

## Testing Decisions

- **Qué es un buen test**: comprueba comportamiento externo a través de la interfaz pública (composiciones + georreferencia → JSON de resultado), nunca funciones internas (NBR, umbral, morfología). Los tests deben sobrevivir a un cambio completo del algoritmo interno mientras el resultado siga siendo correcto.
- **Seam principal — motor de análisis de escena**:
  - *Escenas reales de `data/`*: Huelva y Guadalajara producen ≥ 1 zona; sus focos activos tienen fuente `wildfires` y confianza alta; > 90 % de los focos activos cae dentro de la superficie quemada; la fracción de la superficie quemada que cumple el test de humo o nube es casi nula. Madrid-Ávila (sin Wildfires, 9930 × 6141) produce focos con confianza baja y no falla.
  - *Imágenes sintéticas pequeñas generadas en el test*: un parche con firma de quemado sobre fondo con firma de vegetación produce exactamente una zona con el área esperada; una mancha bajo el área mínima se descarta; dos parches separados producen dos zonas; sin georreferencia, los campos en hectáreas son `null`; con un bbox conocido, el área en hectáreas cae dentro de una tolerancia; un parche con firma de humo no aparece como quemado cuando se aporta True Color.
  - *Alertas*: un dataset de poblaciones inventado con tres poblaciones a distancias conocidas produce los niveles `high`, `medium` y `watch` esperados, ordenados por distancia.
  - *Contrato*: todo resultado valida contra el esquema del JSON acordado.
- **Seam secundario — API HTTP**: un test de humo con el cliente de pruebas de FastAPI: subir solo la SWIR devuelve un JSON válido; composiciones de tamaños distintos devuelven un error claro.
- **No se testea automáticamente**: el frontend (revisión manual en la demo) ni los internos del motor.
- **Prior art**: ninguno; el repositorio aún no tiene código ni tests. Las métricas de autoconsistencia de `docs/research/sentinel2-rgb-fire-sota.md` §5.4 sirven de referencia para las aserciones sobre escenas reales.

## Out of Scope

- Segmentación aprendida (U-Net, entrenamiento propio) y modelos fundacionales geoespaciales (Prithvi, Clay…).
- Refinamiento con SAM/SAM2 (posible trabajo futuro).
- Cualquier método que requiera B11, bandas red-edge o una imagen pre-incendio (dNBR, NBR2, BAIS2, MIRBI, clases de severidad absolutas).
- Dirección del humo y modelo de propagación del incendio para las alertas (documentado como mejora futura del criterio de alerta).
- Despliegue público en internet.
- Validación píxel a píxel contra ground truth (solo presencia/ubicación y comparación con EMSR913).
- Inferir la escala o la ubicación desde el propio JPEG.

## Further Notes

- Plazo: ~8 h restantes de hackathon, 4 personas con agentes de IA. Orden de prioridad: (1) motor de superficie quemada + CLI, (2) focos activos, (3) API + web con resalte al pasar el ratón, (4) georreferencia, (5) poblaciones y alertas, (6) validación y presentación. El JSON de ejemplo permite trabajar en (1) y (3) en paralelo desde el inicio.
- Las cifras de área mid-evento serán menores que las finales publicadas de cada incendio; es lo esperado, no un error.
- Pregunta abierta para quien tenga tiempo: la definición exacta de las capas built-in de Copernicus Browser (gamma ≈ 2.2 entre True Color y SWIR). El método evita depender de ella usando solo diferencias normalizadas dentro de la SWIR.
- Dependencias a instalar al inicio: numpy, scipy, scikit-image, shapely, fastapi, uvicorn, pillow; PIL necesita desactivar el límite de píxeles para Madrid-Ávila.
