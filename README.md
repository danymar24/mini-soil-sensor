# 🪴 ESP32-S2 WiFi Environmental Monitor

A MicroPython-based project for the ESP32-S2 that reads data from a **capacitive soil moisture sensor** and an **ambient DHT22 temperature/humidity sensor**. It serves a real-time status page over Wi-Fi and supports MQTT for remote monitoring.

## ✨ Features

* **DHT22 Integration (Optional):** Supports reading temperature and humidity. Can be **enabled or disabled** via the configuration portal to accommodate different hardware builds.
* **Temperature Unit Selection:** Choose between displaying temperature in **Celsius (°C)** or **Fahrenheit (°F)** via the web configuration.
* **MQTT Integration:** Publishes all sensor data (moisture %, raw ADC, Temp, Humidity) to a configurable MQTT broker.
* **Unique Device ID:** Uses a concise, **3-digit device ID** for easy identification on the network, topics, and web interface.
* **Real-time Web Server:** View all environmental data and status on any browser on the local network.
* **On-the-fly Configuration:** Update **Wi-Fi, MQTT, calibration, brightness, and sensor options** directly via the web portal.
* **Visual Status Indicator:** Uses a single WS2812B NeoPixel LED to display moisture status:
    * **Green:** Moist/Wet (Moisture $\ge 50\%$)
    * **Orange:** Ideal (Moisture $20\% \text{ to } 49\%$)
    * **Red:** Very Dry (Moisture $< 20\%$)
* **Brightness Control:** Adjust the NeoPixel's intensity ($0-255$) via the configuration portal.

***

## 🛠️ Hardware Requirements & Wiring

| Component | ESP32-S2 GPIO | Notes |
| :--- | :--- | :--- |
| **Moisture Sensor (Aout)** | **GPIO 9** | Analog input. |
| **DHT22/DHT11 (DATA)** | **GPIO 14** | Data pin for Temp/Humidity. |
| **WS2812B (DIN)** | **GPIO 10** | Data pin for the NeoPixel LED. |

**⚠️ Note on Power:** The capacitive sensor and ESP32-S2 can be powered by 3.3V. The **WS2812B LED MUST be powered by a 5V source** (if available), with its **GND connected to the ESP32's GND**.

***

## 💻 Software Setup (MicroPython)

### 1. Required Libraries

This project requires two non-standard libraries:

* **`umqttsimple`**: The MQTT client library.
* **`dht`**: The driver library for the DHT sensor.

*Installation:* Upload both **`umqttsimple.py`** and **`dht.py`** to the root directory of your board.

### 2. Upload Files

Upload the following core files to the root directory of your ESP32-S2:

* **`boot.py`**: Handles Wi-Fi connection and loads initial configuration.
* **`main.py`**: Contains all sensor reading, web server, and application logic.
* **`umqttsimple.py`**
* **`dht.py`**

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

| Section | Field | Notes |
| :--- | :--- | :--- |
| **Calibration** | Dry/Wet Reading | **Required.** Raw ADC values in air/water for $0\%$ and $100\%$ moisture. |
| **MQTT** | Broker Address/Port | Broker URL or IP address. |
| **Peripheral** | DHT22 Sensor | **Optional Checkbox.** Enable/disable the DHT sensor. |
| **Peripheral** | Brightness | NeoPixel intensity value ($0-255$). |
| **Peripheral** | Temp Unit | **Radio Button.** Select Celsius (°C) or Fahrenheit (°F). |

Click **"Save Settings & Reboot"**. The device will now connect to your main Wi-Fi network and begin operating.