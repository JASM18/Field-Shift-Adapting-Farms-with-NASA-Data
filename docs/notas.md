# Notas del proyecto, paso a paso

## ¿Qué pide el reto? (Field Shift)

En palabras simples:

> Los agricultores tienen que decidir **qué sembrar en cada temporada**. Hoy es más difícil
> porque el clima está cambiando (más calor, lluvias raras, menos agua) y el suelo se va desgastando.
> Quieren una app que les ayude a decidir usando **datos de satélites de la NASA**.

**Objetivo:** una aplicación para que los agricultores tomen decisiones.

### Concepto clave: rotación de cultivos

No sembrar siempre lo mismo en el mismo terreno, sino ir cambiando. Ejemplo:

- **Año 1:** maíz, que gasta muchos nutrientes del suelo
- **Año 2:** frijol, que le devuelve nitrógeno al suelo
- **Año 3:** otra vez maíz, y el suelo ya se recuperó

Si siembras maíz todos los años, el suelo se cansa, aparecen más plagas y necesitas más fertilizante.
La app debe ayudar a elegir una buena secuencia según el clima, el suelo y lo que el agricultor quiera.

## El camino, en pasos pequeños

1. Entender el problema
2. Entender qué información da cada dataset de la NASA, uno por uno
3. Decidir cuáles datasets nos sirven
4. Definir qué hará la app (qué pregunta y qué responde)
5. Construirla poco a poco

## Pregunta de investigación ✅ (decidida)

> ¿Cómo pueden los agricultores de regiones con climas extremos decidir qué sembrar, cuándo y cómo
> rotar sus cultivos para reducir pérdidas de cosecha por sequía y calor extremo?

(Versión anterior: "...para reducir pérdidas de cosecha y maximizar la calidad de los cultivos?".
Se cambió "calidad" por algo más concreto: sequía y calor extremo.)

Se divide en tres decisiones que la app debe apoyar:

- **¿Qué sembrar?** → cultivos que aguanten el clima de la zona
- **¿Cuándo sembrar?** → la mejor temporada según lluvia y temperatura
- **¿Cómo rotar?** → el orden de cultivos que cuide el suelo

Aclaraciones:

- **Alcance: empezar con Sonora, pero con software escalable** (recomendación de los asesores).
  La app se prueba y se presenta con datos de Sonora, pero se programa para que funcione en
  cualquier lugar con solo cambiar la ubicación (los datos de la NASA son globales).
- **"Calidad de los cultivos"** resume una versión anterior de la pregunta: "para reducir pérdidas
  de cosecha por **sequía y calor extremo** que terminan en **escasez y alza de precios** de los
  alimentos". Es decir: el enfoque está en la sequía y el calor extremo, y el impacto es la
  seguridad alimentaria.

Primera propuesta (descartada): “Con temperaturas cada vez más altas, ¿qué orden de cultivos evita
que un cultivo retrase la siembra del siguiente y le pegue al rendimiento?”

## Estrategia de datos ✅ (decidida)

- **Hackathon:** usar los datos **más sencillos** (APIs sin cuenta y ligeras): NASA POWER, MODIS (ORNL DAAC),
  Open-Meteo, SoilGrids.
- **Si ganamos y el proyecto continúa:** integrar los datos pesados y más detallados (Landsat por parcela, etc.).

## Pendientes para más adelante

- **Catálogo de cultivos:** qué cultivos incluir y qué datos de cada uno (agua, temperatura, calendario).
- **Cómo el programa arma los planes de rotación** (A/B/C) a partir de fuentes como INIFAP.

## Datasets

### NASA POWER ✅ (calor y sequía)

- **Qué es:** el clima de cualquier punto del planeta, día por día, desde 1981, a partir de satélites
  y modelos de la NASA.
- **Datos útiles:** temperatura (media, máxima, mínima), lluvia, humedad del suelo en la zona de
  raíces, días con helada, radiación solar, humedad del aire.
- **Ventajas:** gratis, sin cuenta, global, fácil de usar (se consulta por coordenadas).
- **Limitación:** cada dato cubre una zona de unos 50 × 50 km, no la parcela exacta.
- **Responde a:** ¿qué sembrar? (qué cultivos aguantan ese calor y esa lluvia) y ¿cuándo? (en qué
  meses llueve y no hace calor extremo).
