// Pantalla "¿Te alcanza el agua?": hectáreas × lámina asignada contra lo que pide cada cultivo.
import { UBICACION, conservarUbicacionEnEnlaces } from "./comun.js";

conservarUbicacionEnEnlaces();

const $ = (id) => document.getElementById(id);
const hectareas = $("hectareas");
const lamina = $("lamina");
const botonesAgua = [...document.querySelectorAll(".opciones-agua button")];
const destacado = new URLSearchParams(location.search).get("cultivo"); // si viene de "¿Qué sembrar?"

function crear(etiqueta, clase, texto) {
  const el = document.createElement(etiqueta);
  if (clase) el.className = clase;
  if (texto) el.textContent = texto;
  return el;
}

const ICONO = { alcanza: "✓", limitado: "!", falta: "✕", sin_dato: "?" };


function mostrarAvisoRegion(texto) {
  const el = document.getElementById("aviso-region");
  el.textContent = texto ? `🌎 ${texto}` : "";
  el.hidden = !texto;
}

let pendiente;
function recalcular() {
  clearTimeout(pendiente);
  pendiente = setTimeout(calcular, 150); // espera a que el usuario termine de escribir
}

async function calcular() {
  const ha = Number(hectareas.value);
  const cm = Number(lamina.value);
  botonesAgua.forEach((b) => b.setAttribute("aria-checked", Number(b.dataset.cm) === cm));
  if (!(ha > 0) || !(cm > 0)) return;

  const estado = $("estado");
  try {
    const r = await (await fetch(`/api/agua?hectareas=${ha}&lamina_cm=${cm}&lat=${UBICACION.lat}&lon=${UBICACION.lon}`)).json();
    mostrarAvisoRegion(r.aviso_region);
    estado.hidden = true;
    $("disponible").textContent =
      `You have about ${r.disponible_millares.toLocaleString("en-US")} thousand m³ in total`;

    $("lista").replaceChildren(...r.cultivos.map((c) => {
      const li = crear("li", `cultivo-agua ${c.estado}${c.id === destacado ? " destacado" : ""}`);
      const fila = crear("div", "cultivo-agua-fila");
      fila.append(crear("span", "cultivo-agua-icono", ICONO[c.estado]));
      const textos = crear("div", "cultivo-agua-textos");
      textos.append(crear("strong", "", c.nombre));
      const necesita = c.necesita === "n/a" ? "Needs: n/a"
        : `Needs about ${c.necesita} thousand m³` + (c.necesita_min ? ` (minimum ${c.necesita_min})` : "");
      textos.append(crear("small", "", necesita));
      fila.append(textos, crear("span", "cultivo-agua-estado", c.texto));
      li.append(fila);
      if (c.detalle) {
        const detalle = crear("p", "nota-chica", `${c.riegos} irrigations. ${c.detalle} (${c.fuente})`);
        detalle.hidden = c.id !== destacado;
        li.append(detalle);
        li.addEventListener("click", () => { detalle.hidden = !detalle.hidden; });
      }
      return li;
    }));
  } catch {
    estado.hidden = false;
    estado.className = "estado error";
    estado.textContent = "Could not calculate. Check that the server is running.";
  }
}

$("menos").addEventListener("click", () => {
  hectareas.value = Math.max(0.5, Number(hectareas.value) - 1);
  recalcular();
});
$("mas").addEventListener("click", () => {
  hectareas.value = Number(hectareas.value) + 1;
  recalcular();
});
botonesAgua.forEach((b) => b.addEventListener("click", () => {
  lamina.value = b.dataset.cm;
  recalcular();
}));
hectareas.addEventListener("input", recalcular);
lamina.addEventListener("input", recalcular);

calcular();
