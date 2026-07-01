// ================================================================
//  grid.js — Conecta el tablero 3x3 con la API de Grid de Equipos
// ================================================================

const params = new URLSearchParams(window.location.search);
const modo = params.get("modo") === "diario" ? "diario" : "practica";

const input = document.getElementById("player-input");
const resultMsg = document.getElementById("result-msg");
const seleccionLabel = document.getElementById("celda-seleccionada-label");

let filaSeleccionada = null;
let columnaSeleccionada = null;

function mostrarError(mensaje) {
  resultMsg.textContent = mensaje;
  resultMsg.classList.remove("hidden", "ganaste", "perdiste");
}

function mostrarMensaje(mensaje, clase) {
  resultMsg.textContent = mensaje;
  resultMsg.classList.remove("hidden", "ganaste", "perdiste");
  if (clase) resultMsg.classList.add(clase);
}

async function cargarGrid() {
  let response, data;
  try {
    response = await fetch(`/api/grid?modo=${modo}`);
    data = await response.json();
  } catch (err) {
    mostrarError("No se pudo conectar con el servidor.");
    return;
  }

  if (!response.ok) {
    mostrarError(data.error || "No hay grid activo.");
    return;
  }

  data.filas.forEach((cat, i) => {
    document.getElementById(`row-${i}`).textContent = cat.valor;
  });
  data.columnas.forEach((cat, i) => {
    document.getElementById(`col-${i}`).textContent = cat.valor;
  });

  Object.keys(data.resueltas).forEach((celdaKey) => {
    const [fila, columna] = celdaKey.split("-");
    const celda = document.querySelector(
      `.grid-cell[data-fila="${fila}"][data-columna="${columna}"]`
    );
    if (celda) {
      celda.textContent = data.resueltas[celdaKey];
      celda.classList.add("resuelta");
    }
  });

  if (Object.keys(data.resueltas).length === 9) {
    mostrarMensaje("¡Completaste el grid!", "ganaste");
  }
}

function seleccionarCelda(fila, columna) {
  filaSeleccionada = fila;
  columnaSeleccionada = columna;
  seleccionLabel.textContent = `Celda seleccionada: fila ${fila + 1}, columna ${columna + 1}`;
  document.getElementById("btn-adivinar").disabled = false;
  input.focus();
}

document.querySelectorAll(".grid-cell").forEach((celda) => {
  celda.addEventListener("click", () => {
    if (celda.classList.contains("resuelta")) return;
    const fila = parseInt(celda.dataset.fila);
    const columna = parseInt(celda.dataset.columna);
    seleccionarCelda(fila, columna);
  });
});

async function intentarCelda() {
  if (filaSeleccionada === null || columnaSeleccionada === null) {
    mostrarError("Primero selecciona una celda del tablero.");
    return;
  }

  const nombre = input.value.trim();
  if (!nombre) return;

  let response, data;
  try {
    response = await fetch("/api/grid/intentar", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        modo,
        fila: filaSeleccionada,
        columna: columnaSeleccionada,
        nombre,
      }),
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

  if (data.correcto) {
    const celda = document.querySelector(
      `.grid-cell[data-fila="${filaSeleccionada}"][data-columna="${columnaSeleccionada}"]`
    );
    celda.textContent = data.nombre;
    celda.classList.add("resuelta");
    mostrarMensaje(`¡Correcto! ${data.resueltas}/9 resueltas.`);
    filaSeleccionada = null;
    columnaSeleccionada = null;
    document.getElementById("btn-adivinar").disabled = true;
    seleccionLabel.textContent = "Selecciona una celda del tablero";
  } else {
    mostrarMensaje(`${data.nombre} no cumple con esa fila/columna.`, "perdiste");
  }

  input.value = "";

  if (data.completo) {
    mostrarMensaje("¡Completaste el grid!", "ganaste");
  }
}

async function pedirPista() {
  if (filaSeleccionada === null || columnaSeleccionada === null) {
    mostrarError("Primero selecciona una celda del tablero.");
    return;
  }

  let response, data;
  try {
    response = await fetch("/api/grid/pista", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        modo,
        fila: filaSeleccionada,
        columna: columnaSeleccionada,
      }),
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

  mostrarMensaje(`Pista: probablemente ${data.jugador_sugerido}`);
}

async function reiniciarPartida() {
  let response, data;
  try {
    response = await fetch("/api/grid/reiniciar", {
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

  document.querySelectorAll(".grid-cell").forEach((celda) => {
    celda.textContent = "";
    celda.classList.remove("resuelta");
  });
  filaSeleccionada = null;
  columnaSeleccionada = null;
  document.getElementById("btn-adivinar").disabled = true;
  seleccionLabel.textContent = "Selecciona una celda del tablero";
  resultMsg.classList.add("hidden");
  input.value = "";

  cargarGrid();
}

input.addEventListener("keydown", (e) => {
  if (e.key === "Enter") intentarCelda();
});

cargarGrid();