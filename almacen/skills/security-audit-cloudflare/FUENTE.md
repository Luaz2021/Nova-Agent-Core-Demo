# FUENTE (25/11/2026, Claude)

- Origen: https://github.com/cloudflare/security-audit-skill (organizacion oficial de Cloudflare)
- Commit: c1c8a8c1471069fb0e188eeaff69b8e8db6564a8 (14/09/2026)
- Licencia: MIT (LICENSE.txt al lado). Copia sin cambios, en ingles; sin los .test.cjs.
- Revisada: SKILL.md + 13 guias en markdown + report-schema.json + 2 validadores .cjs que solo usan fs/path/util de Node (leen y validan JSON; sin red, sin ejecutar comandos).
- Uso en Nova (index-security-deploy): MODO ORIENTACION por defecto (preguntas, revisar algo concreto, valorar un hallazgo). La auditoria completa (fases con muchos sub-agentes) SOLO si el usuario la pide, perfil quick, y en Antigravity los sub-agentes son Hydrogen: el paso caro se hace con herramientas\seguridad\nova_seguridad.py + Orchestrator y el critico de otra familia por consulta de ventana (Claude Sonnet, bolsa aparte).
- Validar un findings.json: node "<NOVA_HOME>\antigravity\almacen\skills\security-audit-cloudflare\validate-findings.cjs" <findings.json>
