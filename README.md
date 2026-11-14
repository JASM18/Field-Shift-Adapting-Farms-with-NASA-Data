# 🌱 Field Shift — NASA Space Apps Challenge 2026

**Reto:** *Field Shift: Adapting Farms with NASA Data*

Herramienta de apoyo a la decisión que ayuda a agricultores a explorar **rotaciones de cultivo**
que protejan la salud del suelo, ahorren agua y se adapten al clima cambiante, combinando
observaciones de la NASA, datos de suelo, características de cultivos y **las prioridades del agricultor**.
No reemplaza su criterio: explica *por qué* recomienda cada opción.

## Cómo correrlo

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/streamlit run app.py
```

## Cómo funciona

1. **Ubicación** → el agricultor marca su parcela en el mapa.
2. **Clima (NASA POWER)** → temperatura, lluvia, humedad de suelo en raíces por mes y por temporada
   (Primavera-Verano / Otoño-Invierno), más la tendencia 2001-2024.
3. **Suelo (SoilGrids)** → pH, textura, carbono orgánico; editable con su análisis de laboratorio.
4. **Prioridades** → ahorrar agua, salud del suelo, forraje, resistencia a calor/sequía; ¿tiene riego?
5. **Resultado** → aptitud de cada cultivo por temporada (con razones y alertas) y las mejores
   rotaciones, evaluadas con reglas agronómicas: no repetir familia, leguminosas después de cultivos
   demandantes de nitrógeno, alternar profundidad de raíz, aportar biomasa.

## Estructura

```
app.py               Interfaz (Streamlit)
src/nasa_power.py    Cliente de la API NASA POWER (sin login)
src/soil.py          Cliente de SoilGrids
src/recommender.py   Aptitud de cultivos + búsqueda de rotaciones
data/crops.json      Base de cultivos (⚠️ valores aproximados, validar)
docs/                Notas, referencias, material de presentación
```

## Datos NASA y para qué sirven

| Dataset | Uso en el proyecto | Estado |
|---|---|---|
| **NASA POWER** | Clima mensual, temporadas, tendencia | ✅ Integrado (API sin login) |
| **GPM (IMERG)** | Lluvia más detallada / eventos extremos | 💡 Siguiente |
| **SMAP** | Humedad de suelo real (no está en la lista, pero es clave) | 💡 Siguiente |
| **MODIS / Landsat (NDVI)** | Vigor de la vegetación, historial de la parcela | 💡 Siguiente |
| **ECOSTRESS** | Estrés hídrico / evapotranspiración | 💡 Opcional |
| **GRACE-FO** | Tendencia del agua subterránea (escasez) | 💡 Opcional (contexto regional) |
| **SRTM** | Pendiente → riesgo de erosión | 💡 Opcional |

Para GPM, SMAP, MODIS, ECOSTRESS y GRACE se necesita cuenta en **NASA Earthdata**
(https://urs.earthdata.nasa.gov/users/new) y la librería `earthaccess`.

## Pendientes del equipo

- [ ] Todos: crear cuenta en NASA Earthdata y Space Apps Connect
- [ ] Subir este proyecto a GitHub y agregar al equipo
- [ ] **Validar `data/crops.json`** con las referencias (SADER, manual de fertilización, guía de rotaciones, Best4Soil)
- [ ] Redactar la problemática (1 párrafo) y el pitch
- [ ] Integrar un dataset extra (sugerido: SMAP o NDVI de MODIS)
- [ ] Mejorar textos para agricultores (lenguaje claro, quizá modo móvil)
- [ ] Desplegar (Streamlit Community Cloud es gratis) y grabar video demo
- [ ] Revisar la Guía de Envío de Proyectos (plazos)

## Referencias agronómicas

- Nutrientes por ciclo agrícola (SADER): https://www.gob.mx/agricultura/articulos/nutrientes-necesarios-para-cada-ciclo-agricola
- Manual técnico de fertilización: https://www.agroecologia.net/wp-content/uploads/2019/01/manual_tec_fertilizacion_vd.pdf
- Guía de asociaciones y rotaciones: https://www.madrid.es/UnidadesDescentralizadas/Educacion_Ambiental/ContenidosBasicos/Publicaciones/HuertoJardineria/Guia_Asociaciones_y_Rotaciones_cultivos.pdf
- Ficha PAE rotación: https://pae.gencat.cat/web/.content/al_alimentacio/al01_pae/05_publicacions_material_referencia/arxius/FichaPAE22_Rotacion.pdf
- Salud del suelo (Best4Soil): https://orgprints.org/id/eprint/43505/7/43505_Best4Soil_Soil-health-practical-information_ES.pdf
