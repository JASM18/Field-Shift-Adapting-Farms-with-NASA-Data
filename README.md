# 🌱 Field Shift — NASA Space Apps Challenge 2026

**Reto:** *Field Shift: Adapting Farms with NASA Data*

**Pregunta de investigación:** ¿Cómo pueden los agricultores de regiones con climas extremos decidir qué
sembrar, cuándo y cómo rotar sus cultivos para reducir pérdidas de cosecha por sequía y calor extremo?

Página web (pensada para celular) que ayuda a los agricultores a decidir con datos de la NASA.
Empezamos con **Sonora**, pero el software funciona para cualquier ubicación.

## Cómo correrla

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
DEV=1 .venv/bin/uvicorn backend.main:app --reload --timeout-graceful-shutdown 3 --host 0.0.0.0 --port 8000
```

- En la computadora: http://localhost:8000
- En el celular (mismo WiFi): `http://<IP de la computadora>:8000`
- Con `DEV=1` la página se recarga sola cada vez que cambia un archivo.
- Ubicación: el Inicio la detecta con el GPS (requiere HTTPS o localhost) o se elige tocando el mapa; se guarda en el navegador.
- Otra ubicación por enlace: `http://localhost:8000/?lat=29.07&lon=-110.95&nombre=Hermosillo`

## Fuera de Sonora (escalabilidad)

El catálogo de cultivos (fechas de siembra, agua, rendimiento, riesgos de manejo) es del INIFAP para **Sonora**
(región definida en `data/cultivos.json` → `_info.region`). Si la parcela está fuera:
- La **fecha de siembra se calcula con el clima local** (30 años de NASA POWER): se prueban 24 fechas y se elige
  la que da más días en la temperatura ideal del cultivo, sin heladas ni calor extremo, aprovechando la lluvia.
- No se muestran los riesgos escritos para Sonora; sí los calculados con el clima local.
- Agua y rendimiento se marcan como "referencia de Sonora", y las pantallas muestran un aviso 🌎.

## Asesor con IA

Necesita un archivo `.env` en la raíz con `ANTHROPIC_API_KEY=...` (está en `.gitignore`: **nunca subirlo**).
Quien clone el repositorio no tendrá la llave: la AI dirá «no está configurada» y el resto de la app funciona igual.
Para activarla: copiar `.env.example` como `.env`, pegar la llave (pedirla por un medio privado, no por GitHub
ni grupos) y reiniciar el servidor. Lo más sencillo para el equipo: usar la app publicada, que ya tiene la llave.
Límite: 30 preguntas por persona por hora (`backend/asesor.py`).

## Estructura

```
backend/            Servidor en Python (FastAPI)
  main.py           Rutas: /api/... (datos) y las páginas
  red.py            Conexión compartida (IPv4 + reintentos)
  nasa_power.py     NASA POWER: clima diario de 30 años (se guarda en backend/cache/)
  clima.py          Resumen "El clima de tu zona" (reglas ajustables arriba del archivo)
  fuentes_suelo.py  SoilGrids y SRTM (datos fijos, se guardan una vez por punto)
  suelo.py          Pantalla "Así es tu suelo" (reglas ajustables)
  open_meteo.py     Open-Meteo: días recientes y pronóstico de 16 días
  modis.py          MODIS (ORNL DAAC): superficie verde alrededor de la parcela
  inicio.py         Tarjetas del Inicio "¿Cómo está tu zona hoy?" (reglas ajustables)
  sembrar.py        Pantalla "¿Qué quieres sembrar?": cruza catálogo + clima + pronóstico (reglas ajustables)
  agua.py           Pantalla "¿Te alcanza el agua?": hectáreas × lámina contra el agua de cada cultivo
  planes.py         Pantalla "Tus próximos 3 ciclos": planes de rotación A/B/C (reglas ajustables)
  asesor.py         Asesor con IA (Claude Sonnet 5.5): responde usando las mismas funciones como herramientas
frontend/           Páginas (HTML/CSS/JS)
  index.html        Inicio
  clima.html        El clima de tu zona
  suelo.html        Así es tu suelo
  sembrar.html      ¿Qué quieres sembrar?
  agua.html         ¿Te alcanza el agua?
  planes.html       Tus próximos 3 ciclos
  asesor.html       Pregúntale a tu asesor (chat con IA, voz)
  css/estilos.css   Estilos basados en el diseño (docs/diseno/)
  js/               Código de cada pantalla (mapa.js: mapa interactivo y GPS del Inicio)
data/cultivos.json  Catálogo de 7 cultivos (INIFAP, FAO-24, ECOCROP, SIAP), con fuente en cada dato
docs/               Notas, evaluación de datasets, diseño
pruebas/            Scripts de prueba de APIs
```

## Avance de pantallas

| Pantalla | Datos | Estado |
|---|---|---|
| El clima de tu zona | NASA POWER | ✅ Funciona |
| Inicio | NASA POWER, Open-Meteo, MODIS | ✅ Funciona |
| ¿Qué puedo sembrar? | Catálogo de cultivos + NASA POWER + Open-Meteo (6 meses) + SoilGrids | ✅ Funciona |
| Planear mis próximos ciclos | Catálogo (nitrógeno, agua, familia) + clima de NASA POWER | ✅ Funciona |
| Mi suelo | SoilGrids, SRTM, NASA POWER | ✅ Funciona |
| ¿Me alcanza el agua? | Catálogo de cultivos (agua del INIFAP) | ✅ Funciona |
| Asesor con IA | Claude Sonnet 5.5 + todas las fuentes anteriores (como herramientas) | ✅ Funciona |

## Datos

Decisiones y evaluación en `docs/notas.md` y `docs/evaluacion-datasets.md`.
Se usan: NASA POWER, MODIS (ORNL DAAC), SRTM, Open-Meteo, SoilGrids.
