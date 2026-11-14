# Evaluación de datasets

## 1. ¿Qué da cada uno y dónde entra en la app?

| Dataset | ¿Qué da? | ¿Dónde entra en la app? | Veredicto |
|---|---|---|---|
| 🛰️ **NASA POWER** | Clima: temperatura, lluvia, humedad del suelo en raíces, heladas, sol, viento, humedad del aire (con esto se calcula el agua que pide un cultivo) | **Todas las pantallas**: clima por mes, calor extremo, heladas, agua que necesita cada cultivo, sequías históricas | ✅ **Base de la app** |
| 🛰️ **GPM (IMERG)** | Lluvia con más detalle y casi en tiempo real | Inicio ("Lluvia del mes") | 🟡 Mejora |
| 🛰️ **MODIS** | Qué tan verde está la vegetación (NDVI), temperatura del suelo, evaporación | Inicio ("Siembras alrededor"); historial de cómo le fue a la zona cada año | 🟡 Mejora atractiva |
| 🛰️ **Landsat** | Fotos detalladas donde se distingue cada parcela; también NDVI | Ver el estado de la parcela del agricultor | ⚪ Extra (pesado) |
| 🛰️ **ECOSTRESS** | Si las plantas tienen sed o calor (temperatura de las plantas) | Alerta de estrés de la parcela | ⚪ Extra (datos irregulares) |
| 🛰️ **GRACE-FO** | Si el agua subterránea de una región grande sube o baja | Contexto en "¿Me alcanza el agua?" y en la presentación | ⚪ Extra (muy poco detalle) |
| 🛰️ **SRTM** | Altura y pendiente del terreno | Riesgo de erosión (no está en el diseño) | ❌ No se necesita |
| 🛰️ **SMAP** *(no estaba en la lista)* | Humedad del suelo medida directo por satélite | Inicio ("Agua en el suelo") y "Mi suelo" | 🟡 Opcional |
| 🌐 **Open-Meteo** | Pronóstico de 16 días y de 6 meses | Inicio (próximos días) y "¿Qué sembrar?" (este año) | ✅ Sí se usa |
| 🌐 **SoilGrids** | Tipo de tierra, materia orgánica, pH | "Mi suelo" | ✅ Sí se usa |

## 2. Versatilidad: ¿qué tan fácil y qué tan detallado?

| Dataset | Detalle (tamaño de cada dato) | Cada cuánto | Desde | Retraso | ¿Cuenta? | Forma de acceso | Dificultad |
|---|---|---|---|---|---|---|---|
| NASA POWER | ~50 km | Hora, día, mes | 1981 | ~3 días | No | API sencilla (JSON) | 🟢 Fácil |
| GPM IMERG | ~10 km | 30 min | 1998 | ~4 horas | Earthdata | Archivos (HDF5/NetCDF) | 🟡 Media |
| MODIS | 250 m (NDVI) – 1 km | 1-16 días | 2000 | Días | Earthdata | Archivos o AppEEARS (extrae puntos) | 🟡 Media |
| Landsat | 30 m | 8-16 días (con nubes, menos) | 1972 | Días | USGS o nube | Imágenes pesadas | 🔴 Difícil |
| ECOSTRESS | 70 m | Irregular (desde la Estación Espacial) | 2018 | Días | Earthdata | AppEEARS | 🔴 Difícil |
| GRACE-FO | ~300 km | Mensual | 2002 | ~2 meses | Earthdata | Archivos | 🟡 Media |
| SRTM | 30 m | Una sola vez (año 2000) | — | — | Earthdata | Archivos | 🟢 Fácil |
| SMAP | 9-36 km | 2-3 días | 2015 | ~1-2 días | Earthdata | Archivos | 🟡 Media |
| Open-Meteo | ~10-30 km | Día | — | Pronóstico | No | API sencilla (JSON) | 🟢 Fácil |
| SoilGrids | 250 m | Fijo (no cambia) | — | — | No | API sencilla (JSON) | 🟢 Fácil |

Nota: MODIS viaja en satélites que ya son viejos; la NASA tiene a VIIRS como su continuación.