- Explorar a mano: https://power.larc.nasa.gov/data-access-viewer/
- **Dos formas de obtener los datos:**
  1. *Página web (Data Access Viewer):* para explorar a mano y descargar CSV/Excel.
  2. *API (la usará la app):* el programa pide los datos por internet en el momento, sin descargar nada antes.
     Ejemplo (Valle del Yaqui, Sonora): https://power.larc.nasa.gov/api/temporal/daily/point?parameters=T2M_MAX,PRECTOTCORR&community=AG&latitude=27.37&longitude=-109.93&start=20261101&end=20261111&format=JSON
- **Fecha más reciente:** ~3 días de retraso (el 14 nov 2026 había datos hasta el 11 nov). Los días sin
  datos aún aparecen como `-999`. Los datos de los últimos meses son preliminares.
- **Ojo:** si la API falla de vez en cuando (respuesta vacía), hay que reintentar; la app debe manejarlo.
- **Tipos de consulta:** `climatology` (promedio de varios años por mes), `monthly` (cada mes de cada año),
  `daily` (cada día), `hourly` (cada hora).
- **Ojo:** los promedios esconden los años extremos. Para sequía y calor extremo importan los años malos.

#### Lo que dice NASA POWER del Valle del Yaqui, Sonora (27.37, -109.93)

- Lluvia promedio: ~394 mm al año; el 75 % cae en julio-septiembre. De marzo a junio casi no llueve.
- Calor: temperatura media de 31 °C en junio; máximas de más de 43 °C de mayo a septiembre.
- **Sequías:** 2020 (186 mm) y 2023 (193 mm), la mitad de lo normal.
- **Calentamiento:** temperatura media de 24.7 °C (2001-2012) → 25.5 °C (2014-2025), +0.8 °C.
  Máximas récord en 2023 (46.0 °C) y 2024 (46.6 °C).

### Hueco de datos y pronósticos (fuera de NASA POWER)

NASA POWER **no tiene pronóstico** y le faltan los últimos ~3 días. Opciones:

| Necesidad | Opción | Notas |
|---|---|---|
| Lluvia de los últimos días | **GPM IMERG "Early"** (NASA) | Retraso de ~4 horas; requiere cuenta Earthdata |
| Pronóstico 1-16 días | **Open-Meteo** (`api.open-meteo.com/v1/forecast`) | Gratis, sin cuenta (uso no comercial). Probado con Sonora ✅ |
| Pronóstico por temporada (hasta ~6 meses) | **Open-Meteo Seasonal** (modelo ECMWF SEAS5) | Gratis, sin cuenta. Probado ✅ |
| Alternativa con soporte | **Meteomatics** | Gratis para participantes (Ofertas Globales del correo) |
| Pronóstico estacional de la NASA | **GEOS-S2S** | Existe, pero son archivos pesados; difícil para un hackathon |

**Idea clave:** para decidir *qué sembrar y cuándo* importa más el **pronóstico por temporada** (meses)
que el del clima de mañana. El de 16 días sirve para decisiones del día a día (riego, fecha exacta de siembra).
Space Apps permite usar datos que no son de la NASA, siempre que el proyecto use datos de la NASA.

### GPM (lluvia) 🟡 prioridad media

- **Qué es:** una red de satélites (NASA + Japón) que mide la lluvia en todo el mundo.
  El producto que nos interesa se llama **IMERG**.
- **Detalle:** cuadros de ~10 × 10 km (NASA POWER: ~50 × 50 km), cada 30 minutos, desde 1998.
- **Versiones:** *Early* (~4 horas de retraso), *Late* (~14 horas), *Final* (~3.5 meses, la más precisa).
- **Acceso:** requiere cuenta de **NASA Earthdata**. No es una API sencilla como NASA POWER: se descargan
  archivos (HDF5/NetCDF) y se extrae el punto. En Python se usa la librería `earthaccess`.
- **Para qué en la app:** tarjeta "Lluvia del mes" del Inicio, con más detalle y más reciente.
- **Por qué importa en Sonora:** las lluvias de verano (monzón) son tormentas muy locales; con cuadros de
  50 km se pueden "perder", con 10 km se ven mejor.
- **Conclusión:** NASA POWER alcanza para el clima histórico; GPM es una mejora, no algo indispensable.

### MODIS (vegetación / NDVI) 🟡 → probado ✅

- **Qué es:** sensor en los satélites Terra y Aqua. El dato clave es el **NDVI**: qué tan verde está la
  vegetación (0 = suelo desnudo, ~0.8 = cultivo muy verde y sano).
