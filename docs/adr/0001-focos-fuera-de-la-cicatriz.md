# El criterio de focos fuera de la cicatriz es la corroboración, no un porcentaje

La spec pedía que **más del 90 % de los focos activos cayera dentro de la superficie
quemada**. Ese criterio mide la propiedad equivocada: `CONTEXT.md` define el foco activo como
un subconjunto conceptualmente distinto de la superficie quemada, y el motor **avisa** de los
focos de fuera precisamente porque en una escena con el incendio en marcha son lo esperado.
Lo sustituimos por *todo foco activo fuera de la superficie quemada está corroborado en la
SWIR*, y el porcentaje se reporta como medición, no como umbral.

## Lo que se midió

Escenas de `data/`, 15 de octubre de 2026, sobre `main` en `3278d12`.

- **Los focos de fuera son fuego real.** 14 de 15 grupos de Guadalajara y 5 de 6 de Huelva
  pasaban las dos pruebas de Murphy disponibles (`potentially_burning`); el 94 % de sus
  píxeles en Guadalajara, el 100 % con NBR < 0, y 13 de 15 grupos a menos de 73 px del borde
  quemado (mediana: 5 px). No son ruido.
- **Los dos que no corroboraban eran suelo desnudo.** En Huelva, un único grupo de 597 px de
  nivel 3 con B12 242, B8A 240, NBR mediano −0,002 y 0 de 597 pasando Murphy: el **80 % de
  los píxeles de foco que caían fuera de la cicatriz**. En Guadalajara, un grupo de 1 px.
- **El mecanismo que decían los documentos era falso.** En Guadalajara lo que deja el fuego
  fuera de la máscara es la limpieza morfológica más el área mínima de 30 ha (59 % de los
  píxeles; 114 de 193 vuelven a entrar si se desactivan las dos), no las máscaras de falsos
  positivos: el umbral NBR solo descarta el 0,5 %. En Huelva, el test de nube marcaba el
  81 % de los píxeles de fuera —la observación que hacía el README— pero quitarlo recuperaba
  **cero** píxeles: era pasajero, no causa. El frente tiene NBR de cicatriz; lo que no tiene
  es 30 hectáreas.

## El cambio de código

`_corroborated()` descarta un foco de nivel 3–4 cuando **todo** su grupo conexo cumple
`false_positives.bare_soil_mask()` (B8A ≥ 0,20 y ningún píxel que pase Murphy). No introduce
ninguna constante nueva: reutiliza la puerta de suelo desnudo que ya estaba medida en otro
sitio del motor.

| | Huelva | Guadalajara |
| --- | ---: | ---: |
| Focos | 56 → 55 | 52 → 51 |
| Focos que tocan una zona | 89,3 % → **90,9 %** | 71,2 % → **72,5 %** |
| Píxeles de foco dentro de la cicatriz | 87,1 % → **96,8 %** | 56,7 % → 56,8 % |
| Píxeles de foco con NBR < 0 | 95,7 % → **100 %** | 100 % → 100 % |
| Exhaustividad del detector SWIR | 88,3 % → **98,3 %** | 76,9 % → 77,1 % |
| Grupos de nivel 4 | 19 → 19 | 2 → 2 |

## Alternativas descartadas

1. **Bajar el criterio al 70 %** para que cuadrara con el test que existía
   (`assert ... > 0.70`): es ajustar el enunciado al resultado.
2. **Apretar el detector hasta cumplir el 90 %**: cuesta focos auténticos, y
   `docs/results/informe-criterios-evaluacion.md` advierte expresamente de no forzar todos
   los focos a caer dentro de la cicatriz.
3. **Subir `CORROBORATED_MAX_LEVEL` a 3**: concede a una prueba de Murphy parcial (falta
   `B12/B11`, que ninguna composición trae) un veto general sobre las clasificaciones fuertes
   de la Wildfires, que es lo que `docs/fixes/focos-debiles-sobre-suelo-desnudo.md` rechazó
   por principio. La excepción por firma de suelo desnudo es más estrecha y está medida.
4. **Exentar del filtro de 30 ha a las zonas con un foco activo corroborado**: es la causa
   dominante medida, pero redefine *zona* (`CONTEXT.md`: "mancha conexa que supera el área
   mínima cartografiable") y mueve `zone_count`, hectáreas y alertas. Queda como límite
   conocido, no como arreglo.

## Consecuencias

- Un nivel 3–4 ya **no** se mantiene incondicionalmente: la regla "la Wildfires es la fuente
  preferente" tiene ahora una excepción. `test_strong_wildfires_fire_is_kept_without_swir_support`
  cambió su parche sintético, que representaba el fuego fuerte "sin respaldo" con la firma
  exacta del suelo desnudo —una escena que no puede existir—, y
  `test_strong_wildfires_fire_on_bare_soil_is_dropped` fija la excepción.
- El criterio nuevo es independiente de la escena, así que no se rompe con las escenas
  ocultas de la evaluación. El porcentaje sí depende de ella: 90,9 % y 72,5 %.
- `informe-criterios-evaluacion.md` pide congelar método y umbrales antes de pasar a escenas
  no vistas. Este es el último cambio de umbral previsto.
- La implementación deja una dependencia circular entre `active_fire` y
  `false_positives`, sorteada con un import dentro de la función y anotada como deuda
  pendiente en el README.
