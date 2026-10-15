# Fix: el suelo desnudo entraba como cicatriz y el frente partido se borraba

> Vocabulario según `CONTEXT.md`. Base técnica en `docs/research/sentinel2-rgb-fire-sota.md` §4.3.
> Diagnosticado sobre la escena de Huelva, comprobado además en Guadalajara y Madrid-Ávila.

## Síntomas

1. **Falsos positivos**: perímetros pequeños lejos del incendio sobre campo sin quemar. En
   Huelva eran 22 de las 24 zonas: parcelas cosechadas del regadío del Guadiana, dos cortas
   mineras y un casco urbano.
2. **Falsos negativos**: terreno que en la SWIR se ve quemado y quedaba fuera del perímetro,
   sobre todo en el frente bajo la pluma de humo.

## Cómo reproducirlo

```sh
.venv/bin/python -m pytest tests/test_false_positives.py tests/test_burned_area.py -q
```

Los tres tests que fijan este arreglo son
`test_bare_soil_urban_and_farmland_are_not_burned_area` (16 puntos de referencia verificados
a ojo sobre la SWIR y la True Color de Huelva),
`test_bare_soil_test_does_not_reach_the_scar_or_the_active_front` y
`test_the_front_broken_by_smoke_is_one_zone_and_not_a_shower_of_small_ones`.

## Causa 1: el NBR normaliza justo lo que separa la cicatriz del suelo desnudo

El suelo seco, el rastrojo, las cortas mineras y el casco urbano también tienen B12 por
encima del B8A, así que su NBR (−0.05 … −0.10) es el de una cicatriz y el umbral adaptativo
los deja pasar. `non_burnable_mask` solo rechazaba oscuro, vegetación (NDVI-proxy > 0.6),
humo y nube, y ninguno de los cuatro los toca.

Lo que sí los separa es el **nivel absoluto del NIR**, que la diferencia normalizada del NBR
cancela: al arder desaparece la vegetación y el B8A se hunde, mientras que el suelo desnudo
sigue siendo brillante. Medido sobre las zonas de Huelva (p10–p90):

| Rasgo | Cicatriz | Suelo desnudo | Solape |
| --- | ---: | ---: | ---: |
| **B8A** | 88–123 | 146–201 | **2.7 %** |
| Brillo medio | 91–133 | 138–193 | 21.8 % |
| B04 | 59–96 | 97–146 | 19.5 % |
| NBR | −0.26 … −0.07 | −0.11 … −0.06 | 84.6 % |
| NDVI-proxy | 0.09–0.25 | 0.13–0.21 | 99.3 % |

El corte en reflectancia 0.20 (128 DN con la ganancia lineal 2.5 de la composición) conserva
el 92.4 % de la cicatriz y rechaza el 98.6 % del suelo desnudo.

## Causa 2: el frente llega partido y el filtro de área mínima se lo llevaba

No era el rechazo de humo, que en toda la escena de Huelva solo quitaba 3 741 px. Lo que
borraba superficie era la limpieza morfológica: 68 472 px que pasaban el umbral. El humo sube
el NBR justo por encima del corte y las pistas y cortafuegos cortan la cicatriz, así que la
orla del frente queda en trozos por debajo del área mínima cartografiable (30 ha) y
`remove_small_objects` se los llevaba. **18 de los 34 focos activos del frente** caían en
trozos borrados así, y el incendio salía troceado en zonas sueltas en vez de un perímetro.

## El arreglo

- **`false_positives.bare_soil_mask()`**: rechaza `B8A ≥ BURNED_MAX_B8A` (128 DN). Es un test
  solo con la SWIR, así que también protege a quien no aporta la True Color.
- **Exención por `active_fire.potentially_burning()`**: un píxel ardiendo sube el B12 y
  arrastra el B8A, así que el test anterior lo tomaría por suelo desnudo y dejaría el frente
  activo fuera de la superficie quemada que acaba de crear. Quedan exentos los píxeles que
  pasan las dos pruebas de Murphy disponibles (`B12 ≥ 0.15`, `B12/B8A ≥ 1.4`), extraídas de
  `murphy_partial` a su propia función. Un primer intento eximía solo al B12 saturado y
  bajaba Guadalajara de 9/16 a 7/16 focos de nivel ≥ 3 dentro del área: con la prueba de
  Murphy la exención cubre el 93 % de esos píxeles de foco en vez del 71 %, y ninguno de los
  puntos de suelo desnudo de Huelva.
- **El cierre morfológico solo agrupa zonas** (`FRONT_CLOSING_PX`, 7 px): dos trozos a menos
  de esa distancia son la misma zona, pero los píxeles que se cuentan como quemados siguen
  siendo los suyos. Cerrar la propia máscara recomponía igual de bien el frente, pero se
  tragaba las islas sin quemar de dentro e inflaba la superficie de Guadalajara un 17 %
  (334 852 → 392 647 px), y las hectáreas son una cifra de cabecera.

## Medidas, antes y después

| Escena | Zonas | Superficie (px) | Focos dentro | Nivel ≥ 3 dentro |
| --- | ---: | ---: | ---: | ---: |
| Huelva | 24 → **3** | 228 346 → 190 912 | 47 → **50** / 106 | 20 → **21** / 24 |
| Guadalajara | 14 → **4** | 334 852 → 330 639 | 36 → **37** / 56 | 9 / 16 |
| Madrid-Ávila | 122 → **56** | 1 780 781 → 1 777 397 | 80 → **85** / 203 | — |

La superficie de Huelva baja porque se van 31 582 px de suelo desnudo; en las otras dos
escenas queda igual, que es lo que se buscaba: el cierre no inventa superficie.

## Efecto en el informe de validación

`docs/results/validacion.md` está regenerado con `fire-engine validate`. Además de subir los
focos dentro de la superficie quemada, el resultado queda bastante menos sensible al umbral:
la cola de NBR poco negativo que balanceaba el área era, en buena parte, suelo desnudo.

| Escena | Banda de incertidumbre del área (umbral ±0,02) | Nube dentro de la superficie quemada |
| --- | ---: | ---: |
| Huelva | ±21,3 % → **±7,6 %** | 0,3 % → **0,0 %** |
| Guadalajara | ±6,1 % → **±4,9 %** | 0,0 % |
| Madrid-Ávila | ±9,7 % → **±6,1 %** | 0,0 % |

## Un test existente cambió de premisa

`test_cloud_patch_is_not_burned_area_when_true_color_is_given` afirmaba que, sin la True
Color, la nube sintética no se puede descartar. Esa nube es brillante también en el NIR, así
que ahora la saca el test de suelo desnudo con la SWIR sola. El test comprueba en su lugar
que el test de nube de la True Color la reconoce, que es la cobertura que buscaba.

## Lo que sigue abierto

La spec pide que **más del 90 % de los focos activos caiga dentro de la superficie quemada**
(`docs/specs/deteccion-incendios.md`) y Huelva se queda en el 47 %. Es un defecto distinto y
en otro módulo: de los focos que quedan fuera, 25 son de nivel 1–2 y están en el cinturón
minero y urbano del oeste (x 115–370), con `B12/B8A ≈ 1.03` y `B8A ≈ 235`. Es suelo desnudo
brillante que `decode_wildfires` lee como foco débil; los de nivel 4 están dentro 17 de 19.
La misma familia de causa (el suelo desnudo no estaba modelado), otro sitio:
`potentially_burning()` ya existe como puerta para cerrarlo.
