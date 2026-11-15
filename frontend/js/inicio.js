// Pantalla de Inicio: saludo, 4 tarjetas de "¿Cómo está tu zona hoy?" y resumen en voz alta.
import { UBICACION, pedirApi, conservarUbicacionEnEnlaces } from "./comun.js";

conservarUbicacionEnEnlaces();
document.getElementById("nombre-lugar").textContent = UBICACION.nombre;

const MESES = ["January", "February", "March", "April", "May", "June", "July",
  "August", "September", "October", "November", "December"];
const hora = new Date().getHours();
document.getElementById("saludo").textContent =
  hora < 12 ? "Good morning" : hora < 19 ? "Good afternoon" : "Good evening";
document.getElementById("nota-comparacion").textContent =
  `Compared with what's normal for ${MESES[new Date().getMonth()]}`;

function crear(etiqueta, clase, texto) {
  const el = document.createElement(etiqueta);
  if (clase) el.className = clase;
  if (texto) el.textContent = texto;
  return el;
}

// Cada tarjeta se carga por separado: las rápidas aparecen sin esperar a las lentas.
const tarjetas = [...document.querySelectorAll(".tarjeta-zona")];
const resultados = new Map();

function encabezado(caja) {
  const titulo = crear("p", "tarjeta-zona-titulo", `${caja.dataset.icono} ${caja.dataset.titulo}`);
  caja.replaceChildren(titulo);
}

for (const caja of tarjetas) {
  encabezado(caja);
  caja.append(crear("p", "tarjeta-zona-descripcion", "Loading…"));

  pedirApi(caja.dataset.ruta)
    .then((dato) => {
      encabezado(caja);
      caja.classList.remove("cargando");
      if (dato.error) {
        caja.classList.add("sin-dato");
        caja.append(crear("p", "tarjeta-zona-descripcion", dato.error));
        return;
      }
      resultados.set(caja, dato);
      caja.classList.add(dato.tipo);
      caja.append(crear("p", "tarjeta-zona-nombre", dato.nombre),
                  crear("p", "tarjeta-zona-descripcion", dato.descripcion));
      for (const aviso of dato.avisos || []) caja.append(crear("p", "tarjeta-zona-aviso", aviso));
      const detalle = crear("p", "tarjeta-zona-detalle", dato.detalle);
      detalle.hidden = true;
      caja.append(detalle);
      caja.addEventListener("click", () => { detalle.hidden = !detalle.hidden; });
    })
    .catch((error) => {
      encabezado(caja);
      caja.classList.remove("cargando");
      caja.classList.add("sin-dato");
      caja.append(crear("p", "tarjeta-zona-descripcion", error.message));
    });
}

// "Escuchar el resumen de hoy": usa la voz del navegador (no necesita internet ni servicios externos)
const botonEscuchar = document.getElementById("escuchar");
if (!("speechSynthesis" in window)) {
  botonEscuchar.hidden = true;
}
botonEscuchar.addEventListener("click", () => {
  if (speechSynthesis.speaking) {
    speechSynthesis.cancel();
    return;
  }
  const partes = [`${document.getElementById("saludo").textContent}. Here is how your area is doing today.`];
  for (const caja of tarjetas) {
    const dato = resultados.get(caja);
    if (!dato) continue;
    partes.push(`${caja.dataset.titulo}: ${dato.nombre}. ${dato.descripcion}.`);
    for (const aviso of dato.avisos || []) partes.push(aviso.replace(/^[^\p{L}\d]+/u, "") + ".");
  }
  if (partes.length === 1) partes.push("I'm still loading the data, try again in a few seconds.");
  const voz = new SpeechSynthesisUtterance(partes.join(" "));
  voz.lang = "en-US";
  voz.rate = 0.95;
  speechSynthesis.speak(voz);
});
