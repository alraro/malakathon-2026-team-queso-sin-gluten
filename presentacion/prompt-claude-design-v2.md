El diseño me gusta: mantén la paleta, el triángulo como motivo, la tipografía y la forma de usar las capturas. Te pido dos cambios de fondo.

**1. Hazla más larga.** Con 4 diapositivas no hay un hilo que seguir. La demo será corta (~1 min), así que la presentación pasa a ser lo principal: **10 diapositivas, unos 4 minutos**, entre 20 y 25 segundos cada una. Abajo tienes la estructura nueva. Reutiliza las diapositivas que ya tienes donde encajen.

**2. Tono informativo, sin frases de gancho.** Quita los eslóganes y las frases de efecto (como «Sin entrenar ningún modelo: física de las bandas + estadística…» usada como lema). Cada diapositiva lleva un **título descriptivo** que diga de qué trata («Superficie quemada», «Focos activos») y, debajo, **datos concretos en viñetas cortas**: qué entra, qué hace, qué sale. Nada de frases para impactar ni de preguntas retóricas. Que suene a informe técnico bien presentado, no a anuncio.

## Estructura nueva

### 1 · Portada
- Logo UNHEAT PROJECT.
- «Detección y caracterización de incendios con imágenes Sentinel-2»
- Equipo Queso sin Gluten · III Malackathon 2026 · Reto Indra Espacio.
- Fondo: `08-zoom-focos-activos.jpg`, oscurecido. Sin lema.

### 2 · El reto
- Delimitar la zona afectada por el incendio y estimar su perímetro.
- Detectar los focos de fuego activo en el momento de la captura y distinguirlos de la superficie ya quemada.
- Evitar falsos positivos: vegetación, suelo desnudo, agua, zonas urbanas, nubes y humo.
- Funcionar en escenas que no se conocen de antemano.
- Imagen: `04-antes-imagen-satelite.jpg` (la escena tal como llega, con el humo visible).

### 3 · Entradas
Tres miniaturas con lo que aporta cada una:
- **SWIR** (obligatoria): bandas B12, B8A y B04. De ella sale la superficie quemada. → `01-entrada-swir.jpg`
- **True Color** (opcional): sirve para descartar humo y nubes. → `02-entrada-truecolor.jpg`
- **Wildfires** (opcional): clasificación de focos activos en 4 niveles del Copernicus Browser. → `03-entrada-wildfires.jpg`
- Nota pequeña: «JPEG exportados del Copernicus Browser, sin coordenadas ni bandas originales».

### 4 · Superficie quemada
- Índice NBR calculado dentro de la composición SWIR: (B8A − B12) / (B8A + B12).
- Umbral Multi-Otsu calculado **para cada escena**, sin un valor fijo.
- Severidad relativa a la escena: afectado / muy afectado.
- Zonas de ≥ 30 ha; perímetro vectorial simplificado.
- Imagen: `06-resultado-sobre-swir.jpg`, con la leyenda de colores (ámbar afectado, granate muy afectado, cian perímetro).

### 5 · Reducción de falsos positivos
- Humo y nubes: se comparan el brillo de True Color y de SWIR (el SWIR atraviesa el humo fino).
- Suelo desnudo, agua y sombras: se descartan por su firma en las bandas de la SWIR.
- Dato: en Niebla (Huelva), el filtro de suelo desnudo deja **2 zonas reales donde antes salían 24**.
- Imagen: `12-huelva-resultado.jpg`.

### 6 · Focos activos
- Con Wildfires: se decodifican sus colores en 4 niveles de intensidad (confianza alta).
- Se descartan los focos que la SWIR no respalda (firma de suelo brillante, no de fuego).
- Sin Wildfires: estimación desde la SWIR, marcada como confianza baja.
- Se representan aparte de la superficie quemada: triángulos de amarillo a naranja según el nivel.
- Imagen: `08-zoom-focos-activos.jpg`.

### 7 · Georreferencia e impacto
- Coordenadas manuales, GeoTIFF, o encaje arrastrando la imagen sobre el mapa.
- Con ellas: hectáreas, km de perímetro y poblaciones cercanas (dataset GeoNames).
- Niveles de alerta por distancia: **alta** (dentro del perímetro o < 2 km de un foco) · **media** (< 5 km) · **vigilancia** (< 10 km).
- Imagen: `10-app-alertas-poblaciones.jpg`. Pie: «Guadalajara · georreferencia aproximada de ejemplo».

### 8 · La aplicación
- Web: se suben las composiciones, se cambia el fondo, se encienden y apagan capas, y se consultan zonas y poblaciones.
- Cada resultado indica su nivel de confianza según las composiciones aportadas.
- CLI y API con salida JSON documentada; arranque con `docker compose up`.
- Imagen: `09-app-resumen-hectareas.jpg` (o `11-app-pantalla-subida.jpg` en pequeño al lado).

### 9 · Resultados
Las tres cifras grandes que ya tenías, con su explicación debajo:
- **100 %** de los píxeles de foco activo tienen firma de quemado (NBR < 0), en las 3 escenas.
- **90,9 %** de los focos activos de Niebla caen sobre la superficie quemada.
- **3 escenas · 0 retoques**: mismo comando y mismos parámetros en todas, incluida Guadalajara, que no venía en el reto.
- Imagen de apoyo: `05-despues-resultado-truecolor.jpg`.

### 10 · Siguientes pasos → Demo
- Dirección del humo y propagación para afinar las alertas.
- Con datos multiespectrales originales: banda B11 e imagen anterior al incendio (dNBR).
- Despliegue público.
- Cierre: «Demo» en grande, sin frase final.

## Se mantiene
- 16:9, fondo oscuro cálido y colores con significado: magenta para la marca y los focos, ámbar y granate para lo quemado, cian para el perímetro.
- Cifras y datos técnicos en monoespaciada.
- Poco texto por diapositiva: 3 o 4 viñetas cortas como máximo, y la imagen grande.
