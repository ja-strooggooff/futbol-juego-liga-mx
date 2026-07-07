// ================================================================
//  wordle.js — Adivina el Jugador · FutTrivia
//
//  Conecta el HTML con las APIs de app.py:
//    GET  /api/jugadores        → nombres para el autocompletado
//    POST /api/intentar         → compara el intento con el secreto
//    POST /api/wordle/pista     → revela un atributo (cuesta 1 intento)
//    POST /api/wordle/reiniciar → partida nueva (solo práctica)
//
//  Identidad visual según docs/referencia-diseno/ANIMACIONES.md:
//  fondo casi negro con tinte verde, elementos crema/salvia en
//  outline, logo de portería, y la pelota entrando al arco como
//  transición entre pantallas. El tema se inyecta desde aquí para
//  no tocar style.css (que todavía usa la paleta vieja).
// ================================================================

/* ================================================================
   1. IDENTIDAD VISUAL FUTTRIVIA (compartida con grid.js)
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

// Estilos solo de esta pantalla (tablero de Adivina el Jugador)
const FT_TEMA_PAGINA = `
  .wordle-page { text-align: center; padding-bottom: 60px; }
  .wordle-columns, .wordle-row {
    display: grid; grid-template-columns: 1.6fr repeat(6, 1fr); gap: 6px;
    max-width: 940px; margin: 0 auto 6px; padding: 0 16px;
  }
  .wordle-columns {
    margin-top: 26px; font-size: 11px; letter-spacing: 0.14em;
    text-transform: uppercase; color: var(--texto-muted);
  }
  .wordle-columns span { padding: 6px 0; }
  .wordle-board { max-width: 940px; margin: 0 auto; }
  .wordle-placeholder {
    color: var(--texto-muted); padding: 30px 12px; margin: 0 16px;
    border: 1px dashed var(--borde); border-radius: 4px;
  }
  .wordle-cell {
    background: var(--fondo-card); border: 1px solid var(--borde); border-radius: 4px;
    padding: 10px 6px; font-size: 13px; min-height: 46px;
    display: flex; align-items: center; justify-content: center;
    animation: ft-celda-aparece 0.3s ease backwards;
  }
  .wordle-row .wordle-cell:nth-child(2) { animation-delay: 0.06s; }
  .wordle-row .wordle-cell:nth-child(3) { animation-delay: 0.12s; }
  .wordle-row .wordle-cell:nth-child(4) { animation-delay: 0.18s; }
  .wordle-row .wordle-cell:nth-child(5) { animation-delay: 0.24s; }
  .wordle-row .wordle-cell:nth-child(6) { animation-delay: 0.30s; }
  .wordle-row .wordle-cell:nth-child(7) { animation-delay: 0.36s; }
  .wordle-cell.correcto { background: var(--verde); border-color: var(--verde); color: var(--ft-tinta); font-weight: 600; }
  .wordle-cell.incorrecto { color: var(--texto-sub); }
  @keyframes ft-celda-aparece { from { opacity: 0; transform: translateY(6px) scale(0.96); } }
  .wordle-input-area { display: flex; gap: 10px; justify-content: center; flex-wrap: wrap; margin-top: 22px; }
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

const board = document.getElementById("board");
const input = document.getElementById("player-input");
const resultMsg = document.getElementById("result-msg");
const subtitulo = document.querySelector(".wordle-sub");

const MAX_INTENTOS = 8;
let juegoTerminado = false;
let nombresJugadores = [];   // para el autocompletado

// Columnas tal como las regresa la API (/api/intentar → atributos)
const NOMBRES_COLUMNAS = ["posicion", "liga", "equipo", "pais", "edad", "valor_mercado"];
const ETIQUETAS = {
  posicion: "Posición", liga: "Liga", equipo: "Equipo",
  pais: "País", edad: "Edad", valor_mercado: "Valor",
};

/* ================================================================
   3. LÓGICA DEL JUEGO (contra las APIs de app.py)
   ================================================================ */

function formatearValor(valor) {
  if (typeof valor !== "number") return String(valor);
  if (valor >= 1000000) {
    const millones = valor / 1000000;
    return `€${millones % 1 === 0 ? millones : millones.toFixed(1)}M`;
  }
  if (valor >= 1000) return `€${Math.round(valor / 1000)}K`;
  return String(valor);
}

function actualizarContador(intentos) {
  if (!subtitulo) return;
  const restantes = MAX_INTENTOS - intentos;
  subtitulo.innerHTML = restantes > 0
    ? `Te quedan <strong>${restantes}</strong> de ${MAX_INTENTOS} intentos.`
    : `Se usaron los ${MAX_INTENTOS} intentos.`;
}

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

    if (!info) {
      celda.className = "wordle-cell incorrecto";
      celda.textContent = "—";
      fila.appendChild(celda);
      return;
    }

    celda.className = `wordle-cell ${info.estado}`;
    let texto = attr === "valor_mercado" ? formatearValor(info.valor) : String(info.valor);
    if (info.pista === "subir") texto += " ↑";
    if (info.pista === "bajar") texto += " ↓";
    celda.textContent = texto;
    fila.appendChild(celda);
  });

  return fila;
}

function mostrarError(mensaje) {
  resultMsg.textContent = mensaje;
  resultMsg.classList.remove("hidden", "ganaste", "perdiste");
}

function mostrarFinDeJuego(data) {
  juegoTerminado = true;
  input.disabled = true;

  if (data.gano) {
    resultMsg.textContent = `¡GOL! Era ${data.secreto}. Lo lograste en ${data.intentos} intentos.`;
    resultMsg.classList.add("ganaste");
  } else {
    resultMsg.textContent = `Se acabaron los intentos. Era ${data.secreto}.`;
    resultMsg.classList.add("perdiste");
  }
  resultMsg.classList.remove("hidden");

  const reiniciar = document.getElementById("reiniciar-btn");
  if (reiniciar) reiniciar.disabled = false;
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
  actualizarContador(data.intentos);

  if (data.terminado) {
    mostrarFinDeJuego(data);
  } else {
    resultMsg.classList.add("hidden");
  }
}

async function pedirPista() {
  if (juegoTerminado) return;

  let response, data;
  try {
    response = await fetch("/api/wordle/pista", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ modo }),
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

  const etiqueta = ETIQUETAS[data.atributo] || data.atributo;
  const valor = data.atributo === "valor_mercado" ? formatearValor(data.valor) : data.valor;
  resultMsg.textContent = `Pista (costó 1 intento): ${etiqueta} → ${valor}`;
  resultMsg.classList.remove("hidden", "ganaste", "perdiste");
  actualizarContador(data.intentos_usados);
}

async function reiniciarPartida() {
  let response, data;
  try {
    response = await fetch("/api/wordle/reiniciar", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ modo }),
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

  board.innerHTML = '<p class="wordle-placeholder">Escribe un jugador abajo para empezar 👇</p>';
  resultMsg.classList.add("hidden");
  input.disabled = false;
  input.value = "";
  juegoTerminado = false;
  actualizarContador(0);
  document.getElementById("reiniciar-btn").disabled = true;
  input.focus();
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
    const respuesta = await fetch("/api/jugadores");
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
actualizarContador(0);

// La API compara por valor de mercado, no por dorsal: se corrige el
// encabezado de la última columna sin tocar el template.
const encabezados = document.querySelectorAll(".wordle-columns span");
if (encabezados.length === 7) encabezados[6].textContent = "Valor";

input.addEventListener("keydown", (e) => {
  if (e.key === "Enter") submitGuess();
});
input.focus();
