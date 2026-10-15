# Brief de diseño: interfaz de Unheat Project

> Documento autocontenido para pedir el diseño visual a Claude Design. Describe **qué** debe tener la interfaz, sus pantallas, estados, datos y restricciones; el **cómo se ve** (paleta, tipografía, detalle visual) es trabajo del diseño, dentro de las restricciones de aquí. Vocabulario según `CONTEXT.md`.

## 1. Producto

**Unheat Project** es una aplicación web, en español, que analiza imágenes Sentinel‑2 de un incendio forestal ya descargadas del Copernicus Browser como JPEG. El usuario sube las **composiciones** de una **escena** y obtiene:

- la **superficie quemada**, dividida en **zonas** con su **perímetro** y una **severidad relativa** en dos tonos (afectado / muy afectado);
- los **focos activos**: fuego ardiendo en el momento de la imagen, con nivel de intensidad 1–4;
- cifras globales y por zona, cada una con su **confianza** y su procedencia;
- si la escena está **georreferenciada**: hectáreas, kilómetros y la lista de **poblaciones** cercanas con su **alerta** (alta / media / vigilancia).

Contexto: Malackathon 2026, reto de Indra Espacio. Se presentará en un proyector delante de un jurado.

### Usuario principal

Un **técnico de emergencias** que necesita leer la situación de un vistazo y fiarse de las cifras. La estética es de **sala de operaciones**: seria, densa en información pero ordenada, sin adornos. Tiene que verse como una herramienta real y no como un prototipo, y ser legible en un proyector a 1920×1080.

### Principio rector: nunca fingir un dato

La aplicación nunca inventa ni estima una cifra que no tiene. Si falta algo (p. ej. hectáreas sin georreferencia), se muestra como **«no disponible»** y se dice cómo obtenerlo. Toda cifra lleva su unidad y la procedencia de la que depende. El diseño debe hacer visible esta honestidad, no esconderla.

## 2. Restricciones técnicas (obligatorias)

- **HTML + CSS + JavaScript sin framework.** Nada de React, Vue, Tailwind ni librerías de componentes. El diseño debe poder implementarse como HTML semántico con CSS propio.
- **CSS con variables (tokens)** en `:root` para colores, tipografía, espaciado, radios y sombras.
- **Leaflet** es el visor de mapa y se mantiene. Los controles propios se superponen al mapa como elementos HTML. Los estilos de las capas (polígonos, líneas y marcadores) se definen como colores y trazos que Leaflet aplica.
- **Sin dependencias externas** salvo el mapa base topográfico OpenTopoMap, que solo aparece con la escena georreferenciada o durante el encaje. Las fuentes deben poder servirse localmente o ser fuentes de sistema; nada de CDN obligatorio.
- **Escritorio primero**: diseñar para 1440×900 y 1920×1080. Por debajo de ~1024 px basta con que no se rompa (paneles apilados); no hace falta un diseño móvil propio.
- **Dos temas**, oscuro (por defecto) y claro, con un interruptor visible y respetando `prefers-color-scheme` en la primera visita. El claro es el seguro para proyectores que apagan los oscuros.

## 3. Flujo general

Dos fases y un estado intermedio:

```
Nueva escena ──(Analizar)──► Análisis en curso ──► Espacio de trabajo
     ▲                                                   │
     └──────────────────(Nueva escena)───────────────────┘
                                                         │
                            Espacio de trabajo ◄──► Modo encaje ──(Listo)──► Análisis en curso ──► Espacio de trabajo
```

No hay ejemplo precargado, escenas de muestra, cuentas de usuario ni historial: la app hace una cosa y la hace bien.

## 4. Pantalla «Nueva escena»

Pantalla de entrada, centrada sobre un fondo sobrio.

