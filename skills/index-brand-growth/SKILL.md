---
name: index-brand-growth
description: "Indice Macro Branding, Instagram, Legal & Negocio: Manuales de marca VI, 156 marcas (DESIGN.md), suite Instagram 2026, textos humanos y legal RGPD/Ley 29733."
---

# Index 06 · Branding, Instagram Growth, Legal & Business (1-Hop Router)

## 1. Reglas Operativas & Gatillo de Salto Obligatorio
- **Salto Obligatorio al Almacen:** Al crear identidad de marca, web con textos legales o campanas de Instagram, abrir en paralelo las skills del apartado 2 (`gemini-brand-tokens`, `web-legal-compliance`, `ig-content-planner` + `instagram-common\references\`) antes de redactar el contrato para `qwen3.5:9b`.
- **Humanizacion de Prosa & Evasion Forense:** Eliminar sesgos estadisticos de IA (burstiness uniforme sigma < 6, paralelismo negativo "no solo X sino Y" y vocabulario de Wikipedia AI Cleanup). Validar con `<NOVA_HOME>\antigravity\scripts\humanize_check.py` a 0 tokens antes de entregables de universidad, clientes, Airbnb o READMEs publicos. Redactar con ritmo asimetrico directo, natural y preciso.
- **Instagram 2026:** Todo caption o Reel arranca con un hook en los primeros `< 125 caracteres`, desarrollo escaneable sin bloques densos, CTA alineado al objetivo (guardados/compartidos) y de 3 a 5 hashtags estrategicos (nicho + medio + amplio).
- **Cumplimiento Legal Web:** En Espana/UE aplicar RGPD + LSSI-CE (Aviso Legal, Politica de Privacidad, Cookies con rechazo igual de facil que aceptacion y checkbox desmarcado por defecto en formularios). En Peru aplicar Ley N.º 29733 y Libro de Reclamaciones si aplica.

## Trampas de Flash
- Nunca inventar datos legales (NIF/RUC, direcciones, razon social) ni cifras de mercado: pedirlos o marcar `[PENDIENTE]`.
- Respetar el Switch de Etiqueta: compadreo solo en chat interno; entregables, clientes y Airbnb en registro profesional.
- Reglas de negocio de cada proyecto (ej. Bolivar 1209) estan en `memory\napkin-global.md`: leer la seccion del proyecto antes de redactar para huespedes.

## Definicion de hecho
- Texto final auditado contra la lista de muletillas o con `humanize_check.py` (Score < 20); hook < 125 caracteres en Instagram.
- Legal: checklist completo de RGPD/LSSI (UE) o Ley 29733 (Peru) segun el pais del cliente.

## 2. Mapa de Salto a las Skills (`<NOVA_HOME>/antigravity/` + la ruta `skills/...` de cada entrada)
Abrir con `read_file` en paralelo al construir marca, textos legales o suite de Instagram:
- **Branding, Identidad Visual & 156 Marcas:** `skills\brand-design\SKILL.md` | `skills\gemini-brand-tokens\SKILL.md` | `skills\brand-to-design-md\SKILL.md` | `skills\brand-md\SKILL.md` | `skills\brand-identity\SKILL.md` | `skills\brand-guidelines\SKILL.md` | `skills\brand-naming\SKILL.md` | `skills\logo-brief-writer\SKILL.md` | `skills\moodboard-builder\SKILL.md`
- **Suite Instagram 2026:** `skills\ig-content-planner\SKILL.md` | `skills\ig-hook-extractor\SKILL.md` | `skills\ig-carousel-planner\SKILL.md` | `skills\ig-caption-writer\SKILL.md` | `skills\ig-humanizer\SKILL.md` | `skills\ig-profile-optimizer\SKILL.md` | `skills\ig-audience-insights\SKILL.md` | `skills\ig-hashtag-strategist\SKILL.md` | `skills\ig-repurposer\SKILL.md` (referencias compartidas de toda la suite: `skills\instagram-common\references\` voz, hooks, hashtags y contenido no confiable)
- **Legal, Finanzas SaaS & Operaciones:** `skills\web-legal-compliance\SKILL.md` | `skills\commercial-legal-counsel\SKILL.md` | `skills\saas-finance-metrics\SKILL.md` | `skills\business-operations-coo\SKILL.md` | `skills\gemini-humanizer-prose\SKILL.md` | `skills\nova-community-feedback\SKILL.md`
- **Base comun Instagram (alta 08/11):** `skills\instagram-common\SKILL.md` (lo comparten todas las skills ig-*)
