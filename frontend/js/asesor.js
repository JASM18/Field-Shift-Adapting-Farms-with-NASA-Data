// Chat con el asesor de IA. La conversación vive solo en esta página (no se guarda).
import { UBICACION, conservarUbicacionEnEnlaces } from "./comun.js";

conservarUbicacionEnEnlaces();

const $ = (id) => document.getElementById(id);
const conversacion = $("conversacion");
const entrada = $("pregunta");
const mensajes = []; // [{rol, texto}]
let ocupado = false;

function crear(etiqueta, clase, texto) {
  const el = document.createElement(etiqueta);
  if (clase) el.className = clase;
  if (texto) el.textContent = texto;
  return el;
}

// Convierte el formato sencillo del asesor (**negritas**, listas con "-" o "1.") en elementos,
// sin usar innerHTML con texto del modelo (así no se puede inyectar HTML).
function formatear(texto) {
  const fragmento = document.createDocumentFragment();
  let lista = null;
  for (const linea of texto.split("\n")) {
    const vineta = linea.match(/^\s*(?:[-*•]|\d+[.)])\s+(.*)/);
    if (!linea.trim()) { lista = null; continue; }
    const destino = vineta
      ? (lista ??= fragmento.appendChild(crear(/^\s*\d/.test(linea) ? "ol" : "ul"))).appendChild(crear("li"))
      : (lista = null, fragmento.appendChild(crear("p")));
    const contenido = vineta ? vineta[1] : linea;
    contenido.split(/(\*\*[^*]+\*\*)/g).forEach((parte) => {
      if (parte.startsWith("**") && parte.endsWith("**")) destino.append(crear("strong", "", parte.slice(2, -2)));
      else if (parte) destino.append(parte.replace(/^#+\s*/, ""));
    });
  }
  return fragmento;
}

function hablar(texto, boton) {
  if (speechSynthesis.speaking) { speechSynthesis.cancel(); return; }
  const voz = new SpeechSynthesisUtterance(texto.replace(/[*#•]/g, ""));
  voz.lang = "es-MX";
  voz.rate = 0.95;
  boton.textContent = "⏹ Detener";
  voz.onend = voz.onerror = () => { boton.textContent = "🔊 Escuchar"; };
  speechSynthesis.speak(voz);
}

function agregar(rol, texto, consultas = []) {
  const burbuja = crear("div", `burbuja ${rol === "user" ? "usuario" : "asesor"}`);
  if (rol === "user") burbuja.append(crear("p", "", texto));
  else {
    burbuja.append(formatear(texto));
    const pie = crear("div", "burbuja-pie");
    if (consultas.length) pie.append(crear("small", "", `Consulté: ${consultas.join(", ")}`));
    if ("speechSynthesis" in window) {
      const boton = crear("button", "burbuja-voz", "🔊 Escuchar");
      boton.type = "button";
      boton.addEventListener("click", () => hablar(texto, boton));
      pie.append(boton);
    }
    burbuja.append(pie);
  }
  conversacion.append(burbuja);
  burbuja.scrollIntoView({ behavior: "smooth", block: "start" });
  return burbuja;
}

async function preguntar(texto) {
  texto = texto.trim();
  if (!texto || ocupado) return;
  ocupado = true;
  $("sugerencias").hidden = true;
  entrada.value = "";
  agregar("user", texto);
  mensajes.push({ rol: "user", texto });
  const pensando = agregar("assistant", "Revisando los datos de tu zona…");
  pensando.classList.add("pensando");

  try {
    const respuesta = await fetch("/api/asesor", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ mensajes, lat: UBICACION.lat, lon: UBICACION.lon, nombre: UBICACION.nombre }),
    });
    const datos = await respuesta.json().catch(() => ({}));
    pensando.remove();
    if (!respuesta.ok) throw new Error(datos.detail || "El asesor no respondió.");
    agregar("assistant", datos.texto, datos.consultas);
    mensajes.push({ rol: "assistant", texto: datos.texto });
  } catch (error) {
    pensando.remove();
    agregar("assistant", `⚠ ${error.message}`);
    mensajes.pop(); // la pregunta sin respuesta no se manda en la siguiente
  } finally {
    ocupado = false;
    entrada.focus();
  }
}

$("formulario").addEventListener("submit", (e) => { e.preventDefault(); preguntar(entrada.value); });
document.querySelectorAll("#sugerencias button").forEach((b) => b.addEventListener("click", () => preguntar(b.textContent)));

// Dictado por voz (si el navegador lo permite)
const Reconocimiento = window.SpeechRecognition || window.webkitSpeechRecognition;
const microfono = $("microfono");
if (!Reconocimiento) {
  microfono.hidden = true;
} else {
  const rec = new Reconocimiento();
  rec.lang = "es-MX";
  rec.interimResults = false;
  rec.onresult = (e) => { entrada.value = e.results[0][0].transcript; preguntar(entrada.value); };
  rec.onend = () => microfono.classList.remove("escuchando");
  microfono.addEventListener("click", () => { microfono.classList.add("escuchando"); rec.start(); });
}
