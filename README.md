# 🌊 Flood Monitoring Dashboard System

A vehicle-mounted IoT system that provides real-time flood monitoring with water depth, turbidity detection, GPS tracking, and a live web-based dashboard. Built as a Final Year Project at **Universiti Kuala Lumpur (UniKL), 2026**.

> **Author:** Muhammad Irfan Bin Mohd Fardaus  
> **Supervisor:** Dr. Mohd Zaki Bin Ayob  
> **Programme:** Bachelor of Electronic Engineering Technology with Honours

> **Related Repository:** [Web Dashboard](https://github.com/IrfanFardaus/Flood-Monitoring-Dashboard-web)

---

## 📌 Overview

Traditional flood monitoring relies on fixed sensors at riverbanks and tunnels, leaving urban and residential areas unmonitored. This project transforms everyday vehicles into **mobile flood sensing nodes** by mounting sensors directly on the vehicle chassis and side mirrors.

The system captures real-time flood depth, water turbidity, and GPS coordinates, transmits the data to Google Firebase Firestore, and visualises everything on a responsive web dashboard with live map markers.

**PCB layout and Schematic:** [Here](https://github.com/IrfanFardaus/Flood-Monitoring-Dashboard-system/blob/main/fyp_flood.pdf)

---

## ✨ Features

- 📏 **Dual ultrasonic flood depth sensing** — left & right sensors for accuracy and fault detection
- 💧 **Water turbidity classification** — Clean / Dirty / Muddy states
- 📍 **Real-time GPS tracking** — precise flood hazard location
- 🔴🟡🟢 **Local LED severity indicators** — Safe, Warning, and Danger
- 🖥️ **OLED local display** — shows depth, turbidity, alert status, and GPS state
- ☁️ **Firebase Firestore cloud upload** — ~2 second average latency
- 🗺️ **Live web dashboard** — Leaflet.js map with colour-coded flood markers
- 🔔 **Toast notifications & alert list** — real-time browser alerts
- 📊 **Analytics section** — historical data and charts
- 🔧 **On-device calibration** — height setting via push buttons, saved to flash

---

## 🔧 Hardware Components

| Component | Description |
|---|---|
| **ESP32** | Dual-core MCU with built-in Wi-Fi |
| **JSN-SR04T (×2)** | Waterproof ultrasonic sensors (left & right) |
| **TS-300B** | Turbidity sensor for water clarity |
| **NEO-6M** | GPS module for real-time positioning |
| **SH1106 OLED (1.3")** | Local display for sensor readouts |
| **3× LEDs** | Green (Safe), Orange (Warning), Red (Danger) |
| **3× Push Buttons** | Height calibration and settings control |
| **Custom PCB** | Compact board with pin headers and connectors |
| **Solar Panel + TP4056** | Solar charging for field deployment |
| **3.7V LiPo Battery** | Backup power with overcharge protection |

---

## 📡 System Architecture

```
┌─────────────────────────────────────────────────────┐
│                      INPUT                          │
│  Ultrasonic (L/R) │ Turbidity │ GPS │ Push Buttons  │
└────────────────────────┬────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────┐
│                     PROCESS                         │
│              ESP32 Microcontroller                  │
│  • Calculate flood depth                            │
│  • Classify turbidity                               │
│  • Determine severity (SAFE / WARNING / DANGER)     │
│  • Parse GPS NMEA data                              │
└────────────────────────┬────────────────────────────┘
                         │
          ┌──────────────┼──────────────┐
          ▼              ▼              ▼
    LED Indicators  OLED Display  Firebase Firestore
    (local alert)  (local display)       │
                                         ▼
                               Web Dashboard (Cloudflare)
                               Leaflet.js Map + Alerts
```

---

## 🚦 Severity Thresholds

| Severity | Flood Depth | LED | Duration Requirement |
|---|---|---|---|
| ✅ **SAFE** | < 15 cm | 🟢 Green | Immediate |
| ⚠️ **WARNING** | 15 – 39 cm | 🟡 Orange | Sustained ≥ 3 minutes |
| 🚨 **DANGER** | ≥ 40 cm | 🔴 Red | Sustained ≥ 3 minutes |
| ❌ **INVALID** | Sensor mismatch > 10 cm | Off | — |

## 💧 Turbidity Classification

| Status | Turbidity Percentage |
|---|---|
| Clean | < 2% |
| Dirty | 2% – 50% |
| Muddy | > 50% |

---

## 📁 Repository Structure

```
Flood-Monitoring-Dashboard-system/
├── main.py           # Main ESP32 firmware — sensor loop, severity logic, Firestore upload
├── boot.py           # Boot configuration
├── ajsr04m.py        # Driver for JSN-SR04T waterproof ultrasonic sensor
├── micropyGPS.py     # NMEA GPS parsing library (MicropyGPS)
├── sh1106.py         # SH1106 OLED display driver
├── pymakr.conf       # Pymakr extension configuration for VS Code
└── fyp.code-workspace # VS Code workspace settings
```

---

## ⚡ ESP32 Pin Configuration

| Component | Pin(s) |
|---|---|
| LED Green | GPIO 4 |
| LED Yellow (Orange) | GPIO 13 |
| LED Red | GPIO 14 |
| Button 1 (+) | GPIO 33 |
| Button 2 (−) | GPIO 27 |
| Button 3 (Save) | GPIO 26 |
| Ultrasonic Sensor 1 (Left) | Trigger: GPIO 5, Echo: GPIO 18 |
| Ultrasonic Sensor 2 (Right) | Trigger: GPIO 19, Echo: GPIO 23 |
| Turbidity Sensor | GPIO 34 (ADC) |
| GPS Module UART | TX: GPIO 17, RX: GPIO 16 |
| OLED I2C | SCL: GPIO 22, SDA: GPIO 21 |

---

## 🛠️ Getting Started

### Prerequisites

- ESP32 development board
- [VS Code](https://code.visualstudio.com/) with [Pymakr](https://marketplace.visualstudio.com/items?itemName=pycom.Pymakr) extension
- MicroPython firmware flashed on ESP32
- Google Firebase project with Cloud Firestore enabled

### 1. Flash MicroPython to ESP32

Download the latest MicroPython firmware from [micropython.org](https://micropython.org/download/esp32/) and flash it:

```bash
esptool.py --chip esp32 erase_flash
esptool.py --chip esp32 write_flash -z 0x1000 esp32-firmware.bin
```

### 2. Clone the Repository

```bash
git clone https://github.com/IrfanFardaus/Flood-Monitoring-Dashboard-system.git
cd Flood-Monitoring-Dashboard-system
```

### 3. Configure Wi-Fi and Firebase

Open `main.py` and update the following constants:

```python
WIFI_SSID = 'Your_WiFi_Name'
WIFI_PASS = 'Your_WiFi_Password'
DEVICE_ID = "SENSOR_001"   # Unique ID for this unit
sensor_height = 100        # Height from sensor to ground in cm

PROJECT_ID = 'your-firebase-project-id'
API_KEY    = 'your-firebase-api-key'
```

### 4. Upload to ESP32

Open the project in VS Code and use the **Pymakr** extension to upload all `.py` files to the ESP32. The device will run `boot.py` then `main.py` automatically on startup.

### 5. Sensor Height Calibration

Use the on-device buttons to set the correct sensor mount height:

- **Button 1 (+)** — increase height by 1 cm
- **Button 2 (−)** — decrease height by 1 cm  
- **Button 3 (Save)** — save to flash memory

---

## ☁️ Cloud & Dashboard Setup

### Firebase Firestore

1. Create a project at [Firebase Console](https://console.firebase.google.com/)
2. Enable **Cloud Firestore** in Native mode
3. Copy your `Project ID` and `API Key` into `main.py`
4. The firmware writes to a `sensor_history` collection with the following document schema:

```json
{
  "device_id":           "SENSOR_001",
  "depth_cm":            12.5,
  "turbidity_percent":   1.3,
  "turbidity_status":    "Clean",
  "severity":            "SAFE",
  "timestamp":           1750000000000,
  "latitude":            3.2653822,
  "longitude":           101.72639
}
```

### Web Dashboard (Cloudflare Pages)

The frontend is built with plain HTML, CSS, and JavaScript using **Leaflet.js** for the live flood map. It is deployed via [Cloudflare Pages](https://pages.cloudflare.com/) for global CDN delivery.

Dashboard sections:
- 🗺️ **Main Map** — live colour-coded flood markers from GPS data
- 🔔 **Toast Notifications** — real-time severity alerts
- 📋 **Alert List & Detail** — history of all triggered alerts
- 📊 **Analytics** — historical trends and sensor data
- 📟 **Device Management** — registered sensor unit overview

---

## 📊 System Performance

| Metric | Result |
|---|---|
| Ultrasonic sensor accuracy | < 2% error |
| GPS positioning accuracy | Within 1 metre |
| Cloud transmission latency | ~2 seconds average |
| Data upload interval | Every 5 seconds |
| Turbidity reading variance | < 5% |

---

## ⚙️ Software & Libraries

| Tool / Library | Purpose |
|---|---|
| **MicroPython** | Firmware language for ESP32 |
| **micropyGPS** | NMEA GPS sentence parser |
| **urequests** | HTTP client for Firestore REST API |
| **ntptime** | NTP time synchronisation |
| **Google Firebase Firestore** | Real-time NoSQL cloud database |
| **Leaflet.js** | Interactive web map rendering |
| **Cloudflare Pages** | Static site hosting and CDN |
| **VS Code + Pymakr** | IDE and firmware upload tool |

---

## ⚠️ Known Limitations

- Requires an active Wi-Fi connection for cloud upload; data may be delayed if signal is weak
- GPS accuracy may vary by a few metres in dense urban areas
- Ultrasonic sensors can produce false readings from splashes, road dividers, or sensor tilt
- Turbidity sensor optical lens may require periodic cleaning in heavy silt conditions
- System currently does not support flood forecasting or AI-based prediction

---

## 🔮 Future Work

- Integrate LTE/4G module for areas without Wi-Fi coverage
- Add offline data buffering with retry-on-reconnect logic
- Apply machine learning for flood prediction and trend analysis
- Expand multi-vehicle fleet tracking on a single dashboard
- Add mobile push notifications via Firebase Cloud Messaging

---

## 📜 License

This project was developed for academic purposes at **Universiti Kuala Lumpur (UniKL), British Malaysian Institute**. All rights reserved by the author.

---

## 🙏 Acknowledgements

Special thanks to **Dr. Mohd Zaki Bin Ayob** for supervision and guidance, and to Universiti Kuala Lumpur for supporting this research.
