# AGENTS.md

Hackathon de 18h, equipo de 4 personas, cada una trabajando con agentes de IA. El trabajo se coordina mediante GitHub Issues.

## Agent skills

### Issue tracker

Issues y specs viven en GitHub Issues de este repo (`gh` CLI). See `docs/agents/issue-tracker.md`.

### Triage labels

Etiquetas por defecto: `needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`. See `docs/agents/triage-labels.md`.

### Domain docs

Single-context: un `CONTEXT.md` y `docs/adr/` en la raíz. See `docs/agents/domain.md`.

### Fixes

Diagnósticos de bugs ya arreglados en `docs/fixes/`: síntoma, causa medida, arreglo y qué
tests lo fijan. Antes de tocar los umbrales de `false_positives.py` o la limpieza morfológica
de `burned_area.py`, lee `docs/fixes/suelo-desnudo-y-frente-partido.md`; antes de tocar la
decodificación de la Wildfires, `docs/fixes/focos-debiles-sobre-suelo-desnudo.md`.

### Research

Notas de investigación en `docs/research/`. Antes de fijar el enfoque técnico, lee `docs/research/sentinel2-rgb-fire-sota.md`: estado del arte de delineación de área quemada y detección de fuego activo sobre los composites RGB ya renderizados de `data/`. El veredicto de qué construir está en §0; lo que **no** es posible con estas entradas, en §7.
