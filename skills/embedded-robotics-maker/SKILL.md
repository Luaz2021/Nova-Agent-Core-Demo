---
name: embedded-robotics-maker
description: "Ingenieria de robotica, Arduino, ESP32 e IoT: esquematicos, PWM/Puente H, sensores I2C/SPI, MQTT y firmware con millis()."
trigger: model_decision
---

# Embedded Systems & Robotics Maker (Robótica, Arduino & IoT)

Esta habilidad cubre el diseño electrónico, programación de firmware, integración de sensores/actuadores y arquitectura de robots y dispositivos IoT con microcontroladores (Arduino Uno/Nano, ESP32, ESP8266, STM32 y Raspberry Pi Pico).

---

## 1. Cuándo se Activa
Se activa automáticamente cuando el usuario dice:
- *"Escribe el código para Arduino / ESP32"*, *"¿Cómo conecto este sensor o motor?"*, *"Calcula la resistencia para este LED o transistor"*, *"Diseña un robot siguelíneas / evasor de obstáculos"*, *"Conecta este ESP32 por WiFi / MQTT / Bluetooth"*, *"Programa una máquina de estados para robótica"*, *"Soluciona rebotes en pulsadores o bloqueos por delay()"*.

---

## 2. Los 5 Principios del Hardware Embebido

### Principio 1: Cero Bloqueos (Prohibido delay() en Producción)
- **Temporización con millis():** Uso estricto de deltas de tiempo para multitarea cooperativa (leer sensores a 10Hz, parpadear LEDs a 1Hz y atender comandos serie sin detener la CPU).
- **Máquinas de Estados Finitos (FSM):** Arquitectura por `enum State` y `switch(estado)` para navegación de robots (AVANZAR, GIRAR_IZQ, RETROCEDER, DETENERSE).
- **Interrupciones por Hardware (ISRs):** Uso de `attachInterrupt()` para encoders de motores, pulsadores y señales de emergencia con variables `volatile`.

### Principio 2: Electrónica Básica & Protección de Pines
- **Límite de Corriente:** Nunca alimentar motores directamente desde los pines del microcontrolador (máximo 20-40mA por pin). Uso obligatorio de drivers o transistores (MOSFETs / Puente H).
- **Cálculo de Resistencias (Ley de Ohm):**
  $$R = \frac{V_{fuente} - V_{componente}}{I_{deseada}}$$
- **Diodos Flyback (Protección Inductiva):** Diodo 1N4007 o Schottky en paralelo inverso con bobinas de relés y motores DC para suprimir picos de fuerza contraelectromotriz (Back-EMF).
- **Resistencias Pull-up / Pull-down:** Configuración de `pinMode(pin, INPUT_PULLUP)` interno para evitar estados flotantes en pulsadores.

### Principio 3: Control de Motores y Actuadores
- **Motores DC con Puente H (L298N, DRV8833, TB6612FNG):** Control de sentido de giro con pines lógicos y velocidad mediante PWM (`analogWrite()` o `ledcWrite()` en ESP32).
- **Servomotores (SG90, MG996R):** Control de ángulo por pulsos PWM de 50Hz (librería `Servo.h` o PWM hardware).
- **Motores Paso a Paso (NEMA 17 + A4988/TMC2209):** Control preciso por pasos y dirección con librerías como `AccelStepper`.

### Principio 4: Sensores y Buses de Comunicación
- **Digital / Analógico:** Lectura de sensores ultrasónicos (HC-SR04), infrarrojos (seguidor de línea TCRT5000), potenciómetros y LDRs.
- **Bus I2C (SDA / SCL):** Pantallas OLED 0.96" (SSD1306), sensores giroscopio/acelerómetro (MPU6050) y expansores de pines (PCF8574).
- **Bus SPI (MOSI / MISO / SCK / CS):** Lectores de tarjetas MicroSD y módulos RFID (RC522).
- **Comunicación Serie (UART):** Debug a 115200 baudios y comunicación entre microcontroladores.

### Principio 5: IoT & Conectividad Inalámbrica (ESP32)
- **Protocolo MQTT:** Publicación y suscripción ligera para dashboards (Home Assistant, Node-RED, Mosquitto).
- **ESP-NOW:** Comunicación ultra-rápida entre múltiples placas ESP32 punto a punto sin necesidad de router WiFi.
- **Servidor Web Embebido (AsyncWebServer):** Panel de control HTML/JS servido directamente desde la memoria flash (SPIFFS/LittleFS) para controlar el robot desde el móvil.
