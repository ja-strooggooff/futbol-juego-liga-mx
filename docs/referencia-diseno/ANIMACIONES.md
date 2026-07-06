# Referencia visual y de animaciones — FutTrivia

## Concepto general
Fusión de la pasión futbolera latinoamericana con un estilo minimalista,
sutil y visualmente limpio. Fondo casi negro con tinte verde sutil.
Elementos en outline blanco/verde. Animaciones satisfactorias pero sin
volverse repetitivas o molestas.

## Logo principal
Una portería (arco de fútbol) en estilo "outline" plano — el mismo
estilo de línea que aparece en el escudo de una playera de fútbol
tipo Argentina (rayas celeste/blanca), donde el escudo tiene una
cancha/portería dibujada dentro. El logo se muestra en tamaño
proporcional y minimalista, centrado en la pantalla de landing.

## Animación de transición (la pieza central)
Una pelota de fútbol que:
1. Gira en 2D (efecto de rotación) durante la transición entre pantallas
2. Se anima "entrando al arco/portería" cada vez que el usuario entra
   a un juego — es decir, la pelota rueda hacia la portería del logo
   y esa acción dispara el cambio de pantalla
3. Esta misma animación de "pelota entrando al arco" se repite como
   mecánica de transición entre: landing → selección de juegos, y
   selección de juegos → juego individual

## Pantalla de landing
- Logo del arco centrado, tamaño proporcional (no ocupa toda la pantalla)
- Sin login obligatorio: un solo botón "Jugar" (login queda pendiente
  de decisión del equipo, no implementar todavía)
- Animación de la pelota disponible como parte del estado inicial/idle

## Pantalla de selección de juegos (Opción 2 del sketch original)
- Layout dividido tipo "portería" — los 5 juegos viven como celdas
  dentro de un marco grande de arco de fútbol
- Los 5 juegos: Wordle Fútbol, Immaculate Grid (Grid de Equipos),
  Adivina el Escudo, Trivia Rápida, Conexiones
- Solo Wordle y Grid están disponibles actualmente — el resto debe
  mostrarse como "Próximamente" (deshabilitados visualmente pero
  visibles en el layout)
- Al entrar a un juego disponible, se dispara la animación de la
  pelota entrando al arco como transición

## Paleta de colores
- Fondo: casi negro con tinte verde sutil
- Elementos: outline blanco y verde
- Estilo general: minimalista, no cargado, espacios en blanco/negro
  generosos

## Stack técnico recomendado
Vanilla HTML/CSS/JS como templates Jinja2, para integración directa
con Flask (no React ni frameworks externos).