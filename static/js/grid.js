// ================================================================
//  grid.js — Grid de Equipos (3x3) · FutTrivia
//
//  Conecta el HTML con las APIs de app.py:
//    GET  /api/jugadores      → nombres para el autocompletado
//    GET  /api/grid           → categorías de filas/columnas y celdas resueltas
//    POST /api/grid/intentar  → valida un jugador en una celda
//    POST /api/grid/pista     → sugiere un jugador para la celda elegida
//    POST /api/grid/reiniciar → tablero nuevo (solo práctica)
//
//  Identidad visual según docs/referencia-diseno/ANIMACIONES.md:
//  fondo casi negro con tinte verde, elementos crema/salvia en
//  outline, logo de portería, y la pelota entrando al arco como
//  transición entre pantallas. El tema se inyecta desde aquí para
//  no tocar style.css (que todavía usa la paleta vieja).
// ================================================================

/* ================================================================
   1. IDENTIDAD VISUAL FUTTRIVIA (compartida con wordle.js)
   ================================================================ */

const FT_TEMA_BASE = `
  :root {
    --verde: #a9b56e;
    --verde-dark: #97a45d;
    --fondo: #212620;
    --fondo-card: #272c25;
    --fondo-card2: #2d332b;
    --borde: #3a4136;
    --texto: #f1eee3;
    --texto-sub: #b3b6a5;
    --texto-muted: #767b6a;
    --ft-tinta: #1c211b;
    --ft-error: #c9705f;
  }
  body { background: var(--fondo); color: var(--texto); }

  .navbar { background: rgba(33, 38, 32, 0.9); border-bottom: 1px solid var(--borde); }
  .nav-logo { display: flex; align-items: center; gap: 10px; }
  .nav-logo svg { width: 34px; height: 26px; display: block; }
  .nav-link { color: var(--texto-muted); font-size: 12px; letter-spacing: 0.14em; text-transform: uppercase; }
  .nav-link:hover { color: var(--texto); background: transparent; }
  .nav-cta {
    background: transparent !important; color: var(--texto-sub) !important;
    border: 1px solid var(--borde); font-weight: 500;
  }
  .nav-cta:hover { border-color: var(--texto-sub); color: var(--texto) !important; }

  .back-link { font-size: 12px; letter-spacing: 0.18em; text-transform: uppercase; color: var(--texto-muted); }
  .back-link:hover { color: var(--texto); }
  .wordle-title { color: var(--texto); }
  .wordle-sub { color: var(--texto-sub); }
  .wordle-sub strong { color: var(--verde); font-weight: 600; }

  .btn-primary, .btn-secondary {
    padding: 11px 22px; background: transparent; color: var(--texto);
    border: 1px solid var(--texto-sub); border-radius: 4px;
    font-size: 12px; font-weight: 600; letter-spacing: 0.14em; text-transform: uppercase;
    cursor: pointer; transition: background 0.15s, color 0.15s, border-color 0.15s, opacity 0.15s;
  }
  .btn-primary:hover { background: var(--verde); border-color: var(--verde); color: var(--ft-tinta); }
  .btn-secondary { border-color: var(--borde); color: var(--texto-sub); }
  .btn-secondary:hover { border-color: var(--texto-sub); color: var(--texto); background: transparent; }
  .btn-primary:disabled, .btn-secondary:disabled { opacity: 0.35; cursor: default; }
  .btn-primary:disabled:hover { background: transparent; color: var(--texto); border-color: var(--texto-sub); }

  .wordle-input {
    background: var(--fondo-card); border: 1px solid var(--borde); color: var(--texto);
    border-radius: 4px; padding: 12px 14px; min-width: 260px;
  }
  .wordle-input:focus { outline: none; border-color: var(--verde); }
  .wordle-input::placeholder { color: var(--texto-muted); }
  .wordle-input:disabled { opacity: 0.4; }

  .wordle-result {
    max-width: 940px; margin: 18px auto 0; padding: 14px 18px;
    border: 1px solid var(--borde); border-radius: 4px;
    background: var(--fondo-card); color: var(--texto-sub); text-align: center;
    animation: ft-aparece 0.25s ease;
  }
  .wordle-result.ganaste { border-color: var(--verde); color: var(--verde); }
  .wordle-result.perdiste { border-color: var(--ft-error); color: var(--ft-error); }
  .hidden { display: none; }

  .footer { background: transparent; border-top: 1px solid var(--borde); }
  .footer-inner span { color: var(--texto-muted); }

  @keyframes ft-aparece { from { opacity: 0; transform: translateY(4px); } }

  /* --- Transición: la pelota entra al arco (pieza central) --- */
  .ft-overlay {
    position: fixed; inset: 0; z-index: 9999; background: var(--fondo);
    display: flex; align-items: center; justify-content: center;
  }
  .ft-escena { position: relative; width: 280px; height: 210px; display: flex; align-items: center; justify-content: center; }
  .ft-escena-porteria { width: 210px; color: var(--texto); }
  .ft-escena-pelota {
    position: absolute; left: 50%; top: 55%; width: 42px; height: 42px;
    margin: -21px 0 0 -21px; color: var(--texto);
  }
  .ft-overlay.entrada .ft-escena-pelota { animation: ft-pelota-al-arco 0.95s cubic-bezier(0.3, 0.7, 0.4, 1) forwards; }
  .ft-overlay.entrada .ft-escena-porteria { animation: ft-red-pop 0.3s ease 0.9s; }
  .ft-overlay.entrada { animation: ft-overlay-fade 0.4s ease 1.15s forwards; }
  .ft-overlay.salida { animation: ft-overlay-aparece 0.15s ease; }
  .ft-overlay.salida .ft-escena-pelota { animation: ft-pelota-al-arco 0.55s ease-in forwards; }
  .ft-overlay.salida .ft-escena-porteria { animation: ft-red-pop 0.25s ease 0.5s; }

  @keyframes ft-pelota-al-arco {
    0%   { transform: translateX(-46vw) rotate(0turn); }
    80%  { transform: translateX(0) rotate(2.5turn) scale(1); opacity: 1; }
    100% { transform: translateX(12px) translateY(-8px) rotate(2.8turn) scale(0.55); opacity: 0.8; }
  }
  @keyframes ft-red-pop { 40% { transform: scale(1.05); } }
  @keyframes ft-overlay-fade { to { opacity: 0; visibility: hidden; } }
  @keyframes ft-overlay-aparece { from { opacity: 0; } }

  @media (prefers-reduced-motion: reduce) {
    .ft-overlay { display: none !important; }
    * { animation-duration: 0.01ms !important; transition-duration: 0.01ms !important; }
  }
`;

