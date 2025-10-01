import network
import time
import json
import machine

# --- LED Configuration ---
# GPIO 15 is the common onboard LED for ESP32-S2, usually active-low.
LED_PIN = 15 
led = machine.Pin(LED_PIN, machine.Pin.OUT)

# Function to safely turn the LED ON (set to 0 for active-low)
def led_on():
    led.value(0)

# Function to safely turn the LED OFF (set to 1 for active-low)
def led_off():
    led.value(1)

# Default Configuration
DEVICE_HOSTNAME = "ESP32-Moisture-Sensor"
DEFAULT_SSID = "Moisture_Config_AP"
DEFAULT_PASSWORD = "configpass123" 
CONFIG_FILE = "config.json"

def connect_to_wifi(ssid, password):
    """Attempts to connect to a given SSID."""
    sta_if = network.WLAN(network.STA_IF)
    sta_if.active(True)
    sta_if.config(hostname=DEVICE_HOSTNAME) 
    
    if sta_if.isconnected():
        print("Already connected.")
        led_on() # LED ON if already connected
        return True

    print(f"Connecting to '{ssid}'...", end="")
    sta_if.connect(ssid, password)
    
    timeout = 15
    while not sta_if.isconnected() and timeout > 0:
        print(".", end="")
        time.sleep(1)
        timeout -= 1

    if sta_if.isconnected():
        ip_address = sta_if.ifconfig()[0]
        print(f"\nConnected! IP Address: {ip_address}")
        led_on() # <<< LED ON when successful connection is made
        return True
    else:
        print("\nFailed to connect.")
        sta_if.active(False) 
        led_off() # <<< LED OFF when connection fails
        return False

def start_config_portal():
    """Starts a Configuration Access Point (AP)."""
    # In config mode, the AP is technically active, so let's use a subtle feedback, like blinking
    # However, to keep it simple and aligned with the "off if disconnected" request:
    led_off() 
    
    print("Starting Configuration Portal...")
    ap_if = network.WLAN(network.AP_IF)
    ap_if.active(True)
    ap_if.config(essid=DEFAULT_SSID, password=DEFAULT_PASSWORD, hostname=DEVICE_HOSTNAME)
    
    ip_address = ap_if.ifconfig()[0]
    print(f"Connect to AP: {DEFAULT_SSID}")
    print(f"Then visit: http://{ip_address}/")
    return ap_if

# --- Main Boot Logic ---

# Ensure LED is OFF initially while loading config
led_off()

# 1. Load config from file
try:
    with open(CONFIG_FILE, 'r') as f:
        config = json.load(f)
        wifi_ssid = config['ssid']
        wifi_password = config['password']
except:
    # No config file found or invalid JSON, use placeholder
    print("No valid config found.")
    wifi_ssid = None
    wifi_password = None

# 2. Attempt connection
if wifi_ssid and wifi_password:
    if not connect_to_wifi(wifi_ssid, wifi_password):
        time.sleep(2) 
        start_config_portal()
else:
    start_config_portal()

# Note: The network interface is left active for main.py to use.