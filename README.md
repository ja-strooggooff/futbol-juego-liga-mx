# Futbol Juego Liga MX
Una recreación de Futbol11 pero más inmersiva — pensada para esas noches 
donde te metes a la página y terminas horas jugando online con tus amigos. 
Adaptado a Liga MX y Liga Argentina. Proyecto de aprendizaje para practicar 
flujo de trabajo en GitHub (branching, PRs, code review) y prepararnos para 
hackathons futuros.

## Por qué este proyecto
Queríamos un proyecto real — no solo tutoriales — para aprender:
- Colaboración en Git/GitHub (branch -> commit -> push -> PR -> merge)
- Trabajar en equipo en el mismo código sin pisarnos
- Construir algo que de verdad usaríamos (todos somos fans del fútbol)

## La idea (fase inicial, puede cambiar)
Recrear los juegos/modos de Futbol11, pero:
- Más inmersivo — pensado para sesiones largas, no solo una partida rápida
- Multijugador online con amigos (no solo contra la computadora)
- Adaptado a Liga MX y Liga Argentina (equipos, jugadores, ligas reales)

## Status
En desarrollo — servidor Flask base funcionando con página principal y API de jugadores.

## Equipo y roles

| Nombre | Rol | Responsabilidad |
|---|---|---|
| Jorge Alberto Stroogooff Jaramillo | Backend | Servidor Python, rutas Flask, base de datos de jugadores, lógica del juego |
| Daniel Eduardo Santiago Gutierrez | Frontend | HTML, CSS, diseño visual, experiencia de usuario |
| Juan Carlos Livas Reyes | Full Stack + DevOps | JavaScript, conexión frontend-backend, deploy en internet, revisión de PRs |

## Stack
- **Backend:** Python + Flask
- **Frontend:** HTML + CSS + JavaScript
- **Base de datos:** SQLite (por ahora) → PostgreSQL en producción
- **Deploy:** Por definir (Render / Railway)
- **Control de versiones:** Git + GitHub (branch → PR → merge)