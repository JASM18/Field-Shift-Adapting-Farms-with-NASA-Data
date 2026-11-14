"""Field Shift — herramienta de apoyo para rotación de cultivos con datos de la NASA.

Ejecutar:  .venv/bin/streamlit run app.py
"""
import folium
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from streamlit_folium import st_folium

from src import nasa_power, soil
from src.recommender import SEASONS, best_rotations, crop_fit, load_crops

st.set_page_config(page_title="Field Shift", page_icon="🌱", layout="wide")
st.title("🌱 Field Shift: rotaciones de cultivo con datos de la NASA")
st.caption("Herramienta de apoyo a la decisión. No sustituye el conocimiento del agricultor sobre su parcela.")


@st.cache_data(show_spinner="Consultando NASA POWER…")
def cached_climate(lat, lon):
    return nasa_power.get_climatology(lat, lon)


@st.cache_data(show_spinner="Consultando SoilGrids…")
def cached_soil(lat, lon):
    try:
        return soil.get_topsoil(lat, lon)
    except Exception:
        return {}


@st.cache_data(show_spinner="Descargando serie histórica…")
def cached_series(lat, lon):
    return nasa_power.get_monthly_series(lat, lon)


# ---------- 1. Ubicación ----------
st.header("1. Ubica tu parcela")
if "loc" not in st.session_state:
    st.session_state.loc = (20.6, -100.9)  # Zona agrícola del Bajío (Gto.) como ejemplo

col_map, col_in = st.columns([2, 1])
with col_map:
    m = folium.Map(location=st.session_state.loc, zoom_start=6)
    folium.Marker(st.session_state.loc, tooltip="Parcela").add_to(m)
    out = st_folium(m, height=380, width='stretch', key="map")
    if out and out.get("last_clicked"):
        new = (round(out["last_clicked"]["lat"], 4), round(out["last_clicked"]["lng"], 4))
        if new != st.session_state.loc:
            st.session_state.loc = new
            st.rerun()
with col_in:
    st.write("Haz clic en el mapa o escribe las coordenadas.")
    lat = st.number_input("Latitud", value=float(st.session_state.loc[0]), format="%.4f")
    lon = st.number_input("Longitud", value=float(st.session_state.loc[1]), format="%.4f")
    if (lat, lon) != st.session_state.loc:
        st.session_state.loc = (lat, lon)
        st.rerun()

lat, lon = st.session_state.loc

# ---------- 2. Clima (NASA POWER) ----------
st.header("2. Clima de tu zona (NASA POWER, promedio 2001-2025)")
try:
    clim = cached_climate(lat, lon)
except Exception as e:
    st.error(f"No se pudo consultar NASA POWER: {e}")
    st.stop()

months_es = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]
rain = [clim["PRECTOTCORR"][k] * d for k, d in zip(nasa_power.MONTHS, nasa_power.DAYS_IN_MONTH)]
fig = go.Figure()
fig.add_bar(x=months_es, y=rain, name="Lluvia (mm/mes)", marker_color="#4C8DD6", yaxis="y2")
fig.add_scatter(x=months_es, y=[clim["T2M"][k] for k in nasa_power.MONTHS], name="Temp. media (°C)", line=dict(color="#E0702E", width=3))
fig.add_scatter(x=months_es, y=[clim["T2M_MIN"][k] for k in nasa_power.MONTHS], name="Mínima extrema (°C)", line=dict(color="#7FB3E8", dash="dot"))
fig.update_layout(height=340, margin=dict(t=10, b=10), legend=dict(orientation="h"),
                  yaxis=dict(title="°C"), yaxis2=dict(title="mm", overlaying="y", side="right"))
st.plotly_chart(fig, width='stretch')

seasons = {k: nasa_power.season_summary(clim, v["meses"]) for k, v in SEASONS.items()}
c1, c2 = st.columns(2)
for col, (k, s) in zip((c1, c2), seasons.items()):
    col.metric(f"{SEASONS[k]['nombre']}: lluvia", f"{s['rain_mm']:.0f} mm")
    col.caption(f"Temp. media {s['t_mean']:.1f}°C · días con helada {s['frost_days']:.1f} · humedad de suelo en raíces {s['soil_moisture']:.2f}")

