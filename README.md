# 🪴 ESP32-S2 WiFi Soil Moisture Monitor

A MicroPython-based project for the ESP32-S2 that reads data from a capacitive soil moisture sensor (HW-390) and serves a real-time status page over Wi-Fi. It includes a built-in configuration portal and NeoPixel (WS2812B) visual status indicator.

## ✨ Features

* **Real-time Web Server:** View moisture percentage and raw ADC readings on any browser on the local network.
* **Zero-Code Wi-Fi Setup:** Automatically enters a **Configuration Portal (Access Point)** mode if it cannot connect to the saved Wi-Fi.
* **On-the-fly Calibration:** Update sensor dry/wet calibration values directly via the web configuration page.
* **Visual Status Indicator:** Uses a single WS2812B NeoPixel LED to display moisture status:
    * **Green:** Moist/Wet (Moisture $\ge 50\%$)
    * **Orange:** Ideal (Moisture $20\% \text{ to } 49\%$)
    * **Red:** Very Dry (Moisture $< 20\%$)
* **Stable Operation:** Utilizes non-blocking socket handling to maintain responsiveness and avoid serial port freezes.

## 🛠️ Hardware Requirements

| Component | Description |
| :--- | :--- |
| **Microcontroller** | ESP32-S2 Development Board |
| **Sensor** | Capacitive Soil Moisture Sensor (HW-390) |
| **Status LED** | Single WS2812B NeoPixel LED |
| **Power** | 5V external power source for NeoPixel (recommended) |

---

## 🔌 Wiring Diagram

| Component Pin | ESP32-S2 GPIO | Notes |
| :--- | :--- | :--- |
| **HW-390 (VCC)** | **3.3V** | Power the sensor. |
| **HW-390 (GND)** | **GND** | Common ground. |
| **HW-390 (Aout)** | **GPIO 9** | Analog input (ADC1, Wi-Fi safe). |
| **NeoPixel (DIN)** | **GPIO 10** | Data pin for the WS2812B LED. |
| **NeoPixel (GND)** | **GND** | Common ground. |
| **NeoPixel (VCC)** | **5V Source** | **CRITICAL: Use a dedicated 5V source.** |
| **Onboard LED** | **GPIO 13** | (Status LED is controlled by `boot.py`) |

---

## 💻 Software Setup (MicroPython)

### 1. Install MicroPython

Ensure your ESP32-S2 is flashed with the latest stable version of **MicroPython for ESP32-S2**.

### 2. Required Libraries

This project uses the built-in MicroPython libraries (`machine`, `network`, `socket`, `time`, `json`) and one third-party library:

* **`neopixel`**: The library for controlling the WS2812B LED.
    * *Installation:* This library is typically built-in to recent firmwares. If it's missing, you will need to install the official MicroPython `neopixel.py` file to your board's root directory.

### 3. Upload Files

Upload the following files to the root directory of your ESP32-S2:

* **`boot.py`**: Handles Wi-Fi connection logic, AP fall-back, and LED status.
* **`main.py`**: Contains sensor reading, web server logic, configuration handling, and NeoPixel control.

---

## 🚀 First-Time Setup & Usage

### 1. Enter Configuration Mode

The device will automatically enter **Configuration Mode** if it cannot find the `config.json` file or connect to the Wi-Fi.

* **Initial Setup:** Hard reset the board. It will fail to connect and start the AP.
* **Connect:** Connect your phone or PC to the Wi-Fi Access Point:
    * **SSID:** `Moisture_Config_AP`
    * **Password:** `configpass123`
* **Access Portal:** Navigate to `http://192.168.4.1/` in your browser.

### 2. Set Wi-Fi and Calibration

On the configuration page, you will see fields for Wi-Fi and calibration:

1.  **WiFi:** Enter your home/office Wi-Fi SSID and Password. *(Note: You can leave these blank later to only update calibration.)*
2.  **Calibration:** Perform initial calibration:
    * **Dry Reading (0%):** Place the sensor in **air** and record the raw value (e.g., `8191`).
    * **Wet Reading (100%):** Submerge the sensor in **water** and record the raw value (e.g., `4300`).
3.  Click **"Save Settings & Reboot"**.

### 3. Monitor Status

* **Device Status:** The onboard LED on GPIO 13 will turn **ON** (solid) once connected to the main Wi-Fi network.
* **Access Data Page:** After rebooting, find the device's IP address (check your router's client list for `ESP32-Moisture-Sensor`). Navigate to that IP address in your browser to view live data.
* **Change Calibration:** Click the **"Change WiFi"** link on the data page to update calibration values without needing to disconnect from your network.

---

## ⚙️ Configuration Variables

You can adjust these values at the top of the **`main.py`** file if necessary:

| Variable | File | Description |
| :--- | :--- | :--- |
| `SENSOR_PIN` | `main.py` | GPIO pin used for the HW-390 analog output (default: `9`). |
| `NEOPIXEL_PIN` | `main.py` | GPIO pin used for the NeoPixel data line (default: `10`). |
| `READING_DELAY_MS` | `main.py` | Delay between sensor readings (default: `5000` ms). |
| `COLOR_DRY`, etc. | `main.py` | RGB tuples for visual moisture status. |

# This project was created using AI as support