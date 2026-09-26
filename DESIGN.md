# DESIGN.md — CodeArchaeologist

> Fuente única de verdad visual. Léela antes de tocar cualquier UI. Para *qué* construir y *por qué*,
> lee [PRODUCT.md](PRODUCT.md). Si algo no está aquí, extiende este archivo antes de inventar un estilo.

**Dirección:** *Consola de evidencia*. Un lienzo negro de ingeniería con cromo blanco preciso (hairlines,
tipografía compacta) donde el color solo aparece con significado: naranja señal para la acción primaria,
el espectro de riesgo para severidades y verde para lo verificado. Inspirado en linearity.io, adaptado a
una herramienta densa de uso diario (no a una landing).

- Referencia original (no se usa directamente): [docs/design/reference/](docs/design/reference/).
- Implementación: [frontend/src/styles/tokens.css](frontend/src/styles/tokens.css) (tokens) y
  [frontend/src/components/](frontend/src/components/) (primitivos y dominio).

---

## 1. Principios

1. **El negro es el espacio de trabajo.** Canvas `void` en toda la app. Nada de secciones claras ni tarjetas blancas.
2. **Separar con líneas, no con sombras.** 1px blanco al 10%; nada de elevación flotante.
3. **Color = significado.** Naranja solo en la acción primaria de cada pantalla y en el orbe de enviar a Bob.
   Severidad y verificación usan su propia escala. Nunca decoración.
4. **Densidad con jerarquía.** 14px de cuerpo, 12px en controles, 10px en eyebrows. El espacio crea jerarquía, no vacío.
5. **Evidencia primero.** Rutas `archivo:línea` en mono, siempre clicables, con estado verificado/no verificado.
6. **Nunca solo color.** Cada estado lleva texto y/o glifo (◆ ▲ ● ○ ✓ ✗).

## 2. Tokens

Tres capas. Los componentes usan **solo semánticos** (clases Tailwind generadas desde `@theme`).
Los primitivos existen como variables `--ca-*` y no generan utilidades a propósito.

```
Primitivo (--ca-void)  →  Semántico (--color-canvas → bg-canvas)  →  Componente (Button primary)
```

### 2.1 Primitivos (de la referencia Linearity)

| Primitivo | Valor | Notas |
|---|---|---|
| `--ca-void` | `#000000` | canvas |
| `--ca-near-black` | `#050505` | recess, código |
| `--ca-carbon` | `#292929` | shell del composer de IA |
| `--ca-graphite` | `#4d4d4d` | detalle inactivo |
| `--ca-ash` | `#666666` | **solo decorativo** (3.6:1, no apto para texto) |
| `--ca-steel` | `#808080` | texto sutil (5.3:1) |
| `--ca-fog` | `#999999` | texto de apoyo (7.4:1) |
| `--ca-silver` | `#bfbfbf` | texto secundario, nav |
| `--ca-white` | `#ffffff` | texto primario |
| `--ca-signal-orange` | `#ff4800` | acción primaria |
| `--ca-ember` | `#ff5e23` | hover primario, foco, indicador activo |
| `--ca-electric-yellow` | `#ffd900` | halo del primario, severidad media |
| `--ca-spectrum-*` | `#08c380` `#fd7c0f` `#ff2b2b` `#9500ff` | paradas del *Spectrum Rail* |

### 2.2 Semánticos (usar estos)

