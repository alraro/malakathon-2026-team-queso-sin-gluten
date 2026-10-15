Mantén el diseño, la paleta, el tono informativo y las imágenes. Aplica estos cambios de contenido; la presentación pasa a tener **11 diapositivas** con este orden:

1 Portada · 2 El reto · 3 Entradas · 4 Superficie quemada · 5 Falsos positivos · 6 Focos activos · 7 Georreferencia · 8 Hectáreas y riesgo · 9 Generalización (nueva) · 10 Validación · 11 Conclusiones

La diapositiva «La aplicación» desaparece como tal; su contenido se reparte entre la 2 y la 7–8.

---

### 2 · El reto — añadir
Una cuarta viñeta al mismo nivel que las demás:
- **Pensado para cualquier usuario**: el resultado se lee sin saber de satélites (zonas, focos, hectáreas y poblaciones en lenguaje claro, con nivel de confianza en cada dato).

### 3 · Entradas — completar qué discrimina cada composición
- **SWIR** (obligatoria, B12 · B8A · B04): superficie quemada, y también descarta **agua y sombras** (muy oscuras en las tres bandas), **vegetación** y **suelo desnudo o urbano** (brillante en el infrarrojo cercano).
- **True Color** (opcional): descarta **humo** (brillante en el visible pero no en la SWIR, que lo atraviesa) y **nubes** (brillantes en las dos).
- **Wildfires** (opcional): focos activos en 4 niveles.

### 4 · Superficie quemada — reescribir
- Índice **NBR** = (B8A − B12) / (B8A + B12), calculado en cada píxel de la SWIR.
- Valores orientativos de NBR (el corte exacto se calcula en cada escena):
  - **Vegetación sana**: NBR positivo, ≈ +0,35 a +0,6.
  - **Afectado**: NBR por debajo de ≈ −0,05 (Huelva −0,05 · Guadalajara −0,07).
  - **Muy afectado**: NBR por debajo de ≈ −0,16 a −0,22 (Huelva −0,16 · Guadalajara −0,22).
- **Primera segmentación** (Multi-Otsu de 4 clases sobre toda la escena): separa lo quemado del resto.
- **Severidad relativa**: sobre los píxeles ya quemados se aplica una **segunda segmentación** (Otsu de 2 clases) que los divide en **afectado** y **muy afectado**. Es relativa a la escena: «muy afectado» es lo más quemado de esa imagen.
- Se conservan solo las **áreas suficientemente grandes**, y su contorno se dibuja como **perímetro simplificado** (algoritmo Douglas–Peucker).
- Quita la mención «≥ 30 ha». Si cabe, muestra los valores de NBR como una barra horizontal de −1 a +1 con los tramos coloreados (granate · ámbar · gris · verde).

### 5 · Reducción de falsos positivos — añadir
- Añadir **vegetación**: se descarta el píxel con índice de vegetación (B8A − B04)/(B8A + B04) > 0,6.
- Añadir la idea de fondo: **cada filtro es una máscara de píxeles** (agua y sombra, vegetación, suelo desnudo, humo, nube). La superficie quemada final es «NBR bajo» **menos** la unión de todas esas máscaras.
- Si encaja, un pequeño esquema: máscara NBR − máscaras de descarte = superficie quemada.

### 6 · Focos activos — formato y una viñeta nueva
- Poner en negrita el comienzo: «**Con Wildfires:** …» y «**Sin Wildfires:** …».
- Nueva viñeta: **Bajo nubes**: si la True Color detecta nubes, la Wildfires puede ocultar focos bajo ellas, así que en esas zonas también se buscan con la SWIR y se combinan ambas detecciones.

### 7 · Georreferencia (nueva redacción; antes «Georreferencia e impacto»)
Título: «Situar la escena en el mapa». Los JPEG no traen coordenadas; hay tres formas de dárselas:
- **Coordenadas**: norte, sur, este y oeste en grados.
- **GeoTIFF**: se exporta del Copernicus Browser y las coordenadas se leen solas.
- **Encaje manual**: se arrastra y estira la imagen semitransparente sobre el mapa hasta que coincide con el terreno.
- Imagen: `11-app-pantalla-subida.jpg` (o `09-app-resumen-hectareas.jpg`, recortada al mapa).

