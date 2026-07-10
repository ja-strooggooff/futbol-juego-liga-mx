// ================================================================
//  conexiones.js — Conexiones · FutTrivia
//
//  Conecta el HTML con las APIs de app.py:
//    GET  /api/conexiones            → tablero pendiente, grupos resueltos, errores
//    POST /api/conexiones/intentar   → valida el grupo seleccionado (completo)
//    POST /api/conexiones/pista      → revela un jugador de un grupo pendiente (cuesta 1 error)
//    POST /api/conexiones/reiniciar  → partida nueva (solo práctica)
//
//  OJO (backend): con el pool actual de 47,667 jugadores el tablero
//  que manda /api/conexiones trae TODOS los jugadores agrupables y los
//  grupos son de tamaño variable — injugable tal cual. Este JS está
//  completo contra el contrato de la API, pero limita las fichas
//  visibles y avisa cuando el tablero viene desbordado, igual que se
//  hizo con el Grid antes de arreglar generar_grid().
//
//  Identidad visual según docs/referencia-diseno/ANIMACIONES.md:
//  fondo casi negro con tinte verde, elementos crema/salvia en
//  outline, logo de portería, y la pelota entrando al arco como
//  transición entre pantallas. El tema se inyecta desde aquí para
//  no tocar style.css (que todavía usa la paleta vieja).
// ================================================================