- **Marca** Unheat Project y una línea de presentación: «Sube las composiciones Sentinel‑2 de una escena y mira qué ha ardido y dónde sigue habiendo fuego.»
- **Tres tarjetas de composición** en fila. Cada una es zona de arrastrar y soltar y también selector de archivo con clic. La composición se identifica **por la tarjeta** en que se sube, nunca por el nombre del archivo.

  | Tarjeta | Estado | Qué aporta (una línea) |
  | --- | --- | --- |
  | SWIR | **Obligatoria** | De ella sale la superficie quemada. |
  | True Color | Opcional | Descarta humo y nubes; es el fondo más natural. |
  | Wildfires | Opcional | Da los focos activos con su nivel y confianza alta. |

  Estados de cada tarjeta: vacía, arrastrando encima, cargada (miniatura local del JPEG, nombre del archivo, tamaño en MB y acción «Quitar»), con error (p. ej. «No es una imagen válida»). La SWIR se distingue visualmente como obligatoria.

- **Sección plegada «Ubicación (opcional)»**, cerrada por defecto para que el camino mínimo sea SWIR → Analizar. Al abrirla, dos pestañas:
  - **Archivo GeoTIFF**: un selector de archivo `.tif`. Texto: sus coordenadas se leen solas. Al analizar se envía solo la ubicación de la pestaña activa (y ninguna si la sección está plegada), así que nunca compiten con las coordenadas escritas.
  - **Coordenadas**: cuatro campos numéricos WGS84, Norte, Sur, Este y Oeste, dispuestos como una rosa o un recuadro que sugiera los bordes. Texto: los JPEG no traen coordenadas; sin ellas también se puede analizar y situar la escena en el mapa después.
- **Botón principal «Analizar escena»**, deshabilitado hasta que haya SWIR.
- **Errores**: los de un campo, en línea en su tarjeta o campo. Los del servidor, en un bloque encima del botón. Errores reales que existen:
  - «Falta la composición SWIR: es la única obligatoria.»
  - Archivo no válido o que no es imagen.
  - Composiciones de tamaños distintos (no se pueden analizar juntas).
  - Coordenadas incoherentes (p. ej. norte menor que sur).
  - «No se ha podido conectar con el servidor.»
- **Pie** discreto con los créditos: Copernicus Sentinel‑2, datos de poblaciones de GeoNames (CC BY 4.0), OpenTopoMap y colaboradores de OpenStreetMap.

## 5. Estado «Análisis en curso»

Superposición a pantalla completa con la marca. Dos fases **reales**:

1. **Subiendo composiciones… 47 %**: barra con porcentaje real.
2. **Analizando la escena…**: barra **indeterminada** con el texto «puede tardar en imágenes grandes». El motor no informa de su avance, así que **no se inventan pasos** («Calculando NBR…» y similares están prohibidos).

Se usa igual tras confirmar un encaje (§7), porque la escena se vuelve a analizar.

## 6. Espacio de trabajo

El mapa ocupa el centro; a su derecha va una columna fija de 400 px con pestañas y, sobre el mapa, una ventana flotante con el fondo y las capas. La maqueta de referencia está en `docs/design/`.

```
┌──────────────────────────────────────────────────────────────────────────────────┐
│ ▲ UNHEAT PROJECT │ 2500×1546 px │ SWIR · True Color · Wildfires │ ⌖ Encaje sobre │
│                  │              │                               │ el mapa · 18,2 m/px │ ☀ Tema │ Nueva escena │
├──────────────────────────────────────────────────────┬───────────────────────────┤
│                                                      │ Resumen │ Zonas │ Poblaciones│
│                                                      ├───────────────────────────┤
│                                                      │ titular                   │
│                     MAPA                             │ procedencia de la escala  │
│                                                      │ avisos                    │
│ ┌──────────────────┐                                 │ cifras ⓘ                  │
│ │ Fondo y capas  ✕ │                                 │ confianzas                │
│ │ (con leyenda)    │                                 │                           │
│ └──────────────────┘                                 │                           │
└──────────────────────────────────────────────────────┴───────────────────────────┘
```

