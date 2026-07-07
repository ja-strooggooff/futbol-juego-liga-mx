// ================================================================
//  conexiones.js — Conecta el juego de Conexiones con la API
// ================================================================

const params = new URLSearchParams(window.location.search);
const modo = params.get("modo") === "diario" ? "diario" : "practica";

const tablero = document.getElementById("tablero");
const resultMsg = document.getElementById("result-msg");
const erroresCount = document.getElementById("errores-count");
const erroresMax = document.getElementById("errores-max");
const btnEnviar = document.getElementById("btn-enviar");
const gruposResueltos = document.getElementById("grupos-resueltos");

let seleccionados = new Set();
let juegoTerminado = false;

function mostrarError(mensaje) {
  resultMsg.textContent = mensaje;
  resultMsg.classList.remove("hidden", "ganaste", "perdiste");
}

function mostrarMensaje(mensaje, clase) {
  resultMsg.textContent = mensaje;
  resultMsg.classList.remove("hidden", "ganaste", "perdiste");
  if (clase) resultMsg.classList.add(clase);
}

function toggleSeleccion(nombre, tarjeta) {
  if (juegoTerminado) return;

  if (seleccionados.has(nombre)) {
    seleccionados.delete(nombre);
    tarjeta.classList.remove("seleccionada");
  } else {
    seleccionados.add(nombre);
    tarjeta.classList.add("seleccionada");
  }

  btnEnviar.disabled = seleccionados.size === 0;
}

function renderTarjeta(nombre) {
  const tarjeta = document.createElement("div");
  tarjeta.className = "conexion-tarjeta";
  tarjeta.textContent = nombre;
  tarjeta.addEventListener("click", () => toggleSeleccion(nombre, tarjeta));
  return tarjeta;
}

function renderGrupoResuelto(valor, jugadores) {
  const grupo = document.createElement("div");
  grupo.className = "conexion-grupo-resuelto";
  grupo.innerHTML = `
    <strong>${valor}</strong>
    <span>${jugadores.join(", ")}</span>
  `;
  gruposResueltos.appendChild(grupo);
}

async function cargarConexiones() {
  let response, data;
  try {
    response = await fetch(`/api/conexiones?modo=${modo}`);
    data = await response.json();
  } catch (err) {
    mostrarError("No se pudo conectar con el servidor.");
    return;
  }

  if (!response.ok) {
    mostrarError(data.error || "No hay partida activa.");
    return;
  }

  erroresCount.textContent = data.errores;
  erroresMax.textContent = data.errores_max;

  tablero.innerHTML = "";
  data.tablero.forEach((nombre) => {
    tablero.appendChild(renderTarjeta(nombre));
  });

  data.grupos_resueltos.forEach(({ valor, jugadores }) => {
    renderGrupoResuelto(valor, jugadores);
  });

  if (data.terminado) {
    juegoTerminado = true;
    btnEnviar.disabled = true;
  }
}

async function enviarSeleccion() {
  if (juegoTerminado || seleccionados.size === 0) return;

  let response, data;
  try {
    response = await fetch("/api/conexiones/intentar", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ modo, jugadores: Array.from(seleccionados) }),
    });
    data = await response.json();
  } catch (err) {
    mostrarError("No se pudo conectar con el servidor.");
    return;
  }

  if (!response.ok) {
    mostrarError(data.error || "Ocurrió un error inesperado.");
    return;
  }

  erroresCount.textContent = data.errores;

  if (data.correcto) {
    renderGrupoResuelto(data.categoria_encontrada, Array.from(seleccionados));
    document.querySelectorAll(".conexion-tarjeta").forEach((t) => {
      if (seleccionados.has(t.textContent)) t.remove();
    });
    mostrarMensaje(`¡Correcto! Categoría: ${data.categoria_encontrada}`);
  } else {
    mostrarMensaje("Incorrecto, intenta otra combinación.", "perdiste");
    document.querySelectorAll(".conexion-tarjeta.seleccionada").forEach((t) => {
      t.classList.remove("seleccionada");
    });
  }

  seleccionados.clear();
  btnEnviar.disabled = true;

  if (data.terminado) {
    juegoTerminado = true;
    if (data.errores >= parseInt(erroresMax.textContent)) {
      mostrarMensaje("Se acabaron los intentos. ¡Mejor suerte mañana!", "perdiste");
    } else {
      mostrarMensaje("¡Completaste todas las conexiones!", "ganaste");
    }
  }
}

async function pedirPista() {
  if (juegoTerminado) return;

  let response, data;
  try {
    response = await fetch("/api/conexiones/pista", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ modo }),
    });
    data = await response.json();
  } catch (err) {
    mostrarError("No se pudo conectar con el servidor.");
    return;
  }

  if (!response.ok) {
    mostrarError(data.error || "Ocurrió un error inesperado.");
    return;
  }

  erroresCount.textContent = data.errores;
  mostrarMensaje(`Pista: ${data.jugador_pista} pertenece a un grupo pendiente.`);
}

async function reiniciarPartida() {
  let response, data;
  try {
    response = await fetch("/api/conexiones/reiniciar", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ modo }),
    });
    data = await response.json();
  } catch (err) {
    mostrarError("No se pudo conectar con el servidor.");
    return;
  }

  if (!response.ok) {
    mostrarError(data.error || "Ocurrió un error inesperado.");
    return;
  }

  seleccionados.clear();
  juegoTerminado = false;
  gruposResueltos.innerHTML = "";
  tablero.innerHTML = "";
  resultMsg.classList.add("hidden");
  btnEnviar.disabled = true;

  cargarConexiones();
}

cargarConexiones();