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
