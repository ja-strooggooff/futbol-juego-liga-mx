// ================================================================
//  wordle.js — Conecta el HTML de Adivina el Jugador con la API
// ================================================================

const params = new URLSearchParams(window.location.search);
const modo = params.get("modo") === "diario" ? "diario" : "practica";

const board = document.getElementById("board");
const input = document.getElementById("player-input");
const resultMsg = document.getElementById("result-msg");

let juegoTerminado = false;

const NOMBRES_COLUMNAS = ["posicion", "liga", "equipo", "pais", "edad", "dorsal"];

function crearFila(data) {
  const fila = document.createElement("div");
  fila.className = "wordle-row";

  const celdaNombre = document.createElement("span");
  celdaNombre.className = "wordle-cell";
  celdaNombre.textContent = data.nombre;
  fila.appendChild(celdaNombre);

  NOMBRES_COLUMNAS.forEach((attr) => {
    const info = data.atributos[attr];
    const celda = document.createElement("span");
    celda.className = `wordle-cell ${info.estado}`;

    let texto = String(info.valor);
    if (info.pista === "subir") texto += " ↑";
    if (info.pista === "bajar") texto += " ↓";

    celda.textContent = texto;
    fila.appendChild(celda);
  });

  return fila;
}

function mostrarError(mensaje) {
  resultMsg.textContent = mensaje;
  resultMsg.classList.remove("hidden");
  resultMsg.classList.remove("ganaste", "perdiste");
}

function mostrarFinDeJuego(data) {
  juegoTerminado = true;
  input.disabled = true;

  if (data.gano) {
    resultMsg.textContent = `¡Correcto! Era ${data.secreto}. Lo lograste en ${data.intentos} intentos.`;
    resultMsg.classList.add("ganaste");
  } else {
    resultMsg.textContent = `Se acabaron los intentos. Era ${data.secreto}.`;
    resultMsg.classList.add("perdiste");
  }
  resultMsg.classList.remove("hidden");
}

async function submitGuess() {
  if (juegoTerminado) return;

  const nombre = input.value.trim();
  if (!nombre) return;

  let response, data;
  try {
    response = await fetch("/api/intentar", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ nombre, modo }),
    });
    data = await response.json();
  } catch (err) {
    mostrarError("No se pudo conectar con el servidor. Intenta de nuevo.");
    return;
  }

  if (!response.ok) {
    mostrarError(data.error || "Ocurrió un error inesperado.");
    return;
  }

  const placeholder = board.querySelector(".wordle-placeholder");
  if (placeholder) placeholder.remove();

  board.appendChild(crearFila(data));
  input.value = "";

  if (data.terminado) {
    mostrarFinDeJuego(data);
  }
}

input.addEventListener("keydown", (e) => {
  if (e.key === "Enter") submitGuess();
});