// Estilos solo de esta pantalla (tablero 3x3)
const FT_TEMA_PAGINA = `
  .wordle-page { text-align: center; padding-bottom: 60px; }
  .grid-table { border-collapse: separate; border-spacing: 6px; margin: 26px auto; }
  .grid-table th, .grid-table td { border: none; }
  .grid-table thead th, .grid-table tbody th {
    background: transparent; color: var(--texto-muted);
    font-size: 11px; font-weight: 500; letter-spacing: 0.1em; text-transform: uppercase;
    padding: 10px 8px;
  }
  .ft-cat-tipo { display: block; font-size: 10px; color: var(--texto-muted); margin-bottom: 3px; }
  .ft-cat-valor { display: block; font-size: 13px; letter-spacing: 0.04em; color: var(--texto-sub); text-transform: none; }
  .grid-cell {
    background: var(--fondo-card); border: 1px solid var(--borde); border-radius: 4px;
    color: var(--texto); height: 90px; cursor: pointer;
    transition: background 0.15s, border-color 0.15s;
  }
  .grid-cell:hover { background: var(--fondo-card2); border-color: var(--texto-muted); }
  .grid-cell.seleccionada { border-color: var(--verde); box-shadow: inset 0 0 0 1px var(--verde); }
  .grid-cell.resuelta {
    background: var(--verde); border-color: var(--verde); color: var(--ft-tinta);
    font-weight: 600; cursor: default; animation: ft-celda-pop 0.3s ease;
  }
  .grid-cell.resuelta:hover { background: var(--verde); }
  .grid-cell.fallo { animation: ft-sacudida 0.35s ease; }
  @keyframes ft-celda-pop { 40% { transform: scale(1.06); } }
  @keyframes ft-sacudida {
    20%, 60% { transform: translateX(-5px); }
    40%, 80% { transform: translateX(5px); }
  }
  .wordle-input-area { display: flex; gap: 10px; justify-content: center; flex-wrap: wrap; align-items: center; margin-top: 8px; }
  #celda-seleccionada-label {
    width: 100%; color: var(--texto-muted) !important;
    font-size: 12px !important; letter-spacing: 0.12em; text-transform: uppercase;
  }
`;