| Utilidad | Rol |
|---|---|
| `bg-canvas` | fondo de la app |
| `bg-surface` | paneles, rail de navegación, inspectores (`#050505`) |
| `bg-raised` | filas seleccionadas, hover de listas (blanco 4%) |
| `bg-overlay` | popovers, paleta de comandos (`#0f0f0f`) |
| `bg-control` | inputs y controles (blanco 5%) |
| `bg-composer` | shell del composer de Bob (carbon) |
| `bg-code` / `bg-code-hl` | fondo de código / líneas citadas |
| `text-fg` · `text-fg-2` · `text-muted` · `text-subtle` | blanco · silver · fog · steel |
| `border-line` · `border-line-strong` · `border-line-subtle` | blanco 10% · 18% · 6% |
| `bg-accent` `text-accent` `bg-accent-hover` | naranja señal / ember |
| `text-on-accent` | texto sobre naranja: **negro** (6.2:1). La referencia usa blanco, pero da 3.4:1 y no cumple AA en 12px |
| `text-risk-critical` · `-high` · `-medium` · `-low` · `-info` | escala de severidad (también `bg-`/`border-`) |
| `text-verified` · `text-danger` · `text-warning` | verificado (verde) · error · aviso |
| `bg-activity` / `text-activity` | trabajo en curso (pulso blanco); **nunca** naranja para estados |

Escala de severidad (tomada del espectro de la referencia, nunca naranja señal):

| Severidad | Color | Glifo | Etiqueta |
|---|---|---|---|
| critical | `#ff2b2b` | ◆ | Crítico |
| high | `#fd7c0f` | ▲ | Alto |
| medium | `#ffd900` | ● | Medio |
| low | `#bfbfbf` | ○ | Bajo |
| info | `#808080` | · | Info |

### 2.3 Tipografía

| Familia | Token | Uso |
|---|---|---|
| Space Grotesk Variable (sustituto de AcidGrotesk) | `font-display` | títulos, **siempre peso 400** |
| Inter Variable | `font-sans` | UI y cuerpo |
| JetBrains Mono Variable | `font-mono` | código, rutas, ids, cifras técnicas |

Autoalojadas con `@fontsource-variable/*` (sin CDN).

| Utilidad | Tamaño / interlineado | Uso |
|---|---|---|
| `text-micro` | 10px / 1.4, `tracking-eyebrow` (0.14em), MAYÚSCULAS | eyebrows, cabeceras de tabla |
| `text-caption` | 12px / 1.5 | controles, botones, metadatos |
| `text-body` | 14px / 1.5 | cuerpo, nav |
| `text-title` | 17px / 1.3 display | títulos de panel |
| `text-heading` | 21px / 1.25 display | título de pantalla |
| `text-display` | 34px / 1.2 display, -0.01em | solo la pantalla Proyectos |
| `text-code` | 12px / 1.7 mono | código |

Cifras: `tabular-nums`. Títulos cortos: `text-balance`. Descripciones: `text-pretty`.

### 2.4 Espacio, radios, sombras y movimiento

- **Espacio:** base 4px (escala Tailwind por defecto). Ritmo habitual: 4 · 8 · 12 · 16 · 24 · 56.
- **Radios** (concéntricos: exterior = interior + padding):

| Utilidad | Valor | Uso |
|---|---|---|
| `rounded-pill` | 9999px | botones, chips, segmentados, búsqueda |
| `rounded-panel` | 12px | paneles, popovers, paleta |
| `rounded-inner` | 8.57px | elementos dentro de paneles, bloques de código |
| `rounded-composer` | 17.14px | composer de Bob, zona de carga |
| `rounded-tick` | 2.57px | marcadores diminutos |

- **Sombras:** ninguna salvo `shadow-glow` (halo amarillo del botón primario), `shadow-inset-accent`
  (1px ember interior, selección fuerte) y `shadow-pop` (solo popovers/paleta).
- **Movimiento:** 150ms `ease-out` en hover/press (`transition-[color,background-color,border-color,box-shadow,transform]`),
  200ms para abrir paneles (opacity + translate). Nunca `transition-all`. `prefers-reduced-motion` desactiva
  animaciones no esenciales (ya en `tokens.css`).

### 2.5 Firma visual: *Spectrum Rail*

