// Pantalla "¿Qué quieres sembrar?": botones de cultivos y evaluación del elegido.
import { pedirApi, conservarUbicacionEnEnlaces } from "./comun.js";

conservarUbicacionEnEnlaces();

const $ = (id) => document.getElementById(id);
const estado = $("estado");
const resultado = $("resultado");

function crear(etiqueta, clase, texto) {
  const el = document.createElement(etiqueta);
  if (clase) el.className = clase;
  if (texto) el.textContent = texto;
  return el;
}

function lista(contenedor, textos) {
  contenedor.replaceChildren(...textos.map((t) => crear("li", "", t)));
}

async function mostrar(cultivoId) {
  document.querySelectorAll(".chip").forEach((b) => b.setAttribute("aria-selected", b.dataset.id === cultivoId));
  // Recordar el cultivo en la dirección (se puede compartir el enlace)
  const url = new URL(location);
  url.searchParams.set("cultivo", cultivoId);
  history.replaceState(null, "", url);

  estado.hidden = false;
  estado.className = "estado";
  estado.textContent = "Analizando clima, suelo y pronóstico…";
  resultado.hidden = true;

  try {
    const r = await pedirApi("/api/sembrar", { cultivo: cultivoId });

    $("veredicto").className = `veredicto ${r.tipo}`;
    $("veredicto-titulo").textContent = r.veredicto;
    $("veredicto-razon").textContent = r.razon;
    lista($("veredicto-avisos"), r.avisos);

    $("siembra-texto").textContent = r.siembra.texto;
    $("siembra-meses").replaceChildren(...r.siembra.meses.map((m) => {
      const li = crear("li", m.clase, m.inicial);
      li.title = m.mes;
      return li;
    }));
    const notas = [r.siembra.nota !== "n/a" ? r.siembra.nota : "", ...r.siembra.otras.map((o) => `También: ${o}.`)];
    $("siembra-nota").textContent = notas.filter(Boolean).join(" ");

    const a = r.agua;
    $("agua-texto").textContent = a.m3_ha === "n/a" ? "n/a"
      : `${a.nivel}: unos ${a.m3_ha.toLocaleString("es-MX")} m³ por hectárea (${a.lamina_cm} cm), ${a.riegos} riegos`;
    $("agua-barra").style.width = `${a.porcentaje ?? 0}%`;
    $("agua-detalle").textContent = a.detalle;

    lista($("riesgos"), r.riesgos.length ? r.riesgos : ["n/a"]);
    $("este-anio").textContent = r.este_año || "El pronóstico de 6 meses todavía no alcanza esta temporada.";

    $("bueno-saber").textContent = r.bueno_saber;
    $("rendimiento").textContent = `Rendimiento esperado: ${r.rendimiento}. Ciclo: ${r.ciclo}.`;

    const irAgua = new URL("agua.html", location);
    new URLSearchParams(location.search).forEach((v, k) => irAgua.searchParams.set(k, v));
    irAgua.searchParams.set("cultivo", cultivoId);
    $("ir-agua").href = irAgua;
    const irPlanes = new URL("planes.html", location);
    new URLSearchParams(location.search).forEach((v, k) => { if (k !== "cultivo") irPlanes.searchParams.set(k, v); });
    irPlanes.searchParams.set("ultimo", cultivoId);
    $("ir-planes").href = irPlanes;

    $("detalle-clima").textContent = r.detalle_clima;
    lista($("fuentes"), r.fuentes);

    estado.hidden = true;
    resultado.hidden = false;
  } catch (error) {
    estado.textContent = error.message;
    estado.classList.add("error");
  }
}

try {
  const cultivos = await (await fetch("/api/cultivos")).json();
  const chips = $("chips");
  for (const c of cultivos) {
    const boton = crear("button", "chip", c.nombre);
    boton.type = "button";
    boton.dataset.id = c.id;
    boton.setAttribute("role", "tab");
    boton.addEventListener("click", () => mostrar(c.id));
    chips.append(boton);
  }
  const pedido = new URLSearchParams(location.search).get("cultivo");
  mostrar(cultivos.some((c) => c.id === pedido) ? pedido : cultivos[0].id);
} catch {
  estado.textContent = "No se pudo cargar la lista de cultivos.";
  estado.classList.add("error");
}
