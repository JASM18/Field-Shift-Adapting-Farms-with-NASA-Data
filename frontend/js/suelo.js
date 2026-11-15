// Pantalla "Así es tu suelo": una tarjeta por cada pregunta.
import { pedirApi, conservarUbicacionEnEnlaces } from "./comun.js";

conservarUbicacionEnEnlaces();

const estado = document.getElementById("estado");
const contenedor = document.getElementById("tarjetas");

// Crea un elemento con clase y texto (textContent: evita meter HTML por accidente)
function crear(etiqueta, clase, texto) {
  const el = document.createElement(etiqueta);
  if (clase) el.className = clase;
  if (texto) el.textContent = texto;
  return el;
}

// Tarjeta genérica: pregunta, respuesta grande, descripción, "Qué hacer" y detalle técnico
function tarjeta(pregunta, dato, extra) {
  const caja = crear("section", "tarjeta");
  caja.append(crear("p", "tarjeta-pregunta", pregunta));

  if (dato.error) {
    caja.append(crear("p", "tarjeta-sin-dato", dato.error));
    contenedor.append(caja);
    return;
  }

  caja.append(crear("p", `tarjeta-respuesta ${dato.tipo || ""}`, dato.nombre));
  if (extra) caja.append(extra);
  if (dato.descripcion) caja.append(crear("p", "", dato.descripcion));
  if (dato.que_hacer) {
    const p = crear("p", "que-hacer");
    p.append(crear("strong", "", "Qué hacer: "), dato.que_hacer);
    caja.append(p);
  }
  if (dato.detalle) caja.append(crear("p", "tarjeta-detalle", dato.detalle));
  contenedor.append(caja);
}

// Escala de 5 niveles para la humedad
function escalaHumedad(humedad) {
  const escala = crear("div", "escala");
  humedad.escala.forEach((nombre, i) => {
    const paso = crear("div", `escala-paso nivel-${i}${i === humedad.indice ? " actual" : ""}`);
    paso.append(crear("span", "escala-color"), crear("span", "escala-nombre", nombre));
    escala.append(paso);
  });
  return escala;
}

try {
  const suelo = await pedirApi("/api/suelo");
  const humedad = suelo.humedad;
  if (!humedad.error) humedad.tipo = ["alerta", "alerta", "normal", "agua", "agua"][humedad.indice];

  tarjeta("¿Cuánta humedad tiene ahora?", humedad, humedad.error ? null : escalaHumedad(humedad));
  tarjeta("¿Qué tipo de tierra tengo?", suelo.textura);
  tarjeta("¿Tiene materia orgánica?", suelo.materia_organica);
  tarjeta("¿Es ácida o alcalina?", suelo.ph);
  tarjeta("¿Mi terreno es plano o inclinado?", suelo.terreno);
  estado.hidden = true;
} catch (error) {
  estado.textContent = error.message;
  estado.classList.add("error");
}