// Portería en outline sobre una mancha salvia (el logo aprobado)
const FT_SVG_PORTERIA = `
<svg viewBox="0 0 140 100" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
  <ellipse cx="72" cy="56" rx="60" ry="40" fill="#a9b475"/>
  <g stroke="#f1eee3" stroke-width="1.2" opacity="0.85">
    <path d="M46 38 V72 M59 38 V74 M72 38 V74 M85 38 V74 M98 38 V72"/>
    <path d="M46 47 H98 M46 56 H98 M46 65 H98"/>
    <path d="M28 40 L46 47 M28 56 L46 58 M28 72 L46 70"/>
    <path d="M112 40 L98 47 M112 56 L98 58 M112 72 L98 70"/>
  </g>
  <g stroke="#f1eee3" stroke-width="4" stroke-linecap="round">
    <path d="M28 88 V24 H112 V88"/>
    <path d="M46 38 H98 M46 38 V74 M98 38 V74"/>
    <path d="M28 24 L46 38 M112 24 L98 38 M28 88 L46 74 M112 88 L98 74"/>
    <path d="M16 88 H124"/>
  </g>
</svg>`;

// Pelota en outline (gira con CSS durante la transición)
const FT_SVG_PELOTA = `
<svg viewBox="0 0 40 40" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
  <circle cx="20" cy="20" r="16" stroke="currentColor" stroke-width="2.5"/>
  <path d="M20 12 L27.6 17.5 L24.7 26.5 L15.3 26.5 L12.4 17.5 Z"
        stroke="currentColor" stroke-width="2" stroke-linejoin="round"/>
  <path d="M20 12 V4.5 M27.6 17.5 L34.8 15 M24.7 26.5 L29.5 32.5 M15.3 26.5 L10.5 32.5 M12.4 17.5 L5.2 15"
        stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
</svg>`;

function ftMovimientoReducido() {
  return window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}

function ftAplicarIdentidad(temaPagina) {
  const estilos = document.createElement("style");
  estilos.id = "futtrivia-tema";
  estilos.textContent = FT_TEMA_BASE + temaPagina;
  document.head.appendChild(estilos);

  // El emoji ⚽ del navbar se reemplaza por el logo de la portería
  const logo = document.querySelector(".nav-logo span:first-child");
  if (logo) logo.innerHTML = FT_SVG_PORTERIA;
}

// Pelota rodando hacia el arco. direccion: "entrada" (al llegar a la
// pantalla) o "salida" (antes de navegar a otra). Regresa una promesa
// que se resuelve cuando la animación terminó.
function ftTransicionPelota(direccion) {
  return new Promise((resolver) => {
    if (ftMovimientoReducido()) {
      resolver();
      return;
    }
    const overlay = document.createElement("div");
    overlay.className = `ft-overlay ${direccion}`;
    overlay.innerHTML = `
      <div class="ft-escena">
        <div class="ft-escena-porteria">${FT_SVG_PORTERIA}</div>
        <div class="ft-escena-pelota">${FT_SVG_PELOTA}</div>
      </div>`;
    document.body.appendChild(overlay);

    const duracion = direccion === "entrada" ? 1550 : 700;
    const terminar = () => {
      if (direccion === "entrada") overlay.remove();
      resolver();
    };
    setTimeout(terminar, duracion);
    // Un clic salta la animación de entrada (que no estorbe)
    if (direccion === "entrada") {
      overlay.addEventListener("click", () => {
        overlay.remove();
        resolver();
      }, { once: true });
    }
  });
}

