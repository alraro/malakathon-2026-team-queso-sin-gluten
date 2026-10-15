Hazme una presentación de **4 diapositivas** en español para la final del III Malackathon 2026 (reto de Indra Espacio: detección de incendios con imágenes Sentinel-2). Dura unos **2 minutos**; después viene una demo en vivo de la app. Es una presentación de **puntos clave**: muy poco texto, imágenes grandes, una idea por diapositiva. Te adjunto las imágenes; abajo te digo cuál va en cada una.

## El proyecto

**UNHEAT PROJECT** — equipo **Queso sin Gluten**. A partir de las composiciones JPEG que exporta el Copernicus Browser (SWIR obligatoria; True Color y Wildfires opcionales), la app delimita automáticamente la **superficie quemada** y su **perímetro**, detecta los **focos activos** en el momento de la captura, filtra humo, nubes y suelo desnudo, y con la georreferencia calcula **hectáreas** y qué **poblaciones** están cerca. Sin entrenar ningún modelo: física de las bandas + estadística que se adapta a cada escena.

## Identidad visual (cógela de la propia app, que las capturas se vean en casa)

- **Fondo oscuro cálido**, no negro puro ni azul: `#1d1b18`; paneles/tarjetas `#282521`, líneas `#443f38`.
- Texto `#ede7dc`; texto secundario `#b3a999`.
- **Colores con significado — úsalos solo para lo que significan en el mapa**:
  - Magenta `#ff2bd6` = la marca (el triángulo del logo) y los focos activos. Es el color de acento principal.
  - Ámbar `#e69f00` = superficie quemada (afectado).
  - Granate `#882255` = muy afectado.
  - Cian `#22c7e0` = perímetro.
  - Amarillo → naranja `#ffd34d` / `#ffa600` = niveles de intensidad de los focos.
  - Verde salvia `#9ccb8a` = acento de interfaz/confirmación ("ALTA" confianza, botones).
- **Formas**: el **triángulo** es el motivo gráfico (es el logo y el símbolo de foco activo en el mapa): úsalo como viñeta, separador o marcador, no círculos. Líneas finas tipo contorno cian para enmarcar o subrayar, como el perímetro. Esquinas poco redondeadas (4–6 px).
- **Tipografía**: sans-serif sobria para titulares (tipo Inter/Segoe UI), y **monoespaciada** para cifras y datos técnicos (como la barra superior de la app: `2500×1546 px · SWIR · True Color · Wildfires`). Logo: triángulo magenta + "UNHEAT PROJECT" en mayúsculas con espaciado ancho.
- Estética de herramienta técnica / sala de operaciones, sobria. Nada de llamas de stock, degradados de fuego ni iconos genéricos de satélite: el fuego ya lo ponen las imágenes reales.

## Diapositivas

### 1 · Portada
- Logo UNHEAT PROJECT, grande. Debajo: "Equipo Queso sin Gluten · III Malackathon 2026 · Reto Indra Espacio".
- Frase central: **"Sin entrenar ningún modelo: física de las bandas + estadística que se adapta a cada escena."**
- Imagen de fondo a sangre, oscurecida para que se lea el texto: `08-zoom-focos-activos.jpg`.

### 2 · De tres JPEG a un mapa del incendio
- A la izquierda, las tres entradas como miniaturas apiladas con su etiqueta: `01-entrada-swir.jpg` (SWIR · obligatoria), `02-entrada-truecolor.jpg` (True Color), `03-entrada-wildfires.jpg` (Wildfires).
- Una flecha → a la derecha, grande: `05-despues-resultado-truecolor.jpg`.
- Leyenda mínima con los colores de arriba: ámbar/granate superficie quemada (afectado / muy afectado) · cian perímetro · triángulos focos activos.
- (Alternativa si queda mejor: comparación antes/después con `04-antes-imagen-satelite.jpg` y `05-despues-resultado-truecolor.jpg` lado a lado o con un corte diagonal.)

### 3 · Cómo funciona
Tres pasos en horizontal, cada uno con un triángulo numerado y una línea de texto:
1. **Superficie quemada** — índice NBR dentro de la composición SWIR + umbral Multi-Otsu calculado **para cada escena**.
2. **Falsos positivos fuera** — humo, nubes, agua y suelo desnudo se descartan comparando SWIR y True Color.
3. **Focos activos** — decodificados de la Wildfires en 4 niveles; si no está, estimados desde la SWIR.

Debajo, una franja de imagen: `06-resultado-sobre-swir.jpg` (cómo "ve" el incendio la SWIR).

### 4 · Resultados
- Tres cifras grandes en monoespaciada, cada una con su explicación corta debajo:
  - **100 %** — de los píxeles de foco activo tienen firma de quemado (NBR < 0), en las 3 escenas.
  - **90,9 %** — de los focos activos de Niebla (Huelva) caen sobre la superficie quemada.
  - **3 escenas · 0 retoques** — mismo comando y mismos parámetros en todas.
- Al lado, la captura de la app: `10-app-alertas-poblaciones.jpg` (lista de poblaciones con nivel de alerta y distancia).
- Pie pequeño junto a esa captura: "Guadalajara, escena no incluida en el reto · georreferencia aproximada de ejemplo".
- Cierre en la propia diapositiva: "→ Demo".

## Notas
- Formato 16:9.
- Si alguna captura tiene texto pequeño ilegible al tamaño de la diapositiva, recórtala hacia el mapa antes que reducirla.
- Las imágenes `09-app-resumen-hectareas.jpg`, `07-resultado-sobre-wildfires.jpg`, `11-app-pantalla-subida.jpg` y `12-huelva-resultado.jpg` son de reserva: úsalas solo si mejoran una diapositiva, sin añadir diapositivas nuevas.
