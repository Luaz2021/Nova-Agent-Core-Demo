---
name: index-security-deploy
description: "Indice Macro Ciberseguridad, QA & Despliegue: Auditoria Tanque Web, OWASP/STRIDE, Git Guardian, TDD, Chaos QA, refactoring seguro y deploy a 0 EUR."
---

# Index 05 · Ciberseguridad, QA, Debugging & Deploy 0 EUR (1-Hop Router)

## 1. Reglas Operativas & Gatillo de Salto Obligatorio
- **PRIMER PASO DE TODA AUDITORIA (obligatorio, 0 tokens):** `python <NOVA_HOME>\antigravity\scripts\nova_auditoria.py <carpeta>`. Saca cada hallazgo con `archivo:linea` y la linea como prueba (5 capas + dependencias) y lista lo que NO pudo revisar. Prohibido decir "0 vulnerabilidades" o "todo listo" sin haberlo pasado; "compila" no es "auditado". Despues, revisar cada hallazgo leyendo su linea (confirmar o descartar con motivo) y ampliar con logica de negocio e IDOR, cada hallazgo nuevo tambien con `archivo:linea` y prueba.
- **Salto Obligatorio al Almacen:** En toda Auditoria Tanque, pentesting etico, depuracion compleja o paso a produccion, abrir en paralelo las skills nucleares del apartado 2 (`gemini-owasp-sentinel`, `production-audit`, `ai-deploy-advisor`) antes de armar el inventario `X/Y`.
- **Higiene de Secretos, Entropia & Git Guardian:** Prohibido hardcodear credenciales en codigo o commits. Usar hook fisico pre-commit (`scripts\security\install_git_guard.py`) con detector matematico de entropia de Shannon ($H \ge 4.2$) (`entropy_secret_scanner.py`) para cazar secretos sin prefijo y bloquear `.env` en 0.2s.
- **Auditoria SCA Determinista a 0 Tokens:** Ejecutar `scripts\qa\audit_dependencies.py` para bloquear dependencias con CVEs criticos antes de dar por cerrada cualquier entrega.
- **Bastionado Web (OWASP Top 10):** Sanitizar y validar toda entrada con esquemas estrictos (Zod/Pydantic), usar consultas parametrizadas (cero concatenacion SQL), configurar CORS restrictivo, cabeceras CSP/Helmet y Rate Limiting en endpoints de autenticacion o IA.
- **Depuracion Sistematica & Pruebas Fantasma:** Ante un bug, prohibido parchear a ciegas en la rama activa. Primero aislar causa raiz leyendo el stacktrace exacto, reproducir en script/test aislado (`unittest`/`pytest`/`vitest`) y aplicar fix verificado en 1-Shot.
- **Despliegue a 0 EUR:** Priorizar arquitecturas de coste cero fijo: Frontend/SSR en Vercel o Cloudflare Pages, Backend/Workers en Render/Fly.io/Cloudflare Workers, DB en Supabase/Neon y CI/CD con GitHub Actions.

## Trampas de Flash (errores reales ya cometidos)
- Auditoria: no parar tras parchear los inputs evidentes. Recorrer SIEMPRE las 5 capas: (1) entradas e inyecciones, (2) autenticacion, sesiones y JWT, (3) autorizacion e IDOR, (4) cabeceras, CORS y CSP, (5) logica de negocio y rate limiting.
- Un parche que compila no cierra la vulnerabilidad en el repo: buscar el mismo patron en todos los archivos (`grep`) y corregirlos todos.
- IP real detras de Cloudflare: `req.headers['cf-connecting-ip'] || req.ip` en rate limits, auditoria y alertas.
- Alertas por umbral y resumen diario, no un mensaje por intento (fatiga de alertas con botnets).
- Nunca contrasenas en claro en codigo, `.env` versionado, scripts de test, bitacoras ni memoria (ya se volco una en una bitacora).

## Definicion de hecho
- Inventario por las 5 capas con `X/Y` revisados; cada hallazgo corregido con `archivo:linea` y la prueba que lo demuestra (la peticion que antes pasaba y ahora falla).
- `grep` del patron vulnerable en todo el repo = 0 restantes.
- Despliegue: `/healthz` responde y el cron (si lo hay) va protegido con `CRON_SECRET`.

## 2. Mapa de Salto a las Skills (`<NOVA_HOME>/antigravity/` + la ruta `skills/...` de cada entrada)
Abrir con `read_file` en paralelo al ejecutar auditorias, QA o despliegues:
- **Ciberseguridad & Pentesting Etico:** `skills\gemini-security-bastion\SKILL.md` | `skills\gemini-owasp-sentinel\SKILL.md` | `skills\gemini-stride-security\SKILL.md` | `skills\gemini-military-cybersec\SKILL.md` | `skills\agent-security-hardening\SKILL.md` | `skills\gemini-reverse-engineering\SKILL.md` | `skills\gemini-git-guardian\SKILL.md`
- **Testing, QA & Depuracion:** `skills\gemini-tdd-enforcer\SKILL.md` | `skills\gemini-chaos-qa\SKILL.md` | `skills\gemini-systematic-debugger\SKILL.md` | `skills\gemini-playwright-tester\SKILL.md` | `skills\gemini-safe-refactor\SKILL.md` | `skills\dependency-time-traveler\SKILL.md`
- **Despliegue & Produccion:** `skills\ai-deploy-advisor\SKILL.md` | `skills\deployment-patterns\SKILL.md` | `skills\production-audit\SKILL.md` | `skills\gemini-stack-advisor\SKILL.md`
