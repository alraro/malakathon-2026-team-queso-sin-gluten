# Informe de mejoras frente a los criterios de evaluación

**Fecha:** 15 de octubre de 2026. **Base revisada:** `main`, commit `45de448`.

**Fuente de los criterios:** las dos fotografías facilitadas por el equipo. Son una rúbrica para analizar, no instrucciones de implementación.

**Alcance:** diagnóstico y propuestas; este informe no acredita ensayos nuevos ni modifica la aplicación.

## Diagnóstico ejecutivo

La solución ya distingue superficie quemada y focos activos, usa un umbral NBR adaptativo, filtra varias fuentes de falsos positivos y ofrece web, CLI y configuración Docker. El mayor riesgo para la nota está en **demostrar precisión y generalización en escenas no vistas**: la [validación actual](validacion.md) es de autoconsistencia y no compara la máscara con anotaciones independientes. Las [correcciones de suelo desnudo](../fixes/suelo-desnudo-y-frente-partido.md) y [focos débiles](../fixes/focos-debiles-sobre-suelo-desnudo.md) mejoraron mucho Huelva, pero se ajustaron y midieron principalmente con las escenas disponibles. Conviene reservar las pruebas nuevas para evaluación, sin reajustar después los parámetros sobre ellas.

| Criterio | Peso | Situación comprobada | Mejora con mayor retorno |
| --- | ---: | --- | --- |
| Detección | 35 % | Hay máscara, perímetro y focos. Falta una medida externa de aciertos, omisiones y límites. El detector SWIR de respaldo solo alcanza 27,9 % de precisión frente a Wildfires en Guadalajara; esa comparación tampoco es verdad terreno. | Anotación independiente y matriz de errores por escena, clase y fuente del foco. |
| Robustez | 25 % | El corte NBR se calcula por escena, pero hay reglas fijas de brillo, área y morfología. Solo constan tres escenas de desarrollo. | Ensayo ciego con escenas y condiciones distintas, sin retoques manuales. |
| Automatización y calidad | 15 % | Hay entrada web/CLI, contrato, tests y Docker. La validación de la escena grande documentada ronda 50 s y 3 GB de RAM. | Probar el flujo completo y medir tiempo/RAM en un portátil corriente. |
| Razonamiento | 15 % | La justificación técnica está escrita en la [investigación](../research/sentinel2-rgb-fire-sota.md), pero dispersa para una defensa breve. | Preparar una ficha verificable de decisiones, límites y fallos. |
| Presentación | 10 % | El visor ya permite fondos, capas, leyenda, zonas, avisos y resultado de ejemplo. Al arrancar queda sin una escena analizada. | Demo inicial clara y comparación visual legible de imagen, máscara, perímetro y focos. |

Las metas numéricas que se propongan a continuación deben tratarse como **objetivos internos**, no como umbrales oficiales de la rúbrica. No se puede prometer una puntuación perfecta sin conocer las escenas ocultas.

## 1. Rendimiento de detección — 35 %

### Evidencia y problema

- El motor calcula NBR a partir de la SWIR, segmenta por multi-Otsu y delimita zonas con contornos ([`burned_area.py`](../../src/fire_engine/burned_area.py)). También distingue focos de Wildfires y de SWIR, esta última fuente con confianza baja ([`active_fire.py`](../../src/fire_engine/active_fire.py)).
- La [validación](validacion.md) declara expresamente que no tiene *ground truth*. Las cifras de humo/nube y la contención de focos son comprobaciones internas: **0 % de fuga de nube** en el test implementado no demuestra 0 % de falsos positivos reales.
- En Huelva se redujeron las zonas de 24 a 3 tras eliminar suelo desnudo. Después, el filtro de [focos débiles sin respaldo SWIR](../fixes/focos-debiles-sobre-suelo-desnudo.md) redujo los focos Wildfires de 106 a **56** y elevó los grupos que tocan una zona quemada del 47 % al **89,3 %**. Esto corrige el defecto antes señalado, pero debe comprobarse en escenas nuevas que no se omitan focos auténticos. No se deben forzar todos los focos a caer dentro de la cicatriz: un frente activo puede avanzar por delante de ella.
- La precisión del detector SWIR frente a la decodificación Wildfires filtrada es **27,9 % en Guadalajara** y **62,7 % en Huelva**; la exhaustividad es **76,9 % y 88,3 %** respectivamente. Wildfires es aquí una referencia indirecta, no una anotación independiente.