Gradiente `bg-spectrum` (verde → naranja → rojo → violeta). **Solo** como línea de 2px:
- barra de estado mientras Bob analiza (animada, se detiene con reduced motion);
- subrayado de una frase en la pantalla Proyectos.
Nunca como fondo, en texto ni en bordes de paneles.

## 3. Layout (app shell)

```
┌ TopBar 48px: marca · selector de proyecto · ⌘K · estado de Bob · alternar IA ─────────┐
├ NavRail 224px ┬ Workspace (scroll propio, padding 24px) ┬ Panel de IA 360px ─────────┤
│ bg-surface    │ bg-canvas                              │ bg-surface, colapsable (⌘J)│
├───────────────┴────────────────────────────────────────┴─────────────────────────────┤
└ StatusBar 28px: etapa del análisis · modo · backend · Bob · sha ─────────────────────┘
```

- `< lg`: el NavRail pasa a cajón (botón de menú) y el panel de IA a cajón derecho (cerrado al cargar).
- **Las vistas responden al ancho del workspace, no de la ventana:** `<main>` es `@container` y las rejillas
  internas usan variantes de contenedor (`@3xl:grid-cols-2`, `@4xl:...`). Así el layout se adapta cuando el
  panel de Bob está abierto. No uses `lg:`/`xl:` dentro de `views/`.
- Estado navegable en la URL (hash): `#/p/<job>/<sección>?f=F-1&file=app.py&line=78&node=<id>&play=1`
  (`play=1` reproduce la sesión al abrirla; lo usa la vitrina).
- Las vistas usan **secciones con hairline**, tablas, listas, árboles, grafos y split panes. Tarjetas solo
  para objetos reales (un hallazgo, un archivo descargable).

## 4. Componentes

Primitivos en `components/ui/`:

| Componente | Especificación |
|---|---|
| `Button` primary | píldora, `bg-accent`, `text-on-accent` (**negro**, semibold), borde ember, `shadow-glow`, hover `bg-accent-hover`, press `scale-[0.97]`. **Una por pantalla.** |
| `Button` secondary | píldora, `bg-control`, borde `line-strong`, texto `fg` |
| `Button` ghost | sin borde, `text-fg-2`, hover `bg-raised` |
| `IconButton` | 32px (hit 40px), `rounded-pill`, `aria-label` obligatorio |
| `Chip` | píldora 22px, `text-caption`, borde `line` |
| `SeverityBadge` | glifo + etiqueta, color de severidad, sin relleno |
| `ModeBadge` | mono 10px: LIVE (verde) · IMPORTADO (silver) · EJEMPLO (amarillo) |
| `EvidenceRef` | mono `path:línea`, ✓ verde verificado / ✗ rojo, clicable |
| `Section` | eyebrow `text-micro` + título display + contenido, separado por `border-line` |
| `Panel` | `bg-surface`, `border-line`, `rounded-panel` |
| `Meter` | barra 4px `bg-raised` con relleno semántico y valor tabular |
| `Kbd` | mono 10px, borde `line-strong`, `rounded-tick` |
| `EmptyState` / `ErrorState` | qué pasó · por qué importa · qué hacer (PRODUCT §28–29) |

Dominio en `components/domain/`:

| Componente | Rol |
|---|---|
| `AnalysisStatus` | progreso por etapas reales (✓ ● ○ ✗) + Spectrum Rail mientras corre |
| `RiskRow` · `FindingInspector` | hallazgo en lista densa · revelación progresiva (por qué → evidencia → impacto → acción) |
| `EvidenceRef` · `CodeViewer` | cita `archivo:línea` verificable · superficie de código con marcas de severidad en el margen |
| `RepositoryTree` | árbol con severidad, nº de hallazgos y funciones por archivo |
| `ModuleMap` · `CallGraph` | mapa de módulos por capas (SVG) · grafo de funciones con capas de hallazgos e impacto |
| `MigrationSequence` · `PertRange` | pasos del corte con dependencias · rango PERT como regla |
| `AskBob` (`AskComposer`, `AskAnswerView`) | composer carbon + orbe; respuesta en hechos / inferencias / recomendaciones / desconocido |

