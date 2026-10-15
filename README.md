# Detección de incendios en composiciones Sentinel-2

Aplicación para delimitar **superficie quemada** y **focos activos** a partir de composiciones JPEG ya renderizadas del Copernicus Browser. La composición SWIR es obligatoria. True Color ayuda a descartar humo y nubes; Wildfires aporta la fuente preferente de focos activos. El resultado muestra zonas, perímetros y confianza, y solo calcula hectáreas o distancias si se aporta una georreferencia.

## Arranque con Docker

Desde la raíz del repositorio, con Docker Compose disponible:

```sh
docker compose up --build
```

Abrir <http://localhost:8000>. El servicio monta `data/` como solo lectura en `/data` y guarda resultados en `out/` (montado en `/out`). Para parar, pulsar `Ctrl+C`.

> **Estado de integración:** el motor y el CLI ya están en `main`. La API y la web pertenecen a la issue #5 y aún no están integradas. El comando de arriba arrancará la web cuando `fire_engine.api:app` esté disponible; hasta entonces, `uvicorn` indicará que falta ese módulo. El CLI sí puede ejecutarse en la imagen.

### CLI dentro del contenedor

```sh
docker compose run --rm app fire-engine analyse \
  --swir /data/huelva/2026-08-08-00_00_2026-08-08-23_59_Sentinel-2_L2A_SWIR.jpg \
  --true-color /data/huelva/2026-08-08-00_00_2026-08-08-23_59_Sentinel-2_L2A_True_color.jpg \
  --wildfires /data/huelva/2026-08-08-00_00_2026-08-08-23_59_Sentinel-2_L2A_Wildfires.jpg \
  --out /out/huelva
```

La salida es `out/huelva/result.json`. Para otras escenas, sustituir las rutas; `--true-color` y `--wildfires` son opcionales. Para pasar un bbox WGS84, añadir `--bbox LON_MIN LAT_MIN LON_MAX LAT_MAX` antes de `--out`. Ejemplo: `--bbox -7.5 37.0 -6.8 37.5`. Las coordenadas deben corresponder al encuadre de la escena; **no se pueden deducir del JPEG**.

En PowerShell, el mismo comando se puede escribir en una sola línea. Otra opción es instalar el paquete con `python -m pip install -e .` y ejecutar `fire-engine analyse --swir … --out out/huelva` en el equipo local.

## Entradas y resultado

| Composición | Obligatoria | Aporta |
| --- | --- | --- |
| SWIR (`--swir`) | Sí | Superficie quemada y estimación de focos activos si falta Wildfires. |
| True Color (`--true-color`) | No | Descarte de humo y nubes; aumenta la confianza de la superficie quemada. |
| Wildfires (`--wildfires`) | No | Clasificación de focos activos en cuatro niveles, con mayor confianza. |

Las composiciones de una escena deben tener el mismo tamaño y estar co-registradas. El JSON sigue [`contract/result.schema.json`](contract/result.schema.json); [`contract/example.json`](contract/example.json) muestra la estructura con zonas, focos, alertas y capas. El CLI existente escribe `result.json`; las máscaras y la vista previa PNG se incorporarán al cerrar las issues #2 y #4.

## Método

1. En la composición SWIR, el motor calcula NBR como `(G − R)/(G + R)`; ambas bandas están en el mismo JPEG con la misma ganancia. Un umbral multi-Otsu de tres clases, estimado **para cada escena**, separa no quemado, afectado y muy afectado. Limpieza morfológica y componentes conexas forman zonas; los contornos se simplifican para dibujar el perímetro. La severidad es **relativa a la propia escena**.
2. Cuando hay True Color, se comparan su brillo y el de SWIR para excluir humo y nubes, junto con comprobaciones de vegetación, agua y sombra. Sin True Color se usan solo las señales de SWIR y se comunica menor confianza.
3. Con Wildfires, se decodifican los colores del detector QuickFire ya pintados por Copernicus Browser para localizar focos activos y su nivel 1–4. Sin ella, un detector parcial basado en B12 y B8A de la SWIR produce una estimación de menor confianza.
4. La georreferencia opcional transforma las coordenadas de píxel en hectáreas y kilómetros. Las poblaciones cercanas y sus alertas por distancia solo se muestran cuando hay coordenadas fiables.

El fundamento, las mediciones y los casos problemáticos están en [`docs/research/sentinel2-rgb-fire-sota.md`](docs/research/sentinel2-rgb-fire-sota.md).

## Límites

- Estos JPEG **no incluyen B11**, por lo que el detector QuickFire no se puede reconstruir íntegramente sin la composición Wildfires.
- No hay imagen anterior al incendio: no se calcula dNBR ni severidad absoluta, y una superficie oscura previa podría confundirse con quemado.
- Los JPEG de `data/` no llevan escala ni coordenadas. Sin bbox o GeoTIFF no se deben publicar hectáreas, kilómetros ni poblaciones afectadas.
- Humo, nubes, agua, sombras, suelo desnudo y zonas urbanas pueden provocar errores; la confianza indica qué composiciones respaldan el resultado. Un foco activo fuera de una zona quemada requiere revisión.
- La captura Sentinel-2 muestra el estado en el momento de adquisición; no es seguimiento en tiempo real.

## Trabajo futuro

Dirección del humo y propagación para mejorar las alertas; refinamiento opcional de contornos con SAM2; despliegue público. El criterio de alerta actual se basa en distancias y **no** predice la evolución del incendio.