### Qué aplicar

1. **Crear un pequeño conjunto de referencia independiente.** Anotar máscaras de cicatriz y focos en escenas que no se hayan usado para diseñar reglas, con protocolo explícito para humo, nubes, bordes ambiguos y zonas no evaluables. Si es posible, dos revisores resuelven desacuerdos. Mantener las escenas de evaluación separadas de las de ajuste. Un producto Copernicus puede apoyar la comprobación espacial solo si coinciden fecha, encuadre y georreferencia; la comparación pendiente con EMSR913 no sirve como IoU directa en el estado actual ([§5 de la validación](validacion.md)).
2. **Medir lo que pide la rúbrica cuando la referencia sea fiable.** IoU y Dice de máscara; precisión, exhaustividad y F1 de focos con una regla fija de coincidencia (distancia en píxeles o metros y tratamiento de componentes). Añadir acierto del perímetro, por ejemplo distancia de contorno, para no esconder un límite desplazado detrás de una buena IoU. Informar por escena y agregado, junto con el número de píxeles/focos y las regiones excluidas por incertidumbre. Si no se consigue referencia fiable, declarar esta limitación y mostrar casos revisados manualmente, sin llamarlos IoU real.
3. **Auditar errores por tipo de terreno.** Preparar mosaicos imagen/máscara para vegetación, cultivo seco, suelo desnudo, minas, casco urbano, agua, sombras, nube y humo. Para cada falso positivo u omisión, registrar causa probable y si pertenece a segmentación o a detección activa. El corte fijo de B8A que corrigió Huelva conserva allí el **92,4 %** de la cicatriz medida y descarta el **98,6 %** del suelo desnudo medido; hay que comprobar tanto el descarte como las pérdidas en otras escenas antes de generalizarlo.
4. **Validar el filtro de focos débiles ya aplicado y el modo sin Wildfires.** Separar en la evaluación niveles 1–2 de 3–4 y fuentes Wildfires/SWIR; comprobar en escenas reservadas que la corroboración SWIR no elimina focos reales de baja intensidad. Inspeccionar también los focos fuera de zona: pueden corresponder al frente o a otro fuego, no ser automáticamente falsos positivos. Si la evidencia no permite mejorar el respaldo SWIR, mantenerlo claramente como estimación de baja confianza y priorizar la entrega de Wildfires cuando exista.

**Evidencia de cierre:** tabla de métricas con protocolo y referencia identificables, galería de errores representativos, y comparación antes/después que muestre falsos positivos **y** omisiones. Congelar método y umbrales antes de pasar a las escenas ocultas.

## 2. Robustez y generalización — 25 %

### Evidencia y problema

El umbral principal se adapta al histograma de cada escena, una fortaleza clara. Aun así, el motor usa valores fijos para suelo desnudo, crecimiento de focos, agrupación de fragmentos y área mínima. Los JPEG de `data/` son tres escenas con resoluciones y combinaciones de capas distintas; eso no basta para demostrar transferencia a terrenos, humo y renderizados nuevos. La sensibilidad del área ante desplazar el NBR ±0,02 es de **±4,9 % a ±7,6 %** en esas escenas, dato útil pero distinto de la robustez ante escenas no vistas ([validación](validacion.md)).

### Qué aplicar