La pestaña Poblaciones solo aparece con georreferencia.

### 6.1 Barra superior (fina)

- Marca Unheat Project.
- Chips de la escena: dimensiones en píxeles; composiciones aportadas; **estado de la georreferencia** con su procedencia («Sin georreferencia» / «GeoTIFF» / «Coordenadas manuales» / «Encaje sobre el mapa») y la escala («18,2 m/px») cuando la hay.
- Interruptor de tema claro/oscuro.
- Botón «Nueva escena», que vuelve a §4.

### 6.2 Columna derecha (400 px): pestañas Resumen y Zonas

**Titular**: una línea grande en lenguaje llano con lo esencial, p. ej. **«2 zonas quemadas · 13 684 ha · 7 focos activos»**. Sin georreferencia, el área va en píxeles («413 100 px»).

**Etiqueta de procedencia** visible a nivel de sección, p. ej. «Escala: encaje sobre el mapa · 18,2 m/px», o «Sin escala: cifras en píxeles».

**Cuadrícula de cifras**: cada cifra tiene etiqueta, valor con unidad y un icono **ⓘ** que, al pasar el ratón o con el foco del teclado, muestra la nota que explica de dónde sale. Cifras:

| Cifra | Ejemplo con georreferencia | Sin georreferencia |
| --- | --- | --- |
| Superficie quemada | 13 683,5 ha | 413 100 px |
| Zonas | 2 zonas quemadas | igual |
| Focos activos | 7 focos activos | igual |
| Dentro del perímetro frente a quemado | 14 120,6 ha frente a 13 683,5 ha (la diferencia son islas sin quemar) | *no disponible* |
| Longitud del perímetro | 96,4 km (tolerancia 40 m) | *no disponible* |

Una cifra **no disponible** se ve claramente distinta de una real: atenuada, con «no disponible» y su ⓘ explicando cómo obtenerla.

**Confianzas**: dos insignias, «Superficie quemada: alta|baja» y «Focos activos: alta|baja». En el ⓘ va el motivo en lenguaje llano. Ejemplo para baja en focos: «Sin la composición Wildfires, los focos se estiman desde la SWIR y puede faltar o sobrar alguno. Añade la Wildfires para mejorarla.» La confianza baja debe llamar la atención sin alarmar.

**Avisos del motor**: bloque destacado con 0..n frases. Ejemplo: «La composición Wildfires marca nubes en el 3 % de la escena; bajo ellas se han buscado focos con la SWIR (confianza baja).» Si no hay avisos, el bloque no aparece.

**Aviso de georreferencia** (solo sin georreferencia): discreto pero persistente. «Las cifras están en píxeles. Sitúa la escena en el mapa para obtener hectáreas y poblaciones.» Lleva el botón **«Situar en el mapa»**, que entra en el modo encaje (§7).

**Lista de zonas**, ordenadas de mayor a menor. Cada elemento en reposo muestra «Zona 1 · 11 633,1 ha · 85 % del total · 5 focos activos». Al **seleccionarse**, se despliega en línea (acordeón) como tarjeta con:

- Área (ha o px) con ⓘ.
- Parte del total quemado (85 %).
- Focos activos en la zona (5).
- Severidad relativa como **barra de dos tonos**: 58 % afectado · 42 % muy afectado. Nota: es relativa a esta escena y no se compara con otros incendios.
- Población más cercana: «Niebla, a 1,4 km», o *no disponible* sin georreferencia.

Con muchas zonas (25 o más), la lista hace scroll dentro de la columna.

### 6.3 Columna derecha: pestaña Poblaciones (solo con georreferencia)

Lista ordenada por distancia. Cada elemento lleva:

- Nombre de la población.
- **Nivel de alerta** como insignia con color **y** forma o icono, no solo color: Alta / Media / Vigilancia.
- Habitantes («4 116 habitantes», o «Habitantes sin dato en GeoNames»).
- Distancia y a qué: «1,4 km de un foco activo» / «4,1 km de la superficie quemada».