/* ================================================================
   1. IDENTIDAD VISUAL FUTTRIVIA (compartida con wordle.js y grid.js)
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

// Estilos solo de esta pantalla (fichas y grupos resueltos)
const FT_TEMA_PAGINA = `
  .wordle-page { text-align: center; padding-bottom: 60px; }
  .cx-tablero {
    display: grid; grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
    gap: 8px; max-width: 760px; margin: 22px auto; padding: 0 16px;
  }
  .cx-ficha {
    padding: 13px 8px; font-size: 13px;
    background: var(--fondo-card); color: var(--texto);
    border: 1px solid var(--borde); border-radius: 4px; cursor: pointer;
    transition: border-color 0.15s, background 0.15s;
    animation: ft-aparece 0.25s ease backwards;
    overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
  }
  .cx-ficha:hover { background: var(--fondo-card2); border-color: var(--texto-muted); }
  .cx-ficha.seleccionada {
    border-color: var(--verde); box-shadow: inset 0 0 0 1px var(--verde);
    color: var(--verde);
  }
  .cx-ficha.pista { border-color: #d9a05b; color: #d9a05b; }
  .cx-ficha.fallo { animation: ft-sacudida 0.35s ease; }
  .cx-grupo {
    max-width: 728px; margin: 8px auto 0; padding: 12px 16px;
    background: var(--verde); border-radius: 4px; color: var(--ft-tinta);
    text-align: left; animation: ft-pop 0.3s ease;
  }
  .cx-grupo strong { display: block; font-size: 13px; letter-spacing: 0.08em; text-transform: uppercase; margin-bottom: 3px; }
  .cx-grupo span { font-size: 13px; }
  .cx-aviso {
    max-width: 728px; margin: 18px auto 0; padding: 12px 16px;
    border: 1px dashed var(--borde); border-radius: 4px;
    color: var(--texto-muted); font-size: 13px; text-align: left;
  }
  @keyframes ft-pop { 40% { transform: scale(1.02); } }
  @keyframes ft-sacudida {
    20%, 60% { transform: translateX(-5px); }
    40%, 80% { transform: translateX(5px); }
  }
  .wordle-input-area { display: flex; gap: 10px; justify-content: center; flex-wrap: wrap; margin-top: 10px; }
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
const tiempoActual = ["30", "60", "90", "120"].includes(params.get("tiempo")) ? params.get("tiempo") : "120";

const tableroDiv = document.getElementById("tablero-conexiones");
const gruposDiv = document.getElementById("grupos-resueltos");
const subtitulo = document.getElementById("conexiones-sub");
const btnProbar = document.getElementById("btn-probar");
const resultMsg = document.getElementById("result-msg");

// Con más fichas que esto el navegador se arrastra y el juego no
// tiene sentido: se recorta y se avisa (el arreglo real es de backend).
const MAX_FICHAS_VISIBLES = 48;

let seleccion = new Set();
let terminado = false;

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

function actualizarSub(errores, erroresMax) {
  subtitulo.innerHTML =
    `Selecciona el grupo COMPLETO de jugadores que comparten algo. Errores: <strong>${errores}</strong> de ${erroresMax}.`;
}

function pintarGruposResueltos(grupos) {
  gruposDiv.innerHTML = "";
  grupos.forEach((grupo) => {
    const caja = document.createElement("div");
    caja.className = "cx-grupo";
    caja.innerHTML = "<strong></strong><span></span>";
    caja.querySelector("strong").textContent = grupo.valor;
    caja.querySelector("span").textContent = grupo.jugadores.join(" · ");
    gruposDiv.appendChild(caja);
  });
}

function pintarTablero(nombres) {
  tableroDiv.innerHTML = "";
  seleccion = new Set();
  btnProbar.disabled = true;

  const visibles = nombres.slice(0, MAX_FICHAS_VISIBLES);
  visibles.forEach((nombre, i) => {
    const ficha = document.createElement("button");
    ficha.className = "cx-ficha";
    ficha.textContent = nombre;
    ficha.title = nombre;
    ficha.style.animationDelay = `${Math.min(i * 15, 400)}ms`;
    ficha.addEventListener("click", () => alternarFicha(nombre, ficha));
    tableroDiv.appendChild(ficha);
  });

  if (nombres.length > MAX_FICHAS_VISIBLES) {
    const aviso = document.createElement("div");
    aviso.className = "cx-aviso";
    aviso.textContent =
      `⚠ El backend mandó ${nombres.length.toLocaleString()} jugadores; se muestran solo ` +
      `${MAX_FICHAS_VISIBLES}. Con el pool actual el tablero necesita un arreglo en app.py ` +
      `(grupos chicos y acotados, como se hizo con el Grid) para ser jugable.`;
    tableroDiv.insertAdjacentElement("afterend", aviso);
  }
}

function alternarFicha(nombre, ficha) {
  if (terminado) return;
  if (seleccion.has(nombre)) {
    seleccion.delete(nombre);
    ficha.classList.remove("seleccionada");
  } else {
    seleccion.add(nombre);
    ficha.classList.add("seleccionada");
  }
  btnProbar.disabled = seleccion.size < 2;
}

function deseleccionarTodo() {
  seleccion = new Set();
  document.querySelectorAll(".cx-ficha.seleccionada").forEach((f) => f.classList.remove("seleccionada"));
  btnProbar.disabled = true;
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
    mostrarError(data.error || "No hay partida activa. Recarga la página.");
    return;
  }

  document.querySelectorAll(".cx-aviso").forEach((a) => a.remove());
  actualizarSub(data.errores, data.errores_max);
  pintarGruposResueltos(data.grupos_resueltos);
  pintarTablero(data.tablero);

  terminado = data.terminado;
  if (terminado) {
    ftDetenerCronometro();
    if (data.por_tiempo) ftPintarTiempo(0);
    const gano = data.tablero.length === 0;
    mostrarMensaje(
      data.por_tiempo
        ? "⏱ Se acabó el tiempo. Reinicia para jugar otro tablero."
        : gano ? "¡GOL! Encontraste todos los grupos." : "Se acabaron los errores permitidos.",
      gano ? "ganaste" : "perdiste"
    );
  } else {
    ftIniciarCronometro(data.tiempo_restante, cargarConexiones);
  }
}

async function probarGrupo() {
  if (terminado || seleccion.size < 2) return;

  let response, data;
  try {
    response = await fetch("/api/conexiones/intentar", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ modo, jugadores: [...seleccion] }),
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
    mostrarMensaje(`¡Correcto! Grupo encontrado: ${data.categoria_encontrada}.`, "ganaste");
    cargarConexiones(); // refresca tablero y grupos resueltos
  } else {
    document.querySelectorAll(".cx-ficha.seleccionada").forEach((f) => {
      f.classList.remove("fallo");
      void f.offsetWidth; // reinicia la animación
      f.classList.add("fallo");
    });
    mostrarMensaje("Ese grupo no es. Recuerda: debe estar COMPLETO.", "perdiste");
    actualizarSub(data.errores, 4);
  }

  if (data.terminado && !data.correcto) {
    terminado = true;
    ftDetenerCronometro();
    mostrarMensaje("Se acabaron los errores permitidos.", "perdiste");
  }
}

async function pedirPista() {
  if (terminado) return;

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

  let visible = false;
  document.querySelectorAll(".cx-ficha").forEach((f) => {
    if (f.textContent === data.jugador_pista) {
      f.classList.add("pista");
      visible = true;
    }
  });
  mostrarMensaje(
    `Pista (costó 1 error): ${data.jugador_pista} pertenece a un grupo pendiente` +
    (visible ? "." : " (no está entre las fichas visibles)."),
  );
  actualizarSub(data.errores, 4);
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

  terminado = false;
  resultMsg.classList.add("hidden");
  cargarConexiones();
}

/* ================================================================
   4. ARRANQUE
   ================================================================ */

