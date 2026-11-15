// Pantalla "Tus próximos 3 ciclos": planes de rotación A, B y C.
import { pedirApi, conservarUbicacionEnEnlaces } from "./comun.js";

conservarUbicacionEnEnlaces();

const $ = (id) => document.getElementById(id);
const selector = $("ultimo");
const botonesAgua = [...document.querySelectorAll(".opciones-agua button")];
let lamina = 45;

function crear(etiqueta, clase, texto) {
  const el = document.createElement(etiqueta);
  if (clase) el.className = clase;
  if (texto) el.textContent = texto;
  return el;
}

function indicador(titulo, dato) {
  const caja = crear("div", "indicador");
  caja.append(crear("small", "", titulo), crear("strong", dato.tipo, dato.nivel));
  return caja;
}

function tarjetaPlan(p) {
  const caja = crear("article", `plan${p.recomendado ? " recomendado" : ""}`);
  const cabeza = crear("div", "plan-cabeza");
  cabeza.append(crear("h3", "", `Plan ${p.letra} · ${p.titulo}`));
  if (p.recomendado) cabeza.append(crear("span", "insignia", "Recommended"));
  caja.append(cabeza);

  if (!p.aplica) {
    caja.append(crear("p", "nota-chica", p.texto));
    return caja;
  }

  const ciclos = crear("div", "plan-ciclos");
  p.ciclos.forEach((c, i) => {
    if (i) ciclos.append(crear("span", "plan-flecha", "›"));
    const ciclo = crear("div", `plan-ciclo${c.id === "descanso" ? " descanso" : ""}`);
    ciclo.append(crear("strong", "", c.nombre), crear("small", "", c.etiqueta));
    ciclos.append(ciclo);
  });
  caja.append(ciclos);

  const indicadores = crear("div", "plan-indicadores");
  indicadores.append(indicador("Water", p.agua), indicador("Your soil", p.suelo), indicador("In a drought", p.sequia));
  caja.append(indicadores);

  caja.append(crear("p", "", p.texto));
  if (p.aviso) caja.append(crear("p", "plan-aviso", `⚠ ${p.aviso}`));
  return caja;
}


function mostrarAvisoRegion(texto) {
  const el = document.getElementById("aviso-region");
  el.textContent = texto ? `🌎 ${texto}` : "";
  el.hidden = !texto;
}

async function cargar() {
  botonesAgua.forEach((b) => b.setAttribute("aria-checked", Number(b.dataset.cm) === lamina));
  const estado = $("estado");
  estado.hidden = false;
  estado.className = "estado";
  estado.textContent = "Building plans…";
  try {
    const r = await pedirApi("/api/planes", { ultimo: selector.value, lamina_cm: lamina });
    mostrarAvisoRegion(r.aviso_region);
    $("planes").replaceChildren(...r.planes.map(tarjetaPlan));
    estado.hidden = true;
  } catch (error) {
    estado.textContent = error.message;
    estado.classList.add("error");
  }
}

try {
  const cultivos = await (await fetch("/api/cultivos")).json();
  for (const c of [...cultivos, { id: "descanso", nombre: "Nothing (fallow)" }]) {
    const opcion = crear("option", "", c.nombre);
    opcion.value = c.id;
    selector.append(opcion);
  }
  selector.value = new URLSearchParams(location.search).get("ultimo") || "trigo";
  selector.addEventListener("change", cargar);
  botonesAgua.forEach((b) => b.addEventListener("click", () => { lamina = Number(b.dataset.cm); cargar(); }));
  cargar();
} catch {
  $("estado").textContent = "Could not load the crop list.";
  $("estado").classList.add("error");
}
