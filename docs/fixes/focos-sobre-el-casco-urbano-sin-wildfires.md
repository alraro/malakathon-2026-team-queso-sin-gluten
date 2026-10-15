# Fix: sin Wildfires, el casco urbano de Madrid salía lleno de focos

> Vocabulario según `CONTEXT.md`. Cierra la familia que abrieron
> `docs/fixes/suelo-desnudo-y-frente-partido.md` y
> `docs/fixes/focos-debiles-sobre-suelo-desnudo.md`: el suelo desnudo brillante leído como
> fuego. Aquí por el tercer camino, el único que quedaba sin puerta.

## Síntoma

En Madrid-Ávila, 62 de los 203 focos activos caían sobre el área metropolitana de Madrid
(este de la escena, x > 6951), lejos del incendio, que está al oeste. Comprobados a ojo
sobre la True Color y la SWIR: una cantera con nave de cubierta roja (x 8268), un polígono
industrial (x 8411) y casco urbano (x 8047). Ni humo, ni cicatriz, ni pluma. Solo el 42,4 %
de los focos tocaba una zona.

## Cómo reproducirlo

```sh
.venv/bin/python -m pytest tests/test_active_fire.py -q -k "far_from_every_zone or just_outside_the_zone"
```

## Causa: el camino SWIR-only no tiene ninguna puerta, y la que hay no puede tenerla

Madrid-Ávila es la única escena de `data/` **sin composición Wildfires**. En ese caso
`detect_active_fires` devolvía `murphy_partial(swir)` tal cual: no pasa por `_corroborated`,
así que ninguna de las dos puertas que protegen a Huelva y Guadalajara llega a aplicarse.

Y aunque se aplicase, no serviría. `bare_soil_mask` es
`(B8A ≥ 128) & ~potentially_burning(swir)`, pero **todo** píxel de `murphy_partial` pasa
`potentially_burning` por construcción (es su primer test). La puerta es, sobre este camino,
un no-op garantizado: medida sobre los 600 px de foco del este marca el **0 %**.

El fondo del problema es que sin Wildfires no hay con qué corroborar. La SWIR es a la vez
quien detecta el foco y quien tendría que desmentirlo, y a Murphy le falta `B12/B11`, que es
justo la prueba que separa lo caliente de lo brillante.

## Por qué no se arregla con umbrales

El tejado y el frente se solapan en el espectro. Medido por grupo conexo sobre la escena
(este = casco urbano, oeste = incendio):

| | B8A mediana | B12/B8A máx | px (p50) |
| --- | ---: | ---: | ---: |
| Focos del este (falsos) | 164 | 1,54 | 9 |
| Focos del oeste (frente) | 134 | 2,15 | 23 |

Ninguna puerta espectral los separa sin pagarlo caro:

| Puerta probada | Quita del este | Pierde del oeste |
| --- | ---: | ---: |
| `B8A ≥ 128` (suelo desnudo, sin la exención de Murphy) | 62/62 | **75**/139 |
| `B12/B8A ≥ 1,8` | 56/62 | **40**/139 |
| `ratio < 1,8` **y** `B8A ≥ 110` **y** `≤ 20 px` | 55/62 | **28**/139 |

El B8A del frente activo sube al arder (es la razón de ser de la exención de
`potentially_burning`), así que cualquier corte por NIR se lleva el incendio por delante.
Quitar el crecimiento 3×3 tampoco vale: **sube** el recuento de 62 a 67, porque fragmenta
los grupos en vez de borrarlos.

## El arreglo: corroborar por contexto, que es lo único independiente que queda

`_near_burned_area()` en `active_fire.py`, solo en la rama sin Wildfires: un grupo de foco
se queda si toca una zona o está a menos de `MAX_UNCORROBORATED_FIRE_DISTANCE_M` de ella.
Por grupos conexos, como `_corroborated`.

La distancia **no es una constante nueva medida aquí**: ADR-0001 midió el frente de
Guadalajara a ≤ 73 px de la cicatriz (mediana 5 px). Va en metros y no en píxeles porque
las escenas no comparten escala — Madrid-Ávila es 9930 × 6141 y las otras dos 2500 × 1546 —,
y se convierte con el mismo patrón que ya usaba `burned_area._area_px`:
`metres_per_pixel or ASSUMED_METRES_PER_PIXEL`. A los 20 m/px que se asumen sin
georreferencia, los 1500 m son los 73 px de ADR-0001. `ASSUMED_METRES_PER_PIXEL` se mudó de
`burned_area` a `georef` para que `active_fire` pueda importarla sin ciclo.

Se avisa de cuántos focos se han descartado y por qué, como con las nubes y con el suelo
desnudo.

## Medidas

| | Antes | Después |
| --- | ---: | ---: |
| Focos de Madrid-Ávila | 203 | **123** |
| Focos sobre el casco urbano (x > 6951) | 62 | **1** |
| Focos que tocan una zona | 42,4 % | **69,9 %** |
| Píxeles de foco dentro de la superficie quemada | 83,6 % | **90,2 %** |
| Focos fuera de la superficie quemada | 117 | **37** |
| Zonas | 33 | 33 |

**Huelva y Guadalajara no se mueven ni un píxel**: tienen Wildfires, así que no entran por
esta rama. Las dos filas de `docs/results/validacion.md` salen idénticas.

De los 139 focos del oeste se pierden 19, y **no son frente**: tienen la misma firma de
tejado que los del este (B8A 148–174, `B12/B8A` 1,43–1,68, 4–71 px) y están sobre pueblos
sueltos de la mitad oeste, a 426–1806 px de la cicatriz. Es decir, el filtro quita 80 falsos
positivos, no 62. La única excepción dudosa es un grupo de 27 px con B8A 106 y
`B12/B8A` 2,28 a 87 px de la cicatriz: firma de fuego de verdad, justo por encima del corte.
Subir el alcance a 100 px lo recupera, pero devuelve también 5 focos del casco urbano.

## Qué tests lo fijan

- `test_swir_fire_far_from_every_zone_is_dropped_without_wildfires`
- `test_swir_fire_just_outside_the_zone_is_kept_as_the_advancing_front` (ADR-0001: el foco
  de fuera de la cicatriz es el frente, y tiene que seguir saliendo)

## Dos tests cambiaron de premisa

`test_without_wildfires_fires_come_from_swir_with_low_confidence` y
`test_cli_paints_active_fires_on_the_preview` pintaban un foco sobre vegetación intacta y
**sin cicatriz ninguna**: una escena que no puede existir, porque un fuego que arde deja
cicatriz. Es el mismo cambio de premisa que hizo
`docs/fixes/focos-debiles-sobre-suelo-desnudo.md` con los suyos. Ahora pintan la cicatriz y
el foco en su borde.

## Lo que queda abierto

El foco del este que sobrevive (x 8126, y 5383, 7 px) está sobre labrantío recién arado
junto a un pueblo, y lo corrobora la **zona 20, que es un falso positivo de la superficie
quemada**: `burned_area` deja 15 152 px de "cicatriz" sobre suelo agrícola en la ventana
este. El defecto es de otro módulo y esta puerta no puede verlo: si la cicatriz se equivoca,
el foco que se apoya en ella hereda el error.
