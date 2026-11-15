// Funciones que comparten todas las pantallas.

// Ubicación de la parcela. Por ahora: Cajeme, Sonora.
// Se puede probar otra zona agregando a la dirección: ?lat=29.07&lon=-110.95&nombre=Hermosillo
const parametros = new URLSearchParams(location.search);
export const UBICACION = {
  lat: Number(parametros.get("lat")) || 27.37,
  lon: Number(parametros.get("lon")) || -109.93,
  nombre: parametros.get("nombre") || "Cajeme, Sonora",
};

// Pide datos a nuestro servidor (/api/...). Si falla, lanza un error con un mensaje entendible.
export async function pedirApi(ruta, extra = {}) {
  const consulta = new URLSearchParams({ lat: UBICACION.lat, lon: UBICACION.lon, ...extra });
  const respuesta = await fetch(`${ruta}?${consulta}`);
  if (!respuesta.ok) {
    const cuerpo = await respuesta.json().catch(() => ({}));
    throw new Error(cuerpo.detail || "No se pudieron cargar los datos.");
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
