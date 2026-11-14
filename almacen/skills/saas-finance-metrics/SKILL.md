---
name: saas-finance-metrics
description: "Metricas financieras SaaS y economia unitaria: LTV, CAC, Churn, Payback, MRR/ARR waterfall y regla del 40."
trigger: model_decision
---

# SaaS Finance & Unit Economics Mastery

## 1. Formulas Fundamentales de Economia Unitaria
- **CAC (Coste de Adquisicion):** $\text{CAC} = \frac{\text{Gastos Ventas + Marketing}}{\text{Nuevos Clientes Adquiridos}}$
- **LTV (Lifetime Value):** $\text{LTV} = \frac{\text{ARPU (Ingreso Medio Mensual)} \times \text{Margen Bruto \%}}{\text{Tasa de Churn Mensual \%}}$
- **Ratio LTV / CAC (Salud del Negocio):**
  * `< 1.5x`: Destruccion de capital (inviable).
  * `3.0x - 4.0x`: Nivel optimo de inversion y rentabilidad.
  * `> 5.0x`: Negocio hiper-rentable o infrainversion en crecimiento.
- **Payback Period (Meses de Recuperacion):** $\text{Payback} = \frac{\text{CAC}}{\text{ARPU} \times \text{Margen Bruto \%}}$ (Meta: $\le 12\text{ meses}$).

## 2. Cascada de MRR (MRR Waterfall)
Calcular el flujo recurrente mensual en balance cerrado:
$$\text{MRR Final} = \text{MRR Base} + \text{Nuevos} + \text{Expansion (Upgrades)} - \text{Contraccion (Downgrades)} - \text{Churn (Cancelaciones)}$$

## 3. Regla del 40 (Benchmark de Inversion)
$$\text{Tasa de Crecimiento Anual \%} + \text{Margen de Flujo de Caja Libre \%} \ge 40\%$$
Todo diagnostico financiero debe emitir primero el semaforo de viabilidad (Rojo, Amarillo, Verde) con los 3 ratios clave antes de proyectar tablas.
