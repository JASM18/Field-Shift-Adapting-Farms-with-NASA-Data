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
- Otra ubicación: `http://localhost:8000/?lat=29.07&lon=-110.95&nombre=Hermosillo`

## Estructura

```
backend/            Servidor en Python (FastAPI)
  main.py           Rutas: /api/... (datos) y las páginas
  red.py            Conexión compartida (IPv4 + reintentos)
  nasa_power.py     NASA POWER: clima diario de 30 años (se guarda en backend/cache/)
  clima.py          Resumen "El clima de tu zona" (reglas ajustables arriba del archivo)
  fuentes_suelo.py  SoilGrids y SRTM (datos fijos, se guardan una vez por punto)
  suelo.py          Pantalla "Así es tu suelo" (reglas ajustables)
frontend/           Páginas (HTML/CSS/JS)
  index.html        Inicio
  clima.html        El clima de tu zona
  suelo.html        Así es tu suelo
  css/estilos.css   Estilos basados en el diseño (docs/diseno/)
  js/               Código de cada pantalla
docs/               Notas, evaluación de datasets, diseño
pruebas/            Scripts de prueba de APIs
```

## Avance de pantallas

| Pantalla | Datos | Estado |
|---|---|---|
| El clima de tu zona | NASA POWER | ✅ Funciona |
| Inicio | NASA POWER, Open-Meteo, MODIS | 🟡 Solo menú |
| ¿Qué puedo sembrar? | Catálogo de cultivos + clima + Open-Meteo | ⏳ Falta catálogo |
| Planear mis próximos ciclos | Reglas de rotación | ⏳ Falta catálogo |
| Mi suelo | SoilGrids, SRTM, NASA POWER | ✅ Funciona |
| ¿Me alcanza el agua? | NASA POWER + FAO-56 | ⏳ |

## Datos

Decisiones y evaluación en `docs/notas.md` y `docs/evaluacion-datasets.md`.
Se usan: NASA POWER, MODIS (ORNL DAAC), SRTM, Open-Meteo, SoilGrids.