1. Reunir **una o dos escenas nuevas y reservadas** en pares True Color/SWIR, con Wildfires cuando esté disponible, además de una escena sin fuego si se consigue. Registrar procedencia, fecha, resolución, composición y si los archivos están alineados. No reajustar reglas para cada imagen.
2. Ejecutar una matriz de condiciones: terreno distinto, incendio extenso/pequeño, humo, nube, suelo brillante, ausencia de True Color, ausencia de Wildfires y escena sin incendio. Evaluar también si cambia la salida con variaciones razonables de compresión o escala del JPEG; etiquetar esos ensayos como perturbaciones sintéticas, no como escenas nuevas.
3. Comprobar que la salida es estable y explicable: máscara, focos, confianza, avisos, áreas en píxeles y, solo con georreferencia fiable, hectáreas. Guardar los resultados de cada escena **sin edición manual posterior** y registrar los casos donde falla.
4. Evitar describir la severidad relativa como gravedad física comparable entre escenas. Los JPEG disponibles carecen de imagen anterior al incendio y de B11; por ello no permiten dNBR ni reproducir por completo la prueba SWIR de focos que necesita B11 ([investigación §7](../research/sentinel2-rgb-fire-sota.md)).

**Evidencia de cierre:** tabla por escena y condición, mismo comando y parámetros para todas, métricas de la sección 1 donde haya anotaciones y descripción precisa de los fallos restantes.

## 3. Automatización y calidad técnica — 15 %

### Qué ya existe

[`compose.yaml`](../../compose.yaml) expone la web en el puerto 8000; [`Dockerfile`](../../Dockerfile) inicia Uvicorn; la [API](../../src/fire_engine/api.py) acepta las composiciones y sirve el visor; el [README](../../README.md) explica el arranque y el CLI. Las dependencias de ejecución están fijadas en [`pyproject.toml`](../../pyproject.toml) y hay pruebas automatizadas en `tests/`.

### Qué aplicar

1. **Ensayo de instalación limpia:** construir la imagen desde cero y verificar apertura de la web, carga de ejemplo, subida de una escena nueva, generación de capas y lectura de avisos, sin pasos manuales ocultos. Registrar comando, versión de Docker y resultado. La vista inicial hoy muestra formulario y mapa vacío hasta pulsar «Ver resultado de ejemplo» o analizar; para la evaluación conviene hacer visible esa acción o cargar una demostración inequívocamente marcada como tal.
2. **Medición reproducible en portátil estándar:** tiempo de arranque, tiempo por escena y pico de RAM tanto para escenas de 2500 px como para Madrid-Ávila (9930 × 6141). El README ya documenta alrededor de **50 s y 3 GB** para la validación grande; confirmar el flujo web/Docker y fijar un límite operativo realista. Si supera la memoria disponible, priorizar reducir arrays intermedios o procesar por bloques antes de añadir funciones nuevas.
3. **Pruebas de fallos de entrada:** archivos corruptos, composiciones de distinto tamaño, capas ausentes, escena sin incendio y georreferencia inválida. Verificar mensaje claro y recuperación de la interfaz. Diferenciar este control funcional de la validación científica del detector.
4. Conservar en una ficha de reproducción el commit, comando, archivos de entrada y salida, parámetros automáticos, tiempos y hardware. Ejecutar la suite existente antes de la demo y guardar un resultado del CLI y otro de la web para la misma escena.

**Evidencia de cierre:** registro de una ejecución limpia completa, tabla tiempo/RAM y pruebas esenciales superadas en el equipo de demostración.

## 4. Razonamiento técnico y metodología — 15 %

Preparar una **ficha de una página** y una defensa oral de dos minutos, apoyadas en la [investigación](../research/sentinel2-rgb-fire-sota.md) y las medidas propias:

