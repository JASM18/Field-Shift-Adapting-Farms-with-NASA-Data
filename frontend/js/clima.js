// Pantalla "El clima de tu zona": pide el resumen al servidor y lo dibuja.
import { pedirApi, conservarUbicacionEnEnlaces } from "./comun.js";

conservarUbicacionEnEnlaces();

// La barra va de 15 °C (vacía) a 45 °C (llena)
const BARRA_MIN = 15;
const BARRA_MAX = 45;

const estado = document.getElementById("estado");

try {
  const clima = await pedirApi("/api/clima");

  document.getElementById("subtitulo").textContent =
    `What usually happens each month (${clima.total_años}-year average, ${clima.periodo})`;

  dibujarAvisos(clima.avisos);
  dibujarMeses(clima.meses);

  estado.hidden = true;
  document.getElementById("seccion-meses").hidden = false;
} catch (error) {
  estado.textContent = error.message;
  estado.classList.add("error");
}

function dibujarAvisos(avisos) {
  const contenedor = document.getElementById("avisos");
  for (const aviso of avisos) {
    const caja = document.createElement("div");
    caja.className = `aviso ${aviso.tipo}`;
    const titulo = document.createElement("strong");
    titulo.textContent = aviso.titulo;
    const texto = document.createElement("p");
    texto.textContent = aviso.texto;
    caja.append(titulo, texto);
    contenedor.append(caja);
  }
}

function dibujarMeses(meses) {
  const lista = document.getElementById("meses");
  for (const mes of meses) {
    const ancho = Math.min(100, Math.max(0,
      (100 * (mes.maxima_promedio - BARRA_MIN)) / (BARRA_MAX - BARRA_MIN)));

    const fila = document.createElement("li");
    fila.className = "mes";
    fila.innerHTML = `
      <div class="mes-fila">
        <span class="mes-nombre"></span>
        <div class="barra"><span class="${mes.nivel}" style="width:${ancho}%"></span></div>
        <span class="mes-temp">${Math.round(mes.maxima_promedio)}°</span>
      </div>
      <div class="mes-detalle"></div>`;
    fila.querySelector(".mes-nombre").textContent = mes.mes;

    const detalle = fila.querySelector(".mes-detalle");
    const lluvia = document.createElement("span");
    lluvia.textContent = mes.texto_lluvia;
    lluvia.title = `${mes.lluvia_mm} mm on average`;
    detalle.append(lluvia);
    for (const etiqueta of mes.etiquetas) {
      const chip = document.createElement("span");
      chip.className = `etiqueta ${etiqueta.tipo}`;
      chip.textContent = etiqueta.texto;
      detalle.append(chip);
    }
    lista.append(fila);
  }
}
