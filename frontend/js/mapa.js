// Mapa interactivo del Inicio (Leaflet + mapas abiertos, sin cuenta ni tarjeta).
// - La primera vez intenta detectar la ubicación con el GPS del celular.
// - Tocar el mapa (o arrastrar el marcador) propone un punto; "Usar este punto" lo guarda
//   y todas las pantallas se recalculan para esa ubicación.
import { UBICACION, guardarUbicacion } from "./comun.js";

const $ = (id) => document.getElementById(id);
const CLAVE_GPS_PREGUNTADO = "cropy.gps-preguntado";
const mensaje = $("mapa-mensaje");

// ---- Capas del mapa ----
const ayer = new Date(Date.now() - 86_400_000).toISOString().slice(0, 10);
const capas = {
  "Satélite": L.tileLayer(
    "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
    { maxZoom: 18, attribution: "Imágenes © Esri" }),
  "Mapa": L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png",
    { maxZoom: 19, attribution: "© OpenStreetMap" }),
  // Imagen de satélite de la NASA de ayer (MODIS, ~250 m): se ve la región, no la parcela
  "NASA MODIS (ayer)": L.tileLayer(
    `https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/MODIS_Terra_CorrectedReflectance_TrueColor/default/${ayer}/GoogleMapsCompatible_Level9/{z}/{y}/{x}.jpg`,
    { maxNativeZoom: 9, maxZoom: 18, attribution: "NASA GIBS · MODIS Terra" }),
};

const mapa = L.map("mapa", { zoomControl: true }).setView([UBICACION.lat, UBICACION.lon], 12);
capas["Satélite"].addTo(mapa);
L.control.layers(capas, null, { position: "topright" }).addTo(mapa);

const icono = L.divIcon({ className: "pin-mapa", html: "📍", iconSize: [34, 34], iconAnchor: [17, 32] });
const marcador = L.marker([UBICACION.lat, UBICACION.lon], { icon: icono, draggable: true, title: "Tu parcela" })
  .addTo(mapa);

// ---- Elegir un punto ----
let propuesto = null;
const redondear = (x) => Math.round(x * 10_000) / 10_000;

function proponer(lat, lon) {
  propuesto = { lat: redondear(lat), lon: redondear(lon) };
  marcador.setLatLng([propuesto.lat, propuesto.lon]);
  $("mapa-punto").textContent = `${propuesto.lat}, ${propuesto.lon}`;
  $("mapa-confirmar").hidden = false;
}

mapa.on("click", (e) => proponer(e.latlng.lat, e.latlng.lng));
marcador.on("dragend", () => {
  const { lat, lng } = marcador.getLatLng();
  proponer(lat, lng);
});
$("cancelar-punto").addEventListener("click", () => {
  propuesto = null;
  marcador.setLatLng([UBICACION.lat, UBICACION.lon]);
  $("mapa-confirmar").hidden = true;
});
$("usar-punto").addEventListener("click", () => propuesto && confirmar(propuesto));

// Nombre del lugar (municipio, estado) con OpenStreetMap; si falla, se usan las coordenadas
async function nombreDelLugar(lat, lon) {
  try {
    const r = await fetch(`https://nominatim.openstreetmap.org/reverse?format=jsonv2&zoom=10&accept-language=es&lat=${lat}&lon=${lon}`);
    const d = await r.json();
    const a = d.address || {};
    const lugar = a.city || a.town || a.village || a.municipality || a.county;
    return [lugar, a.state].filter(Boolean).join(", ") || `${lat}, ${lon}`;
  } catch {
    return `${lat}, ${lon}`;
  }
}

async function confirmar({ lat, lon }) {
  $("usar-punto").disabled = true;
  mensaje.textContent = "Guardando tu parcela…";
  guardarUbicacion({ lat, lon, nombre: await nombreDelLugar(lat, lon) });
  location.href = location.pathname; // recarga sin ?lat=… para que todo use la nueva ubicación
}

// ---- GPS del celular ----
function detectar(automatico) {
  if (!("geolocation" in navigator)) {
    mensaje.textContent = "Tu navegador no permite detectar la ubicación: toca el mapa.";
    return;
  }
  if (!window.isSecureContext) {
    mensaje.textContent = "La ubicación automática necesita HTTPS (funcionará al publicar la app). Toca el mapa.";
    return;
  }
  mensaje.textContent = "Buscando tu ubicación…";
  navigator.geolocation.getCurrentPosition(
    (pos) => {
      const { latitude, longitude } = pos.coords;
      mapa.setView([latitude, longitude], 15);
      if (automatico) {
        confirmar({ lat: redondear(latitude), lon: redondear(longitude) });
      } else {
        proponer(latitude, longitude);
        mensaje.textContent = "¿Es aquí tu parcela? Puedes mover el marcador.";
      }
    },
    () => { mensaje.textContent = "No se pudo obtener tu ubicación: toca el mapa para elegirla."; },
    { enableHighAccuracy: true, timeout: 15_000 },
  );
}

$("mi-ubicacion").addEventListener("click", () => detectar(false));

// Primera visita: preguntar una sola vez por el GPS
if (UBICACION.origen === "defecto") {
  let yaPreguntado = false;
  try { yaPreguntado = localStorage.getItem(CLAVE_GPS_PREGUNTADO) === "si"; } catch { /* sin almacenamiento */ }
  if (!yaPreguntado) {
    try { localStorage.setItem(CLAVE_GPS_PREGUNTADO, "si"); } catch { /* sin almacenamiento */ }
    detectar(true);
  }
}
