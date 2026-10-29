# Registro de Aprendizaje y Patrones Optimos (Learnings Template)
# Formato: [Contexto] -> [Forma Generica A (Rechazada)] -> [Forma B de Saul (Adoptada)] -> [Tokens Ahorrados]
# ==============================================================================

## 1. Patrones de Decision y Atajos de Arquitectura

### [Patron #001]: Resolucion de Consultas con Filtros Dinamicos
- **Contexto:** Se requiere filtrar elementos por estado, fecha y categoria en una API.
- **Forma Generica A (Rechazada):** Crear 3 endpoints separados o meter multiples `if/else` encadenados con queries redundantes (gasto excesivo de tokens y lineas).
- **Forma B de Saul (Adoptada):** Un unico endpoint parametrizado con un constructor de clausulas `WHERE` dinamico, tipado estricto y early return si los parametros son nulos.
- **Ahorro de Tokens & Latencia:** ~50% menos tokens en prompts posteriores y una sola conexion a base de datos.

### [Patron #002]: Enrutamiento en Micro-Servidores Node
- **Contexto:** Construccion de API REST ligera sin el peso de Express o Nest.js.
- **Forma Generica A (Rechazada):** Instalar frameworks pesados con docenas de dependencias y middlewares de logging inutiles para desarrollo.
- **Forma B de Saul (Adoptada):** Servidor HTTP minimalista basado en Polka o Fastify con enrutamiento por arbol de prefijos (trie) y middlewares planos.
- **Ahorro de Tokens & Latencia:** Arranque instantaneo y menor complejidad ciclomatica.

### [Patron #003]: Diseno de Video Programatico para Redes
- **Contexto:** Crear un Reel o Short explicativo con animaciones y subtitulos.
- **Forma Generica A (Rechazada):** Configurar un proyecto completo de Remotion con React, Webpack y plugins pesados de video para una animacion de 30 segundos.
- **Forma B de Saul (Adoptada):** Usar `hyperframes-director` con HTML5 plano, CSS3 y GSAP `seek(t)` bajo principio Audio-First. Cero dependencias pesadas de compilacion.
- **Ahorro de Tokens & Latencia:** 70% menos tokens de contexto y renderizado determinista en Chromium headless.

---

## 2. Registro de Nuevas Observaciones del Usuario (Llenado Automatico)
<!-- Aqui Nova registra nuevos patrones cuando el usuario corrige o ensena un atajo -->