- **Detalle:** cuadros de 250 m, una imagen cada 16 días, desde el año 2000. Retraso ~1 mes.
- **Acceso SIN cuenta:** servicio de la NASA ORNL DAAC (API JSON). Ejemplo:
  https://modis.ornl.gov/rst/api/v1/MOD13Q1/subset?latitude=27.37&longitude=-109.93&band=250m_16_days_NDVI&startDate=A2025049&endDate=A2025049&kmAboveBelow=2&kmLeftRight=2
  (valores × 0.0001 = NDVI). El servidor es lento: hay que reintentar.
- **Prueba, Valle del Yaqui, 18 de febrero (pico del trigo), área de ~5 × 5 km:**

| Año | NDVI promedio | Superficie verde |
|---|---|---|
| 2019 | 0.80 | 96 % |
| 2020 | 0.77 | 96 % |
| 2021 | 0.74 | 89 % |
| 2022 | 0.78 | 94 % |
| 2023 | 0.73 | 88 % |
| 2024 | 0.80 | 97 % |
| **2025** | **0.29** | **13 %** |
| 2026 | 0.68 | 79 % |

  En 2025 casi no hubo siembras: coincide con la sequía 2024-2025 y las presas muy bajas.
- **Para qué en la app:** tarjeta "Siembras alrededor" del Inicio; mostrar el impacto de la sequía.

### Landsat (fotos detalladas) ⚪ extra → disponible ✅

- **Qué es:** satélites Landsat 8 y 9 (NASA + USGS). Fotos donde se distingue **cada parcela**.
- **Detalle:** cuadros de 30 m (MODIS: 250 m). Combinando Landsat 8 y 9 pasa cada ~8 días. Desde 1972.
- **Acceso SIN cuenta:** catálogo de Microsoft Planetary Computer (colección `landsat-c2-l2`).
- **Prueba (Valle del Yaqui, dic 2025 – nov 2026):** al menos 40 imágenes; 25 con menos de 20 % de nubes.
  En temporada de lluvias hay imágenes inservibles (29 sep 2026: 99.99 % nubes).
- **Lo difícil:** cada imagen cubre ~185 × 185 km y pesa mucho; para sacar el NDVI de una parcela hay que
  leer solo un pedazo (librería `rasterio`) y descartar imágenes con nubes.
- **Para qué en la app:** ver qué tan verde está **la parcela del agricultor** (no solo la zona) y su historial.
- **Conclusión:** útil pero más trabajo; MODIS ya cubre "Siembras alrededor" a nivel zona.

## Ofertas Globales (patrocinadores)

Decisión del equipo: **no usar las que pidan tarjeta de crédito.**

### ECOSTRESS (estrés de las plantas) ❌ descartado para el hackathon

- **Qué es:** sensor en la Estación Espacial Internacional que mide la **temperatura de las plantas**.
  Una planta con sed cierra sus poros, deja de "sudar" y se calienta: así se detecta el estrés por agua.
- **Dato útil:** **Índice de Estrés por Evaporación (ESI)**, producto `ECO4ESIPTJPL`, y eficiencia en el uso
  del agua (`ECO4WUE`).
- **Detalle:** cuadros de 70 m, casi a nivel parcela. Desde 2018.
- **Problema:** la Estación Espacial no pasa a horario fijo, así que los datos son **irregulares**
  (unos días sí, otros no, y a horas distintas). Difícil armar una serie confiable.
- **Acceso SIN cuenta:** sí está en el servicio ORNL DAAC (el mismo de MODIS). Al probarlo el 14 nov 2026 el
  servidor respondió 503 (no disponible); **falta verificar cuántas fechas hay para Sonora**.
- **Alternativa sencilla:** MODIS tiene evapotranspiración (`MOD16A2GF`, 500 m, cada 8 días, sin huecos)
  en el mismo servicio.
- **Conclusión:** **descartado** para el hackathon: datos irregulares, la API no respondió y la página web
  solo da archivos `.nc` para descargar (con aceptación de licencia). Se puede retomar en la siguiente fase.

**Dónde consultamos:** *ORNL DAAC MODIS/VIIRS Web Service* (API REST, responde JSON, sin descargar archivos):
https://modis.ornl.gov/data/modis_webservice.html · Es distinto de la página web de descarga de ECOSTRESS.
⚠️ El servidor es lento y a veces se cae (MODIS también viene de ahí): la app debe guardar los datos una vez
al día y tener un plan B.

**Hallazgo:** el servicio ORNL DAAC (sin cuenta) también tiene **SMAP** (`SPL3SMP_E`, humedad del suelo, 9 km,
diario) y **VIIRS** (`VNP13A1`, NDVI, el reemplazo de MODIS).