// Los enlaces que salen de la pantalla (← Volver, logo, "Juegos")
// disparan la pelota entrando al arco antes de navegar.
function ftConectarSalidas() {
  let saliendo = false;
  document.querySelectorAll("a.back-link, a.nav-logo, a.nav-link").forEach((enlace) => {
    const destino = enlace.getAttribute("href");
    if (!destino || destino === "#") return;
    enlace.addEventListener("click", (e) => {
      e.preventDefault();
      if (saliendo) return;
      saliendo = true;
      ftTransicionPelota("salida").then(() => { window.location.href = destino; });
    });
  });
}

/* ================================================================
   2. ESTADO Y REFERENCIAS DEL JUEGO
   ================================================================ */

const params = new URLSearchParams(window.location.search);
const modo = params.get("modo") === "diario" ? "diario" : "practica";
const ligaActual = ["mx", "argentina"].includes(params.get("liga")) ? params.get("liga") : "todas";
const dificultadActual = ["facil", "media", "dificil", "legendaria"].includes(params.get("dificultad")) ? params.get("dificultad") : "todas";

const input = document.getElementById("player-input");
const resultMsg = document.getElementById("result-msg");
const seleccionLabel = document.getElementById("celda-seleccionada-label");

let filaSeleccionada = null;
let columnaSeleccionada = null;
let nombresJugadores = [];   // para el autocompletado

const NOMBRE_TIPO = { posicion: "Posición", liga: "Liga", equipo: "Equipo", pais: "País" };

/* ================================================================
   3. LÓGICA DEL JUEGO (contra las APIs de app.py)
   ================================================================ */

function mostrarError(mensaje) {
  resultMsg.textContent = mensaje;
  resultMsg.classList.remove("hidden", "ganaste", "perdiste");
}

function mostrarMensaje(mensaje, clase) {
  resultMsg.textContent = mensaje;
  resultMsg.classList.remove("hidden", "ganaste", "perdiste");
  if (clase) resultMsg.classList.add(clase);
}

function pintarCategoria(idCelda, categoria) {
  const celda = document.getElementById(idCelda);
  if (!celda) return;
  const tipo = NOMBRE_TIPO[categoria.tipo] || categoria.tipo;
  celda.innerHTML = `<span class="ft-cat-tipo">${tipo}</span><span class="ft-cat-valor"></span>`;
  celda.querySelector(".ft-cat-valor").textContent = categoria.valor;
}

function limpiarSeleccion() {
  filaSeleccionada = null;
  columnaSeleccionada = null;
  document.querySelectorAll(".grid-cell.seleccionada").forEach((c) => c.classList.remove("seleccionada"));
  document.getElementById("btn-adivinar").disabled = true;
  seleccionLabel.textContent = "Selecciona una celda del tablero";
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

  data.filas.forEach((cat, i) => pintarCategoria(`row-${i}`, cat));
  data.columnas.forEach((cat, i) => pintarCategoria(`col-${i}`, cat));

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

function seleccionarCelda(fila, columna, celda) {
  document.querySelectorAll(".grid-cell.seleccionada").forEach((c) => c.classList.remove("seleccionada"));
  celda.classList.add("seleccionada");
  filaSeleccionada = fila;
  columnaSeleccionada = columna;
  seleccionLabel.textContent = `Celda: fila ${fila + 1} · columna ${columna + 1}`;
  document.getElementById("btn-adivinar").disabled = false;
  input.focus();
}

document.querySelectorAll(".grid-cell").forEach((celda) => {
  celda.addEventListener("click", () => {
    if (celda.classList.contains("resuelta")) return;
    const fila = parseInt(celda.dataset.fila);
    const columna = parseInt(celda.dataset.columna);
    seleccionarCelda(fila, columna, celda);
  });
});

async function intentarCelda() {
  if (filaSeleccionada === null || columnaSeleccionada === null) {
    mostrarError("Primero selecciona una celda del tablero.");
    return;
  }

  const nombre = input.value.trim();
  if (!nombre) return;

  const celdaActual = document.querySelector(
    `.grid-cell[data-fila="${filaSeleccionada}"][data-columna="${columnaSeleccionada}"]`
  );

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
    celdaActual.textContent = data.nombre;
    celdaActual.classList.remove("seleccionada");
    celdaActual.classList.add("resuelta");
    mostrarMensaje(`¡Correcto! ${data.resueltas}/9 resueltas.`);
    limpiarSeleccion();
  } else {
    celdaActual.classList.remove("fallo");
    void celdaActual.offsetWidth; // reinicia la animación de sacudida
    celdaActual.classList.add("fallo");
    mostrarMensaje(`${data.nombre} no cumple con esa fila/columna.`, "perdiste");
  }

  input.value = "";

  if (data.completo) {
    mostrarMensaje("¡GOL! Completaste el grid 9/9.", "ganaste");
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
    celda.classList.remove("resuelta", "fallo", "seleccionada");
  });
  limpiarSeleccion();
  resultMsg.classList.add("hidden");
  input.value = "";

  cargarGrid();
}

