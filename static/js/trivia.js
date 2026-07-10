// ================================================================
//  trivia.js — Conecta la Trivia Rápida con la API
// ================================================================

const params = new URLSearchParams(window.location.search);
const modo = params.get("modo") === "diario" ? "diario" : "practica";

const preguntaTexto = document.getElementById("pregunta-texto");
const opcionesDiv = document.getElementById("opciones");
const numPregunta = document.getElementById("num-pregunta");
const totalPreguntas = document.getElementById("total-preguntas");
const aciertosSpan = document.getElementById("aciertos");
const resultMsg = document.getElementById("result-msg");

let respondida = false;
let pistaUsada = false;

function mostrarMensaje(mensaje, clase) {
  resultMsg.textContent = mensaje;
  resultMsg.classList.remove("hidden", "ganaste", "perdiste");
  if (clase) resultMsg.classList.add(clase);
}

function renderOpciones(opciones) {
  opcionesDiv.innerHTML = "";
  opciones.forEach((texto, i) => {
    const btn = document.createElement("button");
    btn.className = "trivia-opcion";
    btn.textContent = texto;
    btn.dataset.indice = i;
    btn.addEventListener("click", () => responder(i));
    opcionesDiv.appendChild(btn);
  });
}

async function cargarTrivia() {
  let response, data;
  try {
    response = await fetch(`/api/trivia?modo=${modo}`);
    data = await response.json();
  } catch (err) {
    mostrarMensaje("No se pudo conectar con el servidor.");
    return;
  }

  if (!response.ok) {
    mostrarMensaje(data.error || "No hay partida activa.");
    return;
  }

  if (data.terminado) {
    preguntaTexto.textContent = "¡Trivia completada!";
    opcionesDiv.innerHTML = "";
    mostrarMensaje(
      `Terminaste con ${data.aciertos} de ${data.total} aciertos.`,
      data.aciertos === data.total ? "ganaste" : "perdiste"
    );
    return;
  }

  respondida = false;
  pistaUsada = false;
  numPregunta.textContent = data.numero_pregunta;
  totalPreguntas.textContent = data.total_preguntas;
  aciertosSpan.textContent = data.aciertos;
  preguntaTexto.textContent = data.pregunta;
  renderOpciones(data.opciones);
  resultMsg.classList.add("hidden");
}

async function responder(indice) {
  if (respondida) return;
  respondida = true;

  const botones = opcionesDiv.querySelectorAll(".trivia-opcion");
  botones.forEach((btn) => (btn.disabled = true));

  let response, data;
  try {
    response = await fetch("/api/trivia/responder", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ modo, opcion: indice }),
    });
    data = await response.json();
  } catch (err) {
    mostrarMensaje("No se pudo conectar con el servidor.");
    return;
  }

  if (!response.ok) {
    mostrarMensaje(data.error || "Ocurrió un error inesperado.");
    return;
  }

  aciertosSpan.textContent = data.aciertos;

  botones[indice].classList.add(data.correcto ? "correcta" : "incorrecta");
  if (!data.correcto) {
    botones[data.respuesta_correcta].classList.add("correcta");
  }

  mostrarMensaje(
    data.correcto ? "¡Correcto!" : `Incorrecto. La respuesta era la opción ${data.respuesta_correcta + 1}.`,
    data.correcto ? "ganaste" : "perdiste"
  );

  if (data.terminado) {
    setTimeout(() => cargarTrivia(), 1500);
  } else {
    setTimeout(() => cargarTrivia(), 1500);
  }
}

async function pedirPista() {
  if (respondida || pistaUsada) return;
  pistaUsada = true;

  let response, data;
  try {
    response = await fetch("/api/trivia/pista", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ modo }),
    });
    data = await response.json();
  } catch (err) {
    mostrarMensaje("No se pudo conectar con el servidor.");
    return;
  }

  if (!response.ok) {
    mostrarMensaje(data.error || "Ocurrió un error inesperado.");
    return;
  }

  const botones = opcionesDiv.querySelectorAll(".trivia-opcion");
  data.opciones_eliminadas.forEach((i) => {
    botones[i].classList.add("eliminada");
    botones[i].disabled = true;
  });
}

async function reiniciarPartida() {
  let response, data;
  try {
    response = await fetch("/api/trivia/reiniciar", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ modo }),
    });
    data = await response.json();
  } catch (err) {
    mostrarMensaje("No se pudo conectar con el servidor.");
    return;
  }

  if (!response.ok) {
    mostrarMensaje(data.error || "Ocurrió un error inesperado.");
    return;
  }

  cargarTrivia();
}

cargarTrivia();