Datos de ejemplo:

| Población | Habitantes | Distancia | Respecto a | Alerta |
| --- | --- | --- | --- | --- |
| Niebla | 4 116 | 1,4 km | foco activo | Alta |
| Lucena del Puerto | 3 297 | 4,1 km | superficie quemada | Media |
| Bonares | 6 110 | 6,8 km | superficie quemada | Vigilancia |
| Rociana del Condado | 7 932 | 9,3 km | superficie quemada | Vigilancia |

Encabezado o pie con el criterio: alta = dentro del perímetro o a menos de 2 km de un foco; media < 5 km; vigilancia < 10 km. Se calcula **solo por distancia**: no modela humo ni propagación. Crédito GeoNames, CC BY 4.0.

Estado vacío (georreferenciada pero sin poblaciones en umbral): «No hay poblaciones del conjunto de datos dentro de los umbrales de alerta.»

Las poblaciones **no** se dibujan en el mapa; solo aparecen en esta lista.

### 6.4 Mapa

- **Sin georreferencia**: la imagen se muestra sola en coordenadas de píxel, sin mapa base.
- **Con georreferencia**: la imagen se sitúa sobre el mapa base topográfico OpenTopoMap.
- Zoom y desplazamiento libres.

**Capas** (encendibles y apagables):

| Capa | Representación | Restricciones |
| --- | --- | --- |
| Superficie quemada | Relleno semitransparente | Se ve el terreno debajo. |
| Severidad relativa | Dos tonos dentro de lo quemado: afectado / muy afectado | Diferenciables sin depender de rojo frente a verde. |
| Perímetro | Línea de contorno de cada zona | Legible sobre cualquier fondo. |
| Focos activos | **Triángulo**; tamaño e intensidad crecen con el nivel 1–4 | Forma distinta de todo lo demás. Los **estimados desde la SWIR** no tienen nivel: triángulo **malva grisáceo translúcido con borde blanco**, para que se vea sobre cualquier fondo. Puede haber focos fuera de cualquier zona. |

Todas las capas deben leerse sobre los **tres fondos posibles**: True Color (colores naturales: verdes, ocres y humo blanco), SWIR (falso color rojizo y anaranjado, con lo quemado en tonos oscuros y granates) y Wildfires (True Color con el fuego ya pintado en amarillo, naranja y rojo). Paleta **apta para daltonismo**.

**Interacción con zonas**:

- Al pasar el ratón por una zona: resalte y **tooltip compacto** (Zona 1 · 11 633,1 ha · 85 %).
- Clic en una zona, del mapa o de la lista: queda **seleccionada** (resalte persistente), el mapa se centra en ella y su elemento de la lista se despliega.
- Clic en un área vacía del mapa: deselecciona.
- Teclado en la lista: flechas para recorrer, Enter para seleccionar y Esc para deseleccionar.

Hacen falta tres estilos de zona distinguibles: normal, al pasar el ratón y seleccionada.

### 6.5 Ventana flotante «Fondo y capas» (esquina inferior izquierda del mapa)

- **Fondo**: selector entre las composiciones aportadas (solo las que se subieron). Por defecto True Color si existe; si no, SWIR.
- **Capas**: un interruptor por capa con su **muestra de leyenda** al lado (color o forma), de modo que no haga falta una leyenda aparte. Para los focos, la leyenda enseña los niveles 1–4 y la variante estimada desde la SWIR.
- Una capa que el resultado no trae aparece deshabilitada con su motivo, p. ej. «No se han detectado focos activos».
- Se cierra con ✕ y queda un botón «≋ Fondo y capas» para volver a abrirla.

## 7. Modo encaje sobre el mapa

Es un estado del espacio de trabajo, al que se entra desde «Situar en el mapa». Sirve para georreferenciar sin saber coordenadas.

