---
name: env-drift-sentinel
description: Mantiene la paridad de variables de entorno (.env) entre PC y Laptop de forma segura mediante un cofre privado en Google Drive (Antigravity/vault/) sin exponer secretos en repositorios Git.
---

# Env Drift Sentinel (Sincronización Segura de Secretos)

## Propósito
Evitar que al pasar de PC a Laptop (o viceversa) los proyectos fallen por variables de entorno faltantes (`.env`), protegiendo siempre que ningún secreto se filtre a Git.

## Arquitectura de Cofre (Drive Vault)
- **Ubicación del Cofre:** `<GoogleDrive>\Antigravity\vault\<nombre_proyecto>\.env.vault`
- **Referencia Pública:** El repositorio Git solo contiene `.env.example` con claves vacías o de ejemplo.
- **Git Guardian:** Bloqueo absoluto de commits con archivos `.env` sin ignorar.

## Protocolo de Operación
1. **Auditoría de Paridad:**
   - Al abrir un proyecto en una nueva máquina, comparar las claves requeridas en `.env.example` con el `.env` local.
2. **Sincronización desde el Cofre:**
   - Si faltan variables en local, consultar el cofre seguro en Drive para completar los valores faltantes.
3. **Actualización de Nuevas Claves:**
   - Si se añade una nueva variable en local, reflejar el nombre de la clave en `.env.example` y respaldar el valor en el cofre seguro de Drive.