Consola de la sesión en `components/domain/console/` (sección **Sesión de Bob** y cualquier sección mientras
un análisis corre):

| Componente | Rol |
|---|---|
| `AnalysisConsole` | contenedor: riel de etapas + panel de la etapa seleccionada (sigue a la etapa activa); modos en vivo, reproducción y sesión cerrada |
| `StageRail` | 5 etapas con estado (✓ ● ✗ o número), métrica de una línea y duración; botón con `aria-current="step"` |
| `AgentsPanel` | contadores (turnos, lecturas, subagentes, coste vs tope) · plan de Bob · feed de razonamiento y acciones |
| `AgentConstellation` / `AgentList` | orquestador y subagentes: arista discontinua blanca animada = trabajando, verde continua = terminó. `AgentList` sustituye al SVG por debajo de `@xl` |
| `PreparingPanel` · `ValidationPanel` · `TestsPanel` · `ReadyPanel` | controles del ZIP + inventario · cada cita ✓/✗ · pruebas legado/moderno · expediente y siguientes pasos |
| `useReplay` | cabezal sobre el `t` real de los eventos, comprimido a ~26 s; con `prefers-reduced-motion` no hay reproducción (se muestra la sesión completa y se oculta el botón) |

Reglas de la consola:
- Todo sale de `GET /api/audits/{id}/events`: nada de progreso simulado ni porcentajes inventados.
- Trabajo en curso = token `activity` (blanco pulsante). Terminado = `verified`. El naranja no se usa para estados.
- Las sesiones grabadas se rotulan como tales («Sesión real de IBM Bob grabada…»).
- Nunca mostrar contenido de archivos del repositorio en el feed: solo rutas relativas, títulos y resúmenes.

Shell en `components/shell/`: `AppShell`, `TopBar`, `NavRail`, `StatusBar`, `CommandPalette` (⌘K), `AIPanel` (⌘J), `BrandMark`
(testigo de sondeo con estratos; el inferior en naranja señal).

## 5. Accesibilidad

- Contraste: texto normal ≥ 4.5:1 (nunca `--ca-ash` para texto). Foco visible: anillo 2px ember + offset 2px.
- Semántica: `nav`, `main`, `aside`, `header`; tablas con `th`; diálogos con `role="dialog"` + `aria-modal` + trampa de foco
  (`components/ui/useFocusTrap.ts`) y fondo `inert`. Segmentados: una parada de Tab y flechas. Nodos SVG: `tabIndex` + anillo propio.
- No declares roles ARIA compuestos (`tree`, `grid`, `menu`) sin implementar su teclado completo: usa listas y botones.
- Todo control con teclado; atajos: `⌘K` paleta, `⌘J` panel de IA, `Esc` cierra.
- Estados nunca solo por color; `aria-live="polite"` en el estado del análisis y en respuestas de Bob.

## 6. Qué no hacer

- Gradientes de fondo, glows fuera del botón primario, glassmorphism, violeta "IA", sparkles por todas partes.
- `rounded-xl` genérico en todo, tarjetas dentro de tarjetas, tres tarjetas de métricas en fila por defecto.
- Valores arbitrarios (`bg-[#111]`, `text-[13px]`, `rounded-[10px]`) cuando existe un token.
- Naranja señal como relleno de superficies o para severidades.
- Cifras sin fuente: toda cifra viene del backend (dossier, grafo, arquitectura). Si no hay dato, dilo.

## 7. Cómo extender

1. ¿Existe un token semántico? Úsalo. Si no, añádelo en `tokens.css` (primitivo → semántico) **y** documéntalo aquí.
2. ¿Existe un primitivo en `components/ui`? Compón con él antes de crear otro.
3. Nuevo componente de dominio: documenta aquí su rol en una línea de la tabla §4.