with st.expander("📈 ¿Está cambiando el clima aquí? (tendencia 2001-2024)"):
    if st.button("Calcular tendencia"):
        ser = cached_series(lat, lon)
        years = sorted({k[:4] for k in ser["T2M"]})
        df = pd.DataFrame({
            "Año": [int(y) for y in years],
            "Temp. media anual (°C)": [ser["T2M"][f"{y}13"] for y in years],
            "Lluvia anual (mm)": [ser["PRECTOTCORR"][f"{y}13"] * 365 for y in years],
        }).set_index("Año")
        st.line_chart(df["Temp. media anual (°C)"])
        st.bar_chart(df["Lluvia anual (mm)"])
        half = len(df) // 2
        dt = df.iloc[half:, 0].mean() - df.iloc[:half, 0].mean()
        dr = df.iloc[half:, 1].mean() - df.iloc[:half, 1].mean()
        st.info(f"Segunda mitad vs primera mitad del periodo: {dt:+.2f}°C y {dr:+.0f} mm de lluvia al año.")

# ---------- 3. Suelo ----------
st.header("3. Tu suelo")
sg = cached_soil(lat, lon)
if not sg or sg.get("ph") is None:
    st.warning("SoilGrids no tiene datos aquí (zona urbana o sin cobertura). Captura los datos de tu análisis de suelo.")
else:
    st.success("Valores estimados con SoilGrids (0-30 cm). Si tienes un análisis de laboratorio, corrígelos.")
c1, c2, c3, c4 = st.columns(4)
ph = c1.number_input("pH", 3.5, 10.0, float(sg.get("ph") or 7.0), 0.1)
clay = c2.number_input("Arcilla (%)", 0.0, 100.0, float(sg.get("clay_pct") or 25.0), 1.0)
sand = c3.number_input("Arena (%)", 0.0, 100.0, float(sg.get("sand_pct") or 40.0), 1.0)
soc = c4.number_input("Carbono orgánico (g/kg)", 0.0, 200.0, float(sg.get("soc_g_kg") or 10.0), 0.5)
textura = soil.texture_class(clay, sand)
st.caption(f"Textura estimada: **{textura}**" + (" · Carbono orgánico bajo: prioriza cultivos con mucha biomasa y abonos verdes." if soc < 10 else ""))
soil_info = {"ph": ph, "textura": textura}

# ---------- 4. Prioridades ----------
st.header("4. Tus prioridades")
c1, c2, c3, c4, c5 = st.columns(5)
prio = {
    "agua": c1.slider("💧 Ahorrar agua", 0, 5, 3),
    "suelo": c2.slider("🪱 Salud del suelo", 0, 5, 4),
    "forraje": c3.slider("🐄 Forraje", 0, 5, 2),
    "resiliencia": c4.slider("🔥 Resistir calor/sequía", 0, 5, 3),
}
irrigation = c5.toggle("Tengo riego", value=False)
years = c5.selectbox("Años a planear", [1, 2], index=1)

# ---------- 5. Resultados ----------
st.header("5. Cultivos y rotaciones sugeridas")
crops = load_crops()
fits = {k: [crop_fit(c, seasons[k], soil_info, irrigation) for c in crops] for k in SEASONS}

tabs = st.tabs([f"Aptitud {SEASONS[k]['nombre']}" for k in SEASONS] + ["🔄 Rotaciones"])
for tab, k in zip(tabs, SEASONS):
    with tab:
        rows = sorted(fits[k], key=lambda f: f.score, reverse=True)
        st.dataframe(pd.DataFrame([{
            "Cultivo": f.crop["nombre"], "Aptitud": f.score,
            "Riego necesario (mm)": round(f.water_deficit_mm),
            "A favor": " · ".join(f.reasons), "Alertas": " · ".join(f.warnings),
        } for f in rows]), hide_index=True, width='stretch',
            column_config={"Aptitud": st.column_config.ProgressColumn(min_value=0, max_value=100, format="%.0f")})

with tabs[-1]:
    order = ["PV", "OI"] * years
    rots = best_rotations(fits, order, prio)
    for i, r in enumerate(rots, 1):
        label = " → ".join(f"{c['nombre']} ({k})" for k, c in r.sequence)
        with st.container(border=True):
            st.markdown(f"**Opción {i}** · puntaje {r.total:.0f}/100")
            st.markdown(f"#### {label}")
            m1, m2, m3, m4, m5 = st.columns(5)
            m1.metric("Clima", f"{100 * r.climate:.0f}")
            m2.metric("Salud de suelo", f"{100 * r.soil:.0f}")
            m3.metric("Riego total", f"{r.water_mm:.0f} mm")
            m4.metric("Forraje", f"{100 * r.forage:.0f}")
            m5.metric("Resiliencia", f"{100 * r.resilience:.0f}")
            for n in r.notes:
                st.caption("• " + n)

st.divider()
st.caption("Datos: NASA POWER (clima), ISRIC SoilGrids (suelo). Parámetros de cultivos aproximados — "
           "valida con técnicos locales y con tu experiencia en campo.")
