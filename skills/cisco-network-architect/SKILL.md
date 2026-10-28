---
name: cisco-network-architect
description: "Ingeniero de redes Cisco (CCNA/CCNP, Packet Tracer): VLSM, VLANs, 802.1Q, OSPF, BGP, NAT, ACLs, STP y VPNs."
trigger: model_decision
---

# Cisco Network Architect (Ingeniería de Redes & Telecomunicaciones)

Esta habilidad cubre el diseño, configuración, auditoría y resolución de problemas de infraestructuras de red empresariales basadas en Cisco IOS, Packet Tracer, GNS3 y entornos de producción.

---

## 1. Cuándo se Activa
Se activa automáticamente cuando el usuario dice:
- *"Configura este router/switch Cisco"*, *"Diseña esta topología de red en Packet Tracer"*, *"Calcula el direccionamiento VLSM/CIDR para estas subredes"*, *"Configura OSPF/BGP/VLANs"*, *"Crea una lista de control de acceso (ACL)"*, *"Audita la seguridad de esta red o soluciona un bucle STP"*, *"Configura NAT o DHCP en Cisco IOS"*.

---

## 2. Los 5 Bloques de Redes Cisco

### Bloque 1: Switching Empresarial (Cisco IOS L2/L3)
- **VLANs & 802.1Q Trunking:** Creación de VLANs segmentadas, asignación de puertos access y enlaces troncales tagged.
- **Spanning Tree Protocol (STP / Rapid-PVST+):** Prevención de tormentas de broadcast y bucles de conmutación mediante Bridge Priority y Root Bridge election.
- **EtherChannel (LACP / PAgP):** Agregación de enlaces para alta disponibilidad y ancho de banda multiplicado.
- **Seguridad en Switch (Port Security):** Limitación de MACs por puerto, modo `shutdown` o `restrict` ante intrusos.

### Bloque 2: Routing Dinámico & Inter-VLAN (L3)
- **Router-on-a-Stick & SVI (Switch Virtual Interfaces):** Enrutamiento entre subredes mediante subinterfaces o switches multicapa.
- **OSPFv2 / OSPFv3:** Configuración multi-área (Area 0 Backbone), cálculo de costes métricos, autenticación MD5/SHA y router-id.
- **BGP (Border Gateway Protocol):** Enrutamiento entre Sistemas Autónomos (eBGP e iBGP) para salidas a Internet redundantes.

### Bloque 3: Direccionamiento IP & Subnetting (VLSM)
- Cálculo matemático preciso de máscaras de subred de longitud variable (VLSM) optimizando rangos `/24`, `/26`, `/29`, `/30` para WANs sin desperdiciar IPs.
- Configuración de servidores **DHCP** locales y **DHCP Relay (ip helper-address)**.

### Bloque 4: Seguridad Perimetral & Traducción de Direcciones (NAT/PAT)
- **ACLs Estándar y Extendidas:** Filtrado por IP origen/destino, puertos TCP/UDP específicos y bloqueo de tráfico no autorizado.
- **NAT / PAT (Port Address Translation):** Sobrecarga de IP pública (`ip nat inside source list ... interface ... overload`) para salida a internet.
- **VPNs Seguras:** Túneles IPsec Site-to-Site y VPNs de acceso remoto con cifrado AES-256.

### Bloque 5: Hardening de Dispositivos Cisco (Leyes de Seguridad)
1. Cifrado de contraseñas de consola y enable: `enable secret ...`, `service password-encryption`.
2. Acceso remoto exclusivo por **SSH v2** (prohibido Telnet): generación de claves RSA de 2048 bits.
3. Desactivación de servicios inseguros: `no ip http server`, `no cdp run` en interfaces externas.
4. Banner de advertencia legal: `banner motd #ACCESO RESTRINGIDO - AUTORIZADOS SOLAMENTE#`.