ftAplicarIdentidad(FT_TEMA_PAGINA);
ftTransicionPelota("entrada");
ftConectarSalidas();
cargarConexiones();

/* Selectores de liga, dificultad y tiempo: cada uno marca su opción
   activa y arma los enlaces conservando el modo Y los otros dos
   filtros (así cualquier combinación es alcanzable). */
(function ftInicializarSelectores() {
  const base = window.location.pathname;
  const enlaceCombo = (liga, dificultad, tiempo) =>
    `${base}?modo=${modo}&liga=${liga}&dificultad=${dificultad}&tiempo=${tiempo}`;

  const ligas = document.getElementById("ft-ligas");
  if (ligas) ligas.querySelectorAll("a").forEach((enlace) => {
    const liga = enlace.dataset.liga;
    enlace.href = enlaceCombo(liga, dificultadActual, tiempoActual);
    if (liga === ligaActual) enlace.classList.add("activa");
  });
  const dificultades = document.getElementById("ft-dificultades");
  if (dificultades) dificultades.querySelectorAll("a").forEach((enlace) => {
    const dificultad = enlace.dataset.dificultad;
    enlace.href = enlaceCombo(ligaActual, dificultad, tiempoActual);
    if (dificultad === dificultadActual) enlace.classList.add("activa");
  });
  const tiempos = document.getElementById("ft-tiempos");
  if (tiempos) tiempos.querySelectorAll("a").forEach((enlace) => {
    const tiempo = enlace.dataset.tiempo;
    enlace.href = enlaceCombo(ligaActual, dificultadActual, tiempo);
    if (tiempo === tiempoActual) enlace.classList.add("activa");
  });
})();


/* ================================================================
   CRONÓMETRO DEL LÍMITE DE TIEMPO
   ================================================================
   El SERVIDOR manda tiempo_restante y valida la expiración (un
   cronómetro solo del navegador se burla recargando); aquí se pinta
   la cuenta regresiva — chip outline que se pone rojo en los últimos
   10 segundos — y al llegar a cero se consulta el estado real. */

let ftTiempoIntervalo = null;

function ftChipTiempo() {
  let chip = document.getElementById("ft-tiempo");
  if (!chip) {
    chip = document.createElement("p");
    chip.id = "ft-tiempo";
    chip.className = "ft-tiempo";
    const encabezado = document.querySelector(".wordle-header");
    if (encabezado) encabezado.appendChild(chip);
  }
  return chip;
}

function ftPintarTiempo(restante) {
  const chip = ftChipTiempo();
  const minutos = Math.floor(restante / 60);
  const segundos = String(restante % 60).padStart(2, "0");
  chip.textContent = `\u23F1 ${minutos}:${segundos}`;
  chip.classList.toggle("agotandose", restante <= 10);
}

function ftDetenerCronometro() {
  if (ftTiempoIntervalo) clearInterval(ftTiempoIntervalo);
  ftTiempoIntervalo = null;
}

function ftIniciarCronometro(segundos, alAgotarse) {
  ftDetenerCronometro();
  if (segundos === null || segundos === undefined) return;
  let restante = Math.max(0, Math.floor(segundos));
  ftPintarTiempo(restante);
  if (restante <= 0) {
    // el reloj del servidor puede ir ~1s detras del nuestro: reintentar
    // con un respiro en vez de martillar el endpoint
    setTimeout(alAgotarse, 700);
    return;
  }
  ftTiempoIntervalo = setInterval(() => {
    restante -= 1;
    ftPintarTiempo(restante);
    if (restante <= 0) {
      ftDetenerCronometro();
      alAgotarse();
    }
  }, 1000);
}
