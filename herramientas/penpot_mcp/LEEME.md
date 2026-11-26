# MCP de Penpot para Nova (Windows, macOS y Linux)

Penpot (design.penpot.app, gratis) conectado a Nova por el MCP oficial `@penpot/mcp` (version fija en `lanzar.py`).
Necesita **Node.js** (npm/npx) instalado.

## Como funciona
- El MCP `penpot` va **APAGADO**. El hook lo enciende solo cuando hablas de Penpot (`nova_hook_turno.py`, PIDE_MCP) con
  `scripts/nova_mcp.py activar penpot` (crea la entrada en tu `mcp_config.json` si no existe) y se apaga, parando su
  servidor, al cerrar Antigravity.
- Al encenderse, Antigravity ejecuta `lanzar.py` con el Python de Nova:
  1. si no hay nada en el puerto 4401, instala `@penpot/mcp` en `~/nova_penpot_mcp` (la 1a vez tarda ~1-2 min) y lo
     arranca oculto;
  2. `npx mcp-remote` conecta Antigravity con `http://localhost:4401/mcp`.
- Puertos: 4400 plugin · 4401 MCP · 4402 conexion plugin-servidor · 4403 REPL (solo local).

## Lo que haces tu (una vez por sesion de diseno)
1. Abrir el archivo en Penpot, menu **Plugins** -> cargar `http://localhost:4400/manifest.json`.
2. Abrir el plugin y pulsar **"Connect to MCP server"**. Deja esa pestana abierta mientras Nova trabaja.
3. Si tu navegador no deja conectar con localhost (Brave Shields, bloqueo de red privada): permitelo para `design.penpot.app`.

## Si falla
- Log: `~/nova_penpot_mcp/servidor.log`.
- `ERR_PNPM_IGNORED_BUILDS`: pnpm 12 bloquea esbuild/sharp; `lanzar.py` les da permiso solo.
- Usa el paquete publicado de npm, no el repositorio de GitHub (su rama de desarrollo puede no compilar).
