# Validación por autoconsistencia

Generado con `fire-engine validate`. Sin ground truth: estas cifras comprueban que el
resultado es coherente consigo mismo (ver `docs/research/sentinel2-rgb-fire-sota.md` §5.4).

## 1. Focos activos dentro de la superficie quemada

Fracción de píxeles de foco activo dentro de la superficie quemada y con NBR < 0.
Referencia medida (§4.6, NBR < 0 en los focos Wildfires): 91 % Huelva, 99 % Guadalajara.

| Escena | Fuente de focos | Píxeles de foco | Dentro de la superficie quemada | Con NBR < 0 |
| --- | --- | ---: | ---: | ---: |
| guadalajara | wildfires | 688 | 64,1% | 99,9% |
| huelva | wildfires | 8703 | 58,7% | 91,1% |
| madrid-avila | swir | 12381 | 73,5% | 100,0% |

## 2. Estabilidad del área ante el umbral NBR (±0,02)

Área quemada en píxeles con el umbral adaptativo desplazado. La banda es la semiamplitud
relativa al área del motor.

| Escena | Umbral −0,02 | Umbral del motor | Umbral +0,02 | Banda de incertidumbre |
| --- | ---: | ---: | ---: | ---: |
| guadalajara | 312501 | 334852 | 353303 | ±6,1% |
| huelva | 193213 | 228346 | 290291 | ±21,3% |
| madrid-avila | 1631551 | 1780781 | 1978088 | ±9,7% |

## 3. Fuga de humo y nube en la superficie quemada

Fracción de la superficie quemada que cumple el test de humo (corte del motor D > 2 y
corte de §4.3 D > 1) o el de nube. Requiere True Color.

| Escena | Humo (D > 2) | Humo fino (D > 1) | Nube |
| --- | ---: | ---: | ---: |
| guadalajara | 0,0% | 18,7% | 0,0% |
| huelva | 0,0% | 14,7% | 0,3% |
| madrid-avila | 0,0% | 13,6% | 0,0% |

## 4. Detector SWIR frente a la Wildfires

Precisión y exhaustividad por píxel del detector SWIR (Murphy-partial) tomando como
referencia la decodificación de la Wildfires. Requiere Wildfires.

| Escena | Precisión | Exhaustividad |
| --- | ---: | ---: |
| guadalajara | 27,9% | 75,7% |
| huelva | 62,7% | 59,8% |
| madrid-avila | — | — |

## 5. Comparación con Copernicus EMS EMSR913 (Huelva)

No incluida. Los productos existen (la API de CEMS lista 9 productos y 1 AOI, centroide
−6,69, 37,48), pero los JPEG de `data/` no llevan georreferencia y la escena de Huelva no
tiene un bbox verificado: el perímetro solo existe en coordenadas de píxel y no se puede
superponer a los vectores de EMSR913 (WGS84). Cuando la escena tenga georreferencia (#7),
la comparación será de presencia y ubicación, no IoU píxel a píxel: EMSR913 se activó el
2026-08-07 y la escena es del 2026-08-08.