### 8 · Hectáreas y riesgo (nueva; antes «La aplicación»)
Título: «Medir el impacto». Con la escena situada:
- **Hectáreas** de cada zona (el área de cada píxel se corrige por latitud) y **kilómetros** de perímetro.
- **Proximidad a poblaciones** (GeoNames) para medir el riesgo:
  - **Alta**: dentro del perímetro o a menos de 2 km de un foco.
  - **Media**: a menos de 5 km.
  - **Vigilancia**: a menos de 10 km.
- Imagen: `10-app-alertas-poblaciones.jpg`. Pie: «Guadalajara · georreferencia aproximada de ejemplo».

### 9 · Generalización (diapositiva NUEVA, antes de la validación)
Título: «Una escena que no venía en el reto».
- El reto entregó Ávila-Madrid y Niebla (Huelva); esta escena no estaba en el conjunto original.
- Mismo comando y mismos parámetros, sin retocar nada para esta escena.
- **Deja un hueco grande para una imagen (antes / después) que añadiré yo**, con 2 o 3 cifras de resultado debajo como marcador de posición: `[zonas] · [focos] · [ha]`.

### 10 · Validación (sustituye a «Resultados»)
Título: «Validación». Fuera las cifras de «focos dentro del área» como titulares.
- **Deja la estructura preparada y las cifras como marcadores de posición**; las mediremos comparando la predicción con un etiquetado manual y te las pasaré después.
- Estructura: dos bloques en paralelo, **Superficie quemada** y **Focos activos**, cada uno con 3 cifras grandes en monoespaciada: `Precisión [ ]` · `Exhaustividad [ ]` · `F1 [ ]` (en superficie quemada, también `IoU [ ]`).
- Debajo, una línea fija: **Estabilidad del área**: mover el umbral NBR ±0,02 cambia el área quemada solo **±3,5 %** en las 3 escenas.
- Pie pequeño: «Referencia: etiquetado manual del equipo sobre [escenas]».

### 11 · Conclusiones (sustituye a «Siguientes pasos»)
- Delimitación automática de superficie quemada, severidad y focos activos a partir de JPEG del Copernicus Browser, sin entrenar modelos y con el umbral adaptado a cada escena.
- Filtros por máscaras para humo, nubes, agua, vegetación y suelo desnudo.
- Del píxel al impacto: hectáreas y poblaciones en riesgo.
- **Con más datos, mejor**: la banda **B11** completaría la detección de focos (hoy solo es completa con la Wildfires), y los **GeoTIFF** con bandas originales darían coordenadas exactas, reflectancias reales e imagen previa al incendio (severidad absoluta, dNBR).
- Cierre: «Demo».

---

## Referencias (discretas, a pie de diapositiva)

Añade las fuentes **en letra pequeña (≈ 9–10 pt), color de texto secundario `#b3a999`, alineadas abajo a la izquierda**, en formato corto «Autor (año)». Que no compitan con el contenido. Solo en estas diapositivas:

- **3 · Entradas**: Sentinel Hub custom scripts, *SWIR composite* y *QuickFire v1.0.0* (P. Markuse, 2022).
- **4 · Superficie quemada**: Key & Benson (2006), *Landscape Assessment*, FIREMON RMRS-GTR-164 · Otsu (1979), IEEE Trans. SMC 9(1) · Liao, Chen & Chung (2001), *multilevel Otsu*, J. Inf. Sci. Eng. 17 · Douglas & Peucker (1973), *Cartographica* 10(2).
- **5 · Falsos positivos**: Rouse et al. (1974), NDVI.
- **6 · Focos activos**: Murphy et al. (2016), HOTMAP, *Remote Sens. Environ.* 177 · Markuse (2022), QuickFire v1.0.0.
- **8 · Medir el impacto**: GeoNames (CC BY 4.0) · EFFIS, *Rapid Damage Assessment*.
- **11 · Conclusiones**: EFFIS, *Fire Severity* (clases dNBR).
