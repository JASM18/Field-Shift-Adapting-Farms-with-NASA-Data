# ¿Qué datos necesita cada pantalla del diseño?

Diseño en `docs/diseno/`. Leyenda: 🛰️ NASA · 🌐 fuente externa · 🧑‍🌾 lo captura el agricultor · 📚 conocimiento agronómico (lo armamos nosotros)

Decisión: usaremos **el pronóstico de 6 meses** y **el de 16 días** (Open-Meteo).

## 1. Inicio
| Elemento | Dato | Fuente |
|---|---|---|
| Ubicación (Cajeme) | Coordenadas de la parcela | 🧑‍🌾 GPS del celular o mapa |
| Agua en el suelo (seca/normal) | Humedad actual vs. normal del mes | 🛰️ NASA POWER (`GWETROOT`) o SMAP |
| Lluvia del mes | Lluvia en lo que va del mes vs. normal | 🛰️ NASA POWER / GPM + 🌐 Open-Meteo (últimos días) |
| Temperatura | Temperatura actual y próximos días vs. normal | 🛰️ NASA POWER + 🌐 Open-Meteo 16 días |
| Siembras alrededor | Qué tan verdes están las parcelas vs. otros años (NDVI) | 🛰️ MODIS (o Landsat) |
| Escuchar resumen | Texto a voz | Función del navegador (no es dato) |

## 2. El clima de tu zona
| Elemento | Dato | Fuente |
|---|---|---|
| Barra por mes | Máxima **promedio** de la tarde | 🛰️ NASA POWER (calcular desde datos diarios) |
| Seco / Lluvias | Lluvia por mes | 🛰️ NASA POWER |
| Posible helada | Días con helada | 🛰️ NASA POWER (`FROST_DAYS`) |
| Calor fuerte / extremo | Días arriba de 35 °C / 38 °C | 🛰️ NASA POWER (datos diarios) |
| Mejor época / Cuidado | Reglas a partir de lo anterior | 📚 |

⚠️ El diseño dice "promedio de 30 años". La climatología de NASA POWER es de 25 años (2001-2025);
para 30 años hay que calcularlo con datos diarios (existen desde 1981). Cambiar el texto o calcularlo.

⚠️ El `T2M_MAX` de la climatología es la máxima **más extrema**, no la de un día normal.
Para la barra hay que promediar las máximas diarias.

## 3. ¿Qué quieres sembrar?
| Elemento | Dato | Fuente |
|---|---|---|
| Lista de cultivos (trigo, cártamo, garbanzo, canola, maíz) | Necesidades de cada cultivo | 📚 INIFAP / SIAP / FAO |
| ¿Conviene? | Clima + humedad actual + pronóstico 6 meses | 🛰️ NASA POWER + 🌐 Open-Meteo estacional |
| Cuándo sembrar | Calendario del cultivo ajustado al clima | 📚 + 🛰️ NASA POWER |
| Agua que necesita | Evapotranspiración × coeficiente del cultivo (método FAO-56) | 🛰️ NASA POWER (datos para calcularla) + 📚 FAO |
| Riesgo en tu zona | Ej. calor en marzo-abril durante el llenado del grano | 🛰️ NASA POWER + 🌐 pronóstico 6 meses |

## 4. Tus próximos 3 ciclos
| Elemento | Dato | Fuente |
|---|---|---|
| Lo último que sembraste | Cultivo anterior | 🧑‍🌾 |
| Planes A/B/C | Reglas de rotación (familias, nitrógeno, agua) | 📚 referencias del equipo |
| Agua / Si hay sequía | Agua de cada cultivo + qué tan seguido hay sequía | 🛰️ NASA POWER (años extremos) |
| Tu suelo (mejora/desgasta) | Reglas de rotación | 📚 |

## 5. Mi suelo
| Elemento | Dato | Fuente |
|---|---|---|
| Humedad | Humedad actual del suelo | 🛰️ NASA POWER (`GWETROOT`) o SMAP |
| Tipo de tierra, materia orgánica, pH | Arcilla/arena, carbono orgánico, pH | 🌐 SoilGrids (ISRIC) |

## 6. ¿Te alcanza el agua?
| Elemento | Dato | Fuente |
|---|---|---|
| Hectáreas | Superficie (o dibujarla en el mapa) | 🧑‍🌾 |
| Agua asignada (lámina) | 30 / 45 / 70 cm | 🧑‍🌾 (la asigna el distrito de riego) |
| Total disponible | hectáreas × lámina (10 ha × 0.45 m = 45 000 m³) | Cálculo |
| Lo que necesita cada cultivo | Evapotranspiración del cultivo − lluvia del ciclo | 🛰️ NASA POWER + 📚 FAO-56 |

## Resumen: datasets que sí usa el diseño
| Dataset | Pantallas | Prioridad |
|---|---|---|
| 🛰️ NASA POWER | Todas | Imprescindible ✅ |
| 🌐 Open-Meteo (16 días y 6 meses) | Inicio, Qué sembrar | Alta ✅ |
| 🌐 SoilGrids | Mi suelo | Alta |
| 🛰️ MODIS (NDVI) | Inicio ("siembras alrededor") | Media |
| 🛰️ GPM | Inicio (lluvia del mes) | Media (mejora la lluvia) |
| 🛰️ SMAP | Inicio, Mi suelo | Opcional (mejora la humedad) |
| 🛰️ ECOSTRESS, GRACE-FO, Landsat | — | Opcionales / extras |
| 🛰️ SRTM | — | No se necesita |
