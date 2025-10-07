# 🪴 ESP32-S2 WiFi Environmental Monitor

A MicroPython-based project for the ESP32-S2 that monitors **soil moisture** (using either an external sensor or the built-in touch pin) and **ambient temperature/humidity** (DHT22). It features a robust web configuration portal and real-time data publishing via MQTT.

## ✨ Features

* **Dual Moisture Sensor Support:** Configure the device to use either the:
    * **External Capacitive Sensor** (ADC on GPIO 9)
    * **Internal Capacitive Sensor** (Touch Pin on GPIO 13)
* **Auto-Inverting Calibration:** The moisture percentage calculation logic automatically handles sensors where **Wet readings are numerically higher or lower** than Dry readings, ensuring correct $0\% (\text{Dry})$ to $100\% (\text{Wet})$ mapping.
* **DHT22 Integration (Optional):** Enable/disable the DHT sensor via configuration.
* **Temperature Unit Selection:** Choose between displaying temperature in **Celsius (°C)** or **Fahrenheit (°F)**.
* **MQTT Integration:** Publishes all sensor data (moisture, Temp, Humidity) to a configurable MQTT broker.
* **Unique Device ID:** Uses a concise, **3-digit device ID** for easy identification.
* **Visual Status Indicator:** Uses a single WS2812B NeoPixel LED to display moisture status.
* **Brightness Control:** Adjust the NeoPixel's intensity ($0-255$).
* **Non-Blocking Configuration:** Update all settings on-the-fly via a web portal.

***

## 🛠️ Hardware Requirements & Wiring

| Component | ESP32-S2 GPIO | Notes |
| :--- | :--- | :--- |
| **Moisture Sensor (Aout)** | **GPIO 9** | Used for **External** Capacitive Sensor (ADC). |
| **Soil Probe** | **GPIO 13** | Used for **Internal** Capacitive Sensor (Touch Pin T5). |
| **DHT22/DHT11 (DATA)** | **GPIO 14** | Data pin for Temp/Humidity. |
| **WS2812B (DIN)** | **GPIO 10** | Data pin for the NeoPixel LED. |

**⚠️ Note on Power:** The **WS2812B LED MUST be powered by a 5V source** (if available), with its **GND connected to the ESP32's GND**.

***

## 💻 Software Setup (MicroPython)

### 1. Required Libraries

This project requires three external libraries:

* **`umqttsimple`**: The MQTT client library.
* **`dht`**: The driver library for the DHT sensor.

*Installation:* Upload **`umqttsimple.py`** and **`dht.py`** to the root directory of your board.

### 2. Upload Files

Upload the following core files to the root directory of your ESP32-S2:

* **`boot.py`**
* **`main.py`**
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
| **Sensor Type** | Radio Buttons | **Select** if you are using the **External Capacitive Sensor (ADC)** or the **Internal Capacitive Sensor (Touch)**. |
| **Calibration** | Dry/Wet Reading | **Required.** Raw sensor values when the sensor is in **air** (Dry) and **submerged** (Wet). The system will automatically map the lower/higher raw values to $0\%/100\%$. |
| **Peripheral** | DHT22 Sensor | **Optional Checkbox.** Enable/disable the DHT sensor. |
| **Peripheral** | Temp Unit | **Radio Button.** Select Celsius (°C) or Fahrenheit (°F). |
| **Peripheral** | Brightness | NeoPixel intensity value ($0-255$). |

Click **"Save Settings & Reboot"**. The device will now connect to your main Wi-Fi network and begin operating.