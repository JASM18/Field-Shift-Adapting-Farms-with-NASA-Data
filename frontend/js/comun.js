// Funciones que comparten todas las pantallas.

// Ubicación de la parcela, en este orden:
//   1. La dirección (?lat=29.07&lon=-110.95&nombre=Hermosillo), útil para compartir un enlace
//   2. La que el usuario eligió en el mapa del Inicio (se guarda en este navegador)
//   3. Por defecto: Cajeme, Sonora
const CLAVE_UBICACION = "cropy.ubicacion";
export const UBICACION_POR_DEFECTO = { lat: 27.37, lon: -109.93, nombre: "Cajeme, Sonora" };

function ubicacionGuardada() {
  try {
    const u = JSON.parse(localStorage.getItem(CLAVE_UBICACION));
    return u && Number.isFinite(u.lat) && Number.isFinite(u.lon) ? u : null;
  } catch {
    return null; // navegación privada o almacenamiento bloqueado
  }
}

export function guardarUbicacion(ubicacion) {
  try {
    localStorage.setItem(CLAVE_UBICACION, JSON.stringify(ubicacion));
  } catch { /* sin almacenamiento: se usará solo en esta visita */ }
}

const parametros = new URLSearchParams(location.search);
const desdeDireccion = Number.isFinite(parseFloat(parametros.get("lat"))) && Number.isFinite(parseFloat(parametros.get("lon")))
  ? { lat: parseFloat(parametros.get("lat")), lon: parseFloat(parametros.get("lon")),
      nombre: parametros.get("nombre") || "Chosen location", origen: "direccion" }
  : null;
const guardada = ubicacionGuardada();

export const UBICACION = desdeDireccion
  || (guardada && { ...guardada, origen: "guardada" })
  || { ...UBICACION_POR_DEFECTO, origen: "defecto" };

// Pide datos a nuestro servidor (/api/...). Si falla, lanza un error con un mensaje entendible.
export async function pedirApi(ruta, extra = {}) {
  const consulta = new URLSearchParams({ lat: UBICACION.lat, lon: UBICACION.lon, ...extra });
  const respuesta = await fetch(`${ruta}?${consulta}`);
  if (!respuesta.ok) {
    const cuerpo = await respuesta.json().catch(() => ({}));
    throw new Error(cuerpo.detail || "Could not load the data.");
  }
  return respuesta.json();
}

// Mantiene la ubicación (?lat=..&lon=..) al navegar entre pantallas.
export function conservarUbicacionEnEnlaces() {
  document.querySelectorAll("a[href$='.html']").forEach((a) => {
    a.href = a.getAttribute("href") + location.search;
  });
}

// Solo en desarrollo: recarga la página sola cuando cambia algún archivo.
(async function recargaAutomatica() {
  if (!["localhost", "127.0.0.1"].includes(location.hostname)) return; // solo al programar en tu computadora
  let versionInicial = null;
  setInterval(async () => {
    try {
      const r = await fetch("/dev/version");
      if (!r.ok) return; // en producción no existe esta ruta
      const { version } = await r.json();
      if (versionInicial === null) versionInicial = version;
      else if (version !== versionInicial) location.reload();
    } catch { /* sin conexión al servidor: no hacemos nada */ }
  }, 1000);
})();
