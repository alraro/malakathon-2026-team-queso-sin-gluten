# Fix: la Wildfires pinta como foco débil el suelo desnudo brillante

> Vocabulario según `CONTEXT.md`. Continúa `docs/fixes/suelo-desnudo-y-frente-partido.md`:
> misma causa de fondo (el suelo desnudo no estaba modelado), otro módulo.

## Síntoma

Focos activos sobre campo sin incendio, lejos de la cicatriz. En Huelva eran 51 de 104, casi
todos en el cinturón minero y urbano del oeste (x 115–370). La spec pide que más del 90 % de
los focos caiga dentro de la superficie quemada; la escena se quedaba en el 47 %.

## Causa

`decode_wildfires` lee la clasificación que QuickFire pinta en el render: rojo cerca de
saturación y `R − B` muy por encima de la mediana de la escena. El suelo desnudo brillante
cumple las dos cosas, y con el render solo no hay forma de distinguirlo: la Wildfires no
lleva más información. Medido en Huelva, en los píxeles de foco:

| | B12 | B8A | B12/B8A |
| --- | ---: | ---: | ---: |
| Focos de nivel ≥ 3 | 253 | 122 | **2.07** |
| Focos de nivel 1–2 | 245 | 235 | **1.03** |

La SWIR, que es obligatoria, sí lo distingue: un píxel con combustión tiene `B12 ≥ 0.15` y
`B12/B8A ≥ 1.4` (las dos pruebas de Murphy disponibles, ya en `potentially_burning()`).

## El arreglo

`_corroborated()` en `active_fire.py`, sobre los niveles decodificados y antes de nada más:

- **Solo los niveles 1–2 necesitan respaldo** (`CORROBORATED_MAX_LEVEL`). Los niveles 3–4 se
  aceptan tal cual: `CONTEXT.md` hace de la Wildfires la fuente preferente de focos, y la
  prueba de Murphy aquí es parcial (le falta `B12/B11`, que no está en ninguna composición),
  así que no es quién para desmentir una clasificación fuerte. Toda la confusión con el
  suelo desnudo vive en los niveles débiles. Filtrar también los niveles 3–4 subía Huelva un
  punto (94 % en vez de 93 % de los focos de la Wildfires) a cambio de tirar un nivel 3 por
  escena: no compensa.
- **Por grupos conexos, no por píxel**: las dos composiciones pueden ir desplazadas un píxel,
  así que basta con que uno del grupo pase la prueba. Exigir que pasara la mitad del grupo
  tiraba un foco bueno de Guadalajara.
- **Se avisa**: el resumen dice cuántos focos débiles se han descartado y por qué, como con
  las nubes.

## Medidas

| Escena | Focos | Dentro de la superficie quemada | Nivel 4 |
| --- | ---: | ---: | ---: |
| Huelva | 106 → **56** | 47 % → **89 %** | 19 → 19 |
| Guadalajara | 56 → **52** | 69 % → **71 %** | 2 → 2 |
| Madrid-Ávila | 203 | 42 % | sin composición Wildfires, la puerta no se aplica |

**Ningún foco que cayera dentro de la superficie quemada se pierde**, en ninguna de las dos
escenas con Wildfires, y no se pierde ningún nivel 4. Por píxeles (`docs/results/validacion.md`,
regenerado): en Huelva, los de foco dentro de la superficie quemada pasan del 59 % al 87 %, y
los que tienen NBR < 0 del 91 % al 96 %.

## Dos tests sintéticos cambiaron de escena

`test_wildfires_active_fires_are_decoded_with_their_level` y
`test_cloud_next_to_wildfires_triggers_swir_search_and_warning` pintaban el foco solo en la
Wildfires, sobre una SWIR de vegetación intacta: una escena que no puede existir, porque un
foco de verdad se ve en las dos composiciones. Ahora pintan las dos, que es lo que la puerta
da por supuesto.

## Lo que queda fuera, y por qué está bien

En Huelva quedan 6 focos fuera de la superficie quemada. Cinco están a menos de 73 px del
borde: es el frente avanzando sobre combustible aún sin quemar, justo lo que describe el
aviso que ya daba el motor. El sexto es un nivel 4 a 1093 px, en el regadío, con B12 252 y
`B12/B8A = 2.40`: pasa la prueba de Murphy, así que es un foco de verdad — quema de rastrojo,
habitual en agosto en esa zona — y no un falso positivo.

Guadalajara se queda en el 71 % y no llega al 90 % de la spec. Sus focos de fuera también
corroboran en la SWIR, así que son frente, no ruido. Si se quiere ese criterio en verde, lo
honesto es afinar el enunciado de la spec para que excluya los focos corroborados fuera de la
cicatriz, no apretar el detector hasta que el número cuadre.
