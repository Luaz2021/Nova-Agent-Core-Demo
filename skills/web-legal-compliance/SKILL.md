---
name: web-legal-compliance
description: "Auditor y generador legal web multi-jurisdiccion: RGPD/LSSI (España/UE), Terms/CCPA (EE.UU./Demos) y Ley 29733 (Peru)."
trigger: model_decision
---

# Web Legal Compliance & Privacy Auditor (Multi-Jurisdicción)

Esta habilidad asegura que cualquier sitio web, ecommerce, aplicación SaaS, landing de reservas o captación de leads cumpla con las normativas legales vigentes según el mercado donde opere, protegiendo al negocio de sanciones y demandas.

---

## 1. Regla de Oro: Preguntar Jurisdicción Antes de Redactar

Antes de generar o auditar cualquier texto legal, el agente debe formular una pregunta rápida para identificar el territorio de aplicación:

> *"¿Para qué país o mercado principal estamos preparando este proyecto? (Ej: España/UE, EE.UU./Global, o pruebas/demo)"*

### Regla para Proyectos Demo / Pruebas / MVP:
Si el usuario indica que es un **proyecto de prueba, demo, portafolio o prototipo**, el agente aplica automáticamente el **estándar global de Estados Unidos**:
- `Terms of Service (ToS)` con cláusulas robustas de "AS IS" (sin garantías), limitación de responsabilidad (*limitation of liability*) y arbitraje.
- `Privacy Policy` ligera compatible con el estándar general de EE.UU. (CCPA / COPPA / CalOPPA) y aviso básico de cookies.

---

## 2. Matriz de Jurisdicciones

### A. Estándar Global / Estados Unidos (Para Demos, SaaS y Comercio Global)
1. **Terms of Service (Términos de Servicio):**
   - Uso aceptable del servicio y propiedad intelectual.
   - **Cláusula "AS IS":** El software se ofrece tal cual, sin garantías explícitas ni implícitas.
   - **Limitación de Daños:** Límite máximo de compensación por errores técnicos o caídas del servicio.
   - Ley aplicable y resolución de disputas (ej. Estado de Delaware o California).
2. **Privacy Policy (Política de Privacidad EE.UU.):**
   - Qué datos se recopilan automáticamente (IP, User-Agent, logs).
   - Uso de proveedores de análisis (Google Analytics, Stripe).
   - Derechos del consumidor bajo la CCPA/CPRA de California (Do Not Sell My Info).
   - Aviso de protección a menores de 13 años (COPPA).
3. **Banner de Cookies:**
   - Modelo "Opt-out" o aviso informativo flotante: *"Utilizamos cookies para mejorar la experiencia..."*.

---

### B. España y Unión Europea (Para Negocios Locales, Autónomos y Ecommerces UE)
Aplica el marco normativo más estricto del mundo (**RGPD, LOPDGDD y LSSI-CE**):
1. **Aviso Legal (LSSI Art. 10):**
   - Nombre o Razón Social, NIF/CIF, domicilio fiscal, correo de contacto y datos de Registro Mercantil.
2. **Política de Privacidad y Primera Capa en Formularios (RGPD Art. 13):**
   - Justo antes del botón de enviar, tabla visible con: *Responsable, Finalidad, Legitimación y Derechos*.
   - Casilla de verificación desmarcada obligatoria: `[ ] He leído y acepto la Política de Privacidad`.
3. **Banner de Cookies (Guía AEPD 2024+):**
   - Modelo estricto "Opt-in": ninguna cookie de terceros o análisis se ejecuta antes del clic.
   - Botón **"Rechazar"** obligatorio en el primer nivel, con idéntico tamaño y visibilidad que el de **"Aceptar"**.
4. **Comercio Electrónico y Reservas:**
   - Precios desglosados con IVA, derecho de desistimiento de 14 días naturales y canal de reclamaciones.

---

### C. Latinoamérica (México, Perú, Colombia, etc.)
- Cumplimiento de leyes locales de protección de datos personales (LFPDPPP en México, Ley 29733 en Perú, Ley 1581 en Colombia).
- Aviso de Privacidad Integral y Simplificado en formularios.
- Mecanismos para el ejercicio de derechos ARCO (Acceso, Rectificación, Cancelación y Oposición).

---

## 3. Checklist de Auditoría en 60 Segundos

1. `[ ]` ¿Se conoce la jurisdicción del proyecto o se acordó modo demo (EE.UU.)?
2. `[ ]` ¿Los enlaces a Términos/Aviso Legal y Privacidad están visibles en el footer?
3. `[ ]` ¿Los formularios cumplen con la capa informativa de la jurisdicción elegida?
4. `[ ]` ¿El comportamiento de cookies respeta el estándar correspondiente (Opt-in para UE, Opt-out para EE.UU./Demo)?