- Se ocultan la columna derecha y la ventana de capas, la barra superior dice «Encaje en curso», y aparece un panel de instrucciones: «Arrastra el punto central para mover la imagen y las esquinas para cambiar su tamaño sin deformarla, hasta que ríos y carreteras coincidan con el mapa.»
- La imagen SWIR se superpone **semitransparente** sobre el mapa base, con **asas**: una central para mover y cuatro en las esquinas para cambiar el tamaño manteniendo la proporción. Al ampliar el mapa, la imagen mantiene su tamaño en pantalla.
- Un **regulador de opacidad** de la imagen (10–100 %).
- Botones **Listo** (confirma, y se vuelve a analizar con §5) y **Cancelar** (vuelve al resultado anterior sin cambios).

## 8. Accesibilidad

- Paleta apta para daltonismo; nada se distingue solo por rojo frente a verde. Los focos y las alertas se distinguen también por forma o icono.
- Contraste AA en los dos temas.
- Todo es operable con teclado, con foco visible. Los ⓘ se abren también con foco.
- Hay un **párrafo resumen para lector de pantalla**, oculto visualmente y en región `aria-live`, del tipo «Se han detectado 2 zonas quemadas, unas 13 684 ha quemadas en total, y 7 focos activos. Zona 1: 85 % del total quemado, 5 focos activos; población más cercana: Niebla, a 1,4 km. … Confianza alta en la superficie quemada y alta en los focos activos.» No necesita diseño visual.

## 9. Textos

Se pueden reescribir los microtextos para que sean más cortos y claros, con dos límites:

- Respetar los términos del glosario y no sustituirlos por sinónimos: **Escena, Composición (SWIR, True Color, Wildfires), Superficie quemada, Zona, Perímetro, Foco activo, Severidad relativa (afectado / muy afectado), Confianza, Georreferencia, Encaje, Población, Alerta (alta / media / vigilancia).** Evitar «hotspot», «área afectada», «pueblo», «riesgo», «score» o «capa» para referirse a una composición.
- Nunca presentar una cifra que no existe ni dar a entender precisión que no hay.

Formato numérico español: separador de miles con espacio fino (13 684) y coma decimal (11 633,1 ha; 1,4 km).

## 10. Estados que el diseño debe cubrir

1. **Nueva escena**: vacía; con SWIR cargada; con las tres composiciones y la ubicación abierta (en cada pestaña); con errores en línea y de servidor.
2. **Análisis en curso**: fase de subida (con %) y fase de análisis (indeterminada).
3. **Espacio de trabajo completo**: tres composiciones y georreferencia, con la Zona 1 seleccionada y panel de alertas (datos de §6.2 y §6.3).
4. **Sin georreferencia**: cifras en px, *no disponible* donde toca, aviso «Situar en el mapa» y sin panel de alertas.
5. **Georreferenciada sin poblaciones en umbral**: panel de alertas en estado vacío.
6. **Cero zonas quemadas**: titular, lista vacía con su mensaje y mapa limpio.
7. **Cero focos activos**: capa de focos deshabilitada con su motivo.
8. **Solo SWIR**: ambas confianzas bajas con su explicación y focos estimados en malva.
9. **Muchas zonas** (≈ 25): lista con scroll.
10. **Modo encaje sobre el mapa.**
11. Los dos **temas**, claro y oscuro, al menos para las pantallas 1, 3 y 10.

## 11. Entregable esperado de Claude Design

- Las maquetas de los estados de §10.
- Los **tokens** (colores para los dos temas, tipografía, espaciados, radios, sombras) como variables CSS.
- La **especificación de las capas del mapa**: colores, opacidades y trazos de superficie quemada, severidad, perímetro (normal, al pasar el ratón y seleccionada), focos por nivel 1–4 y estimado, más las insignias de alerta y confianza.
- HTML/CSS de referencia sin framework (§2), si es posible.