- **Por qué este enfoque:** NBR dentro de la composición SWIR conserva la relación B8A/B12 bajo la ganancia lineal; multi-Otsu evita un corte NBR manual por escena; la True Color ayuda a distinguir humo/nube y la Wildfires ya codifica una clasificación de focos. Comparar brevemente con umbral fijo, clasificación solo RGB y modelos que requieren bandas o entrenamiento no disponibles. La eficacia medida importa más que la complejidad.
- **Qué significan las dos salidas:** la cicatriz es terreno ya afectado en la imagen; el foco indica actividad posible en el instante de adquisición. «Muy afectado» es una división **relativa** de la escena, no una clase oficial de severidad. Un foco fuera del perímetro exige revisión y puede ser frente nuevo o falso positivo.
- **Principales fallos:** suelo desnudo/urbano confundido con cicatriz; humo que rompe un frente; focos débiles espurios; nubes que ocultan focos; pérdida de cicatriz con reglas de rechazo; errores de alineación entre composiciones. Para cada uno, mostrar un ejemplo, su mitigación actual y el error residual.
- **Qué añadiría con datos originales:** bandas sin renderizar, especialmente B11, para completar pruebas espectrales de focos y mejorar discriminación; imagen anterior al incendio para dNBR; georreferencia nativa y anotaciones temporales compatibles para evaluación externa. Presentarlo como mejora futura, no como capacidad actual.

**Evidencia de cierre:** respuestas directas a las tres preguntas sugeridas por el documento del jurado (elección y alternativas; fallos y falsos positivos; mejora con multiespectral/tiempo), sin equiparar autoconsistencia con exactitud real.

## 5. Presentación y usabilidad — 10 %

El [visor actual](../../web/index.html) ya tiene leyenda con símbolos distintos, fondos intercambiables, capas independientes, lista de zonas, resumen y avisos. Hay un botón de resultado de ejemplo, correctamente marcado como cifras inventadas ([`status.js`](../../web/js/status.js)); no conviene presentarlo como resultado de una escena real.

1. Preparar un recorrido visible de **imagen original → máscara → perímetro → focos** con controles y leyenda a la vista, sobre True Color y SWIR. Mostrar un caso con Wildfires y otro solo con SWIR para que la diferencia de confianza sea evidente.
2. En el arranque, orientar al jurado con una escena real precargada o una llamada a la acción destacada para abrir el ejemplo. Si se precarga algo, distinguir de forma persistente demostración, datos reales y análisis nuevo; incluir procedencia de la escena.
3. Revisar legibilidad de máscara y contorno en fondos claros/oscuros, el foco pequeño al hacer zoom, las zonas sin incendio y las advertencias sobre nubes, falta de georreferencia y baja confianza. Hacer una prueba rápida con alguien que no conozca el proyecto: debe identificar qué ardió, qué sigue activo y cuánta certeza hay sin explicación oral.
4. En cifras y mapa, no atribuir hectáreas o distancias precisas a un JPEG sin escala verificada. Con bbox manual o encaje visual, explicitar la procedencia y posible error de ubicación.

**Evidencia de cierre:** capturas de dos escenas reales y una prueba de comprensión de 3 preguntas con una persona ajena al desarrollo; corregir confusiones detectadas.

## Orden propuesto para el tiempo restante

1. **Primero: evaluación externa y fallos de detección (35 % + 25 %).** Conseguir escenas reservadas, anotar una muestra pequeña pero fiable, fijar protocolo y medir errores. Revisar falsos focos débiles y pérdidas de cicatriz según esos resultados.
2. **Después: ejecución ciega y rendimiento (25 % + 15 %).** Pasar el mismo flujo por escenas nuevas, Docker, web y CLI; medir RAM/tiempo y documentar fallos sin ajuste manual por escena.
3. **Luego: claridad para el jurado (15 % + 10 %).** Ficha metodológica, guion de las tres preguntas, demo inicial inequívoca y capturas comparativas.
4. **Solo si sobra tiempo:** mejorar georreferencia/contraste con EMSR913 y funciones accesorias. Sin un bbox verificado y un instante comparable, esa comparación no debe convertirse en una cifra de IoU.

La mejora más valiosa no es añadir un algoritmo más complejo: es demostrar, con pruebas independientes y un flujo reproducible, **dónde acierta y dónde falla la solución existente**.