/* ================================================================
   4. AUTOCOMPLETADO (usa GET /api/jugadores)
   ================================================================
   Son ~47,000 nombres: meterlos todos a un <datalist> traba el
   navegador, así que se filtran a máximo 10 sugerencias por tecleo.
   La comparación ignora acentos y mayúsculas ('gonzalez' encuentra
   'González'), igual que el backend. */

function ftNormalizar(texto) {
  return texto.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase();
}

async function cargarAutocompletado() {
  try {
    const respuesta = await fetch(`/api/jugadores?liga=${ligaActual}`);
    if (!respuesta.ok) return;
    nombresJugadores = (await respuesta.json()).map((nombre) => ({
      nombre,
      norm: ftNormalizar(nombre),
    }));
  } catch (err) {
    return; // sin autocompletado se puede jugar igual
  }

  const lista = document.createElement("datalist");
  lista.id = "ft-lista-jugadores";
  document.body.appendChild(lista);
  input.setAttribute("list", "ft-lista-jugadores");

  input.addEventListener("input", () => {
    const texto = ftNormalizar(input.value.trim());
    lista.innerHTML = "";
    if (texto.length < 2) return;

    // Primero los que EMPIEZAN con lo tecleado, luego el resto
    const prefijo = [];
    const contiene = [];
    for (const j of nombresJugadores) {
      if (j.norm.startsWith(texto)) {
        if (prefijo.push(j.nombre) >= 10) break;
      } else if (contiene.length < 10 && j.norm.includes(texto)) {
        contiene.push(j.nombre);
      }
    }
    for (const nombre of prefijo.concat(contiene).slice(0, 10)) {
      const opcion = document.createElement("option");
      opcion.value = nombre;
      lista.appendChild(opcion);
    }
  });
}

/* ================================================================
   5. ARRANQUE
   ================================================================ */

ftAplicarIdentidad(FT_TEMA_PAGINA);
ftTransicionPelota("entrada");
ftConectarSalidas();
cargarAutocompletado();

input.addEventListener("keydown", (e) => {
  if (e.key === "Enter") intentarCelda();
});

cargarGrid();

/* Selectores de liga y dificultad: cada uno marca su opción activa y
   arma los enlaces conservando el modo Y el otro filtro (así cualquier
   combinación liga × dificultad es alcanzable). */
(function ftInicializarSelectores() {
  const base = window.location.pathname;
  const ligas = document.getElementById("ft-ligas");
  if (ligas) ligas.querySelectorAll("a").forEach((enlace) => {
    const liga = enlace.dataset.liga;
    enlace.href = `${base}?modo=${modo}&liga=${liga}&dificultad=${dificultadActual}`;
    if (liga === ligaActual) enlace.classList.add("activa");
  });
  const dificultades = document.getElementById("ft-dificultades");
  if (dificultades) dificultades.querySelectorAll("a").forEach((enlace) => {
    const dificultad = enlace.dataset.dificultad;
    enlace.href = `${base}?modo=${modo}&liga=${ligaActual}&dificultad=${dificultad}`;
    if (dificultad === dificultadActual) enlace.classList.add("activa");
  });
})();
