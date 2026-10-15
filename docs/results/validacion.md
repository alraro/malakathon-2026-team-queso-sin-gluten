# Validación por autoconsistencia

Generado con `fire-engine validate`. Sin ground truth: estas cifras comprueban que el
resultado es coherente consigo mismo (ver `docs/research/sentinel2-rgb-fire-sota.md` §5.4).

## 1. Focos activos dentro de la superficie quemada

Focos activos (grupos conexos) que tocan una zona; los demás disparan el aviso del
motor. Por píxel: fracción dentro de la superficie quemada y con NBR < 0.
Referencia medida (§4.6, NBR < 0 en los focos Wildfires): 91 % Huelva, 99 % Guadalajara.

| Escena | Fuente | Focos | Focos en una zona | Píxeles de foco | Píxeles en la superficie quemada | Píxeles con NBR < 0 |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| guadalajara | wildfires | 51 | 80,4% | 678 | 68,6% | 100,0% |
| huelva | wildfires | 55 | 90,9% | 5320 | 97,6% | 100,0% |
| madrid-avila | swir | 203 | 42,4% | 12381 | 83,6% | 100,0% |

## 2. Estabilidad del área ante el umbral NBR (±0,02)

Área quemada en píxeles con el umbral adaptativo desplazado. La banda es la semiamplitud
relativa al área del motor.

| Escena | Umbral −0,02 | Umbral del motor | Umbral +0,02 | Banda de incertidumbre |
| --- | ---: | ---: | ---: | ---: |
| guadalajara | 359685 | 373374 | 384989 | ±3,4% |
| huelva | 285146 | 296707 | 306187 | ±3,5% |
| madrid-avila | 2315189 | 2395358 | 2471680 | ±3,3% |

## 3. Humo y nube en la superficie quemada

Fracción de la superficie quemada que cumple el test de humo (corte del motor D > 2 y
corte de §4.3 D > 1) o el de nube. Requiere True Color. El humo no es una fuga: es la
cicatriz bajo humo que el motor recupera a propósito creciendo desde la cicatriz
visible (solo manchas que la tocan). La nube sí se excluye: esa columna mide lo que
reintroduce la limpieza morfológica.

| Escena | Humo (D > 2) | Humo fino (D > 1) | Nube |
| --- | ---: | ---: | ---: |
| guadalajara | 1,8% | 28,2% | 0,1% |
| huelva | 8,1% | 46,0% | 0,0% |
| madrid-avila | 4,1% | 37,6% | 0,0% |

## 4. Detector SWIR frente a la Wildfires

Precisión y exhaustividad por píxel del detector SWIR (Murphy-partial) tomando como
referencia la decodificación de la Wildfires. Requiere Wildfires.

| Escena | Precisión | Exhaustividad |
| --- | ---: | ---: |
| guadalajara | 27,9% | 77,1% |
| huelva | 62,7% | 98,3% |
| madrid-avila | — | — |

## 5. Comparación con Copernicus EMS EMSR913 (Huelva)

No incluida. Los productos existen (la API de CEMS, consultada el 2026-10-15, lista
9 productos y 1 AOI con centroide −6,69, 37,48), pero los JPEG de `data/` no llevan
georreferencia y la escena de Huelva no tiene un bbox verificado: el perímetro solo existe
en coordenadas de píxel y no se puede superponer a los vectores de EMSR913 (WGS84).
Cuando la escena tenga georreferencia (#7),
la comparación será de presencia y ubicación, no IoU píxel a píxel: EMSR913 se activó el
2026-08-07 y la escena es del 2026-08-08.
