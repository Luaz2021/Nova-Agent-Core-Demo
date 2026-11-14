---
name: commercial-legal-counsel
description: "Auditoria y redaccion de contratos mercantiles: MSA, SLA, NDA, leasing de software y deteccion de clausulas trampa."
trigger: model_decision
---

# Commercial Legal Counsel & Contract Hardening

## 1. Clausulas Obligatorias de Blindaje
- **Propiedad Intelectual Condicionada (Conditional IP):** Background IP (herramientas previas, utilidades y frameworks) siempre pertenece al desarrollador. Foreground IP solo se transfiere tras la liquidacion del 100% de facturas.
- **Aceptacion Tacita (Deemed Acceptance):** 5 a 7 dias habiles tras entrega en Staging para objeciones fundadas por escrito; vencido el plazo, el hito queda legalmente aprobado y facturable.
- **Limite de Responsabilidad (Liability Cap):** La responsabilidad total maxima queda topada estrictamente a la cuantia total cobrada en el contrato.
- **Retraso Imputable al Cliente:** Cualquier retraso en feedback o credenciales prorroga dia a dia la fecha final; suspension tras 15 dias con tasa de reanudacion del 10%.

## 2. Auditoria de Deteccion de Trampas Legales (Red Flags)
Al revisar contratos de terceros, marcar en rojo y vetar:
- Indemnizaciones ilimitadas por danos indirectos o lucro cesante.
- Clausulas de no competencia amplias que impidan trabajar con otros clientes del mismo sector.
- Traspaso de derechos previo al cobro total.
- Penalizaciones diarias unilaterales sin causa de fuerza mayor ni reciprocidad.
