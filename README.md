# 🪴 ESP32-S2 WiFi Soil Moisture Monitor

A MicroPython-based project for the ESP32-S2 that reads data from a capacitive soil moisture sensor (HW-390) and serves a real-time status page over Wi-Fi. It includes a robust configuration portal, an MQTT client for remote monitoring, and a NeoPixel (WS2812B) visual status indicator.

## ✨ Features

* **MQTT Integration:** Publishes sensor data (moisture %, raw ADC) to a configurable MQTT broker using a structured topic hierarchy.
* **Unique Device ID:** Uses a concise, 3-digit device ID for easy identification on the network, topics, and web interface.
* **Real-time Web Server:** View moisture percentage and raw ADC readings on any browser on the local network.
* **Zero-Code Wi-Fi Setup:** Automatically enters a **Configuration Portal (Access Point)** mode if it cannot connect to the saved Wi-Fi.
* **On-the-fly Configuration:** Update Wi-Fi, MQTT broker details, and sensor calibration values directly via the web configuration page while the device is running.
* **Visual Status Indicator:** Uses a single WS2812B NeoPixel LED to display moisture status:
    * **Green:** Moist/Wet (Moisture $\ge 50\%$)
    * **Orange:** Ideal (Moisture $20\% \text{ to } 49\%$)
    * **Red:** Very Dry (Moisture $< 20\%$)

***

## 🛠️ Hardware Requirements & Wiring

| Component | ESP32-S2 GPIO | Notes |
| :--- | :--- | :--- |
| **HW-390 (Aout)** | **GPIO 9** | Analog input. |
| **WS2812B (DIN)** | **GPIO 10** | Data pin for the NeoPixel LED. |
| **Onboard LED** | **GPIO 13** | (Controlled by `boot.py` for connection status) |

**⚠️ Note on Power:** The capacitive sensor and ESP32-S2 can be powered by 3.3V. However, the **WS2812B LED MUST be powered by a 5V source**, with its **GND connected to the ESP32's GND**.

***

## 💻 Software Setup (MicroPython)

### 1. Required Libraries

This project uses standard MicroPython libraries and the following third-party library:

* **`umqttsimple`**: The MQTT client library.
    * *Installation:* Upload the **`umqttsimple.py`** file to the root directory of your board.
* **`neopixel`**: The library for controlling the WS2812B LED.
    * *Installation:* This is often built-in. If not, install the official MicroPython **`neopixel.py`** file.

### 2. Upload Files

Upload the following files to the root directory of your ESP32-S2:

* **`boot.py`**: Handles Wi-Fi connection and loads initial configuration.
* **`main.py`**: Contains sensor reading, web server logic, configuration handling, MQTT client, and NeoPixel control.
* **`umqttsimple.py`** (if required)

### 3. MQTT Topic Structure

The device publishes data and subscribes to commands using the following hierarchy, where **`###`** is the unique 3-digit device ID:

| Direction | Topic | Purpose |
| :--- | :--- | :--- |
| **Publish** | `sensors/moisture/esp32-###/data` | Real-time sensor readings (JSON payload). |
| **Subscribe** | `sensors/moisture/esp32-###/cmd` | Listens for commands (e.g., `reboot`). |

***

## 🚀 First-Time Setup & Configuration

### 1. Enter Configuration Mode

The device enters **Configuration Mode (Access Point)** if it cannot connect to the saved Wi-Fi (e.g., first boot).

* **Connect:** Connect your phone or PC to the Wi-Fi Access Point:
    * **SSID:** `Moisture_Config_AP`
    * **Password:** `configpass123`
* **Access Portal:** Navigate to `http://192.168.4.1/` in your browser.

### 2. Configure Settings

On the configuration page, you must set the following:

1.  **WiFi Credentials:** Enter the SSID and Password for your main network. (Can be left blank later to only update other settings).
2.  **Calibration Values:**
    * **Dry Reading (0% Moisture):** Raw ADC value when the sensor is in **air**.
    * **Wet Reading (100% Moisture):** Raw ADC value when the sensor is submerged in **water**.
3.  **MQTT Broker Settings:**
    * **Broker Address & Port:** The address and port for your Mosquitto, HiveMQ, or cloud broker.
    * **Username/Password:** Required if your broker uses authentication.

Click **"Save Settings & Reboot"**.

### 3. Monitor Status

* **Device IP:** After rebooting and connecting to your network, find the device's IP address and navigate to it to view the live data page.
* **MQTT Data:** Subscribe to the topic `sensors/moisture/MQTT_CLIENT_ID/data` on your broker to see the JSON payload from the device.