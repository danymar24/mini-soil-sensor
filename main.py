import machine
import time
import socket
import network
import json
import boot
import neopixel
import ubinascii 
import dht
from umqtt.simple import MQTTClient

# --- Global Sensor Data ---
current_raw_reading = 0
current_moisture_percent = 0.0

# --- Sensor Configuration ---
SENSOR_PIN = 9          
# GLOBAL CALIBRATION VALUES (use the ones loaded by boot.py)
CALIBRATION_DRY = boot.CALIBRATION_DRY
CALIBRATION_WET = boot.CALIBRATION_WET
READING_DELAY_MS = 5000 

# --- Web Server Configuration ---
WEB_PORT = 80
RESPONSE_HEADER_OK = 'HTTP/1.0 200 OK\r\nContent-type: text/html\r\n\r\n'
RESPONSE_HEADER_REDIRECT = 'HTTP/1.0 302 Found\r\nLocation: /\r\n\r\n'
CONFIG_FILE = "config.json"

# --- WS2812B Configuration ---
NEOPIXEL_PIN = 10  # Use GPIO 10 for the NeoPixel data line
NEOPIXEL_COUNT = 1 # We are using only one LED

# --- Color Definitions (RGB Tuples) ---
COLOR_DRY = (255, 0, 0)     # Red (Very Dry)
COLOR_IDEAL = (255, 165, 0) # Orange (Ideal)
COLOR_WET = (0, 255, 0)     # Green (Wet/Moist)
BRIGHTNESS_LEVEL = boot.BRIGHTNESS_LEVEL  # Global brightness level (0-255)

# --- MQTT Setup ---
# Set the Client ID to be unique using the device's MAC address
unique_bytes = machine.unique_id()[-3:]
unique_int = int.from_bytes(unique_bytes, 'big')
SHORT_DEVICE_ID = "{:03d}".format(unique_int % 1000)
MQTT_CLIENT_ID = f'esp32-{SHORT_DEVICE_ID}'
MQTT_BROKER = boot.MQTT_BROKER
MQTT_PORT = boot.MQTT_PORT
MQTT_USER = boot.MQTT_USER
MQTT_PASSWORD = boot.MQTT_PASSWORD

# --- DHT22 Configuration ---
DHT_PIN = 14 
DHT_ENABLED = False
TEMP_UNIT_C = True
current_temp_c = 0.0
current_humidity = 0.0

d = None

# Define Topics (using the unique ID for organization)
TOPIC_PUB = f'sensors/moisture/{MQTT_CLIENT_ID}/data'.encode('utf-8')
TOPIC_SUB_COMMAND = f'sensors/moisture/{MQTT_CLIENT_ID}/cmd'.encode('utf-8')

mqtt_client = None # Global variable for the MQTT client object

# Initialize the NeoPixel object
try:
    np = neopixel.NeoPixel(machine.Pin(NEOPIXEL_PIN), NEOPIXEL_COUNT)
except Exception as e:
    print(f"NeoPixel initialization failed: {e}")
    np = None

# --- ADC Initialization ---
try:
    # Use 13-bit for the ESP32-S2 if 12 is rejected, based on previous errors.
    # Note: If this line causes an error, try adc.width(14) or remove it completely
    # and let it use the firmware's default (which seems to be 13-bit).
    adc = machine.ADC(machine.Pin(SENSOR_PIN))
    adc.width(13) 
    adc.atten(machine.ADC.ATTN_11DB) 
except Exception as e:
    print(f"ADC init error: {e}. Sensor reading disabled.")
    adc = None # Disable sensor reading if init fails
    
def initialize_dht():
    """Initializes the DHT sensor only if the flag is enabled."""
    global d
    if DHT_ENABLED:
        try:
            import dht
            d = dht.DHT22(machine.Pin(DHT_PIN))
            print("DHT sensor initialized and enabled.")
        except Exception as e:
            print(f"ERROR: DHT sensor initialization failed: {e}. Disabling DHT.")
            d = None
    else:
        print("DHT sensor is disabled via configuration.")

initialize_dht()

# --- Sensor Functions ---
def read_moisture():
    """Reads the raw ADC value and converts it to a moisture percentage."""
    global current_raw_reading, current_moisture_percent
    if not adc:
        current_raw_reading = 0
        current_moisture_percent = 0.0
        return
        
    num_samples = 10
    raw_value = 0
    for _ in range(num_samples):
        raw_value += adc.read()
        time.sleep_ms(5)
        
    raw_value = raw_value // num_samples
    
    # --- Conversion Logic ---
    constrained_value = max(CALIBRATION_WET, min(CALIBRATION_DRY, raw_value))
    moisture_range = CALIBRATION_DRY - CALIBRATION_WET
    moisture_value = constrained_value - CALIBRATION_WET
    moisture_percentage = (moisture_range - moisture_value) / moisture_range * 100
    
    # UPDATE GLOBAL VARIABLES
    current_raw_reading = raw_value
    current_moisture_percent = round(moisture_percentage, 1)

    set_neopixel_color(current_moisture_percent)

# --- NeoPixel Functions ---
def set_neopixel_color(moisture_percent):
    """Sets the NeoPixel color based on moisture percentage and global brightness."""
    if np is None:
        return

    if moisture_percent < 20:
        base_color = COLOR_DRY 
    elif moisture_percent < 50:
        base_color = COLOR_IDEAL 
    else:
        base_color = COLOR_WET 

    # Scale each R, G, B component by the BRIGHTNESS_LEVEL / 255.0
    scale_factor = BRIGHTNESS_LEVEL / 255.0
    
    r = int(base_color[0] * scale_factor)
    g = int(base_color[1] * scale_factor)
    b = int(base_color[2] * scale_factor)
    
    scaled_color = (r, g, b)

    try:
        np[0] = scaled_color
        np.write()
    except Exception as e:
        print(f"Error writing to NeoPixel: {e}")

def read_dht():
    """Reads temperature and humidity from the DHT22 sensor."""
    global current_temp_c, current_humidity

    if not DHT_ENABLED or d is None:
        current_temp_c = 0.0 
        current_humidity = 0.0
        return
        
    try:
        # Measure must be called before accessing temperature() or humidity()
        d.measure() 
        current_temp_c = round(d.temperature(), 1)
        current_humidity = round(d.humidity(), 1)
        print(f"DHT Read: Temp={current_temp_c}°C, Humidity={current_humidity}%")
    except OSError as e:
        # Common error when reading fails (e.g., timing issue)
        print(f"ERROR: Failed to read DHT sensor: {e}")
        # Optionally, set values to 0.0 or last known good value
        current_temp_c = 0.0 
        current_humidity = 0.0

# --- Configuration Portal Functions ---

def url_decode(s):
    """Simple URL decoder for MicroPython."""
    i = 0
    res = ''
    while i < len(s):
        if s[i] == '%':
            if i + 2 < len(s):
                # Decode %xx to the actual character
                try:
                    res += chr(int(s[i+1:i+3], 16))
                    i += 3
                except ValueError:
                    # Fallback if decoding fails
                    res += s[i]
                    i += 1
            else:
                res += s[i]
                i += 1
        elif s[i] == '+':
            res += ' '  # Replace '+' with space
            i += 1
        else:
            res += s[i]
            i += 1
    return res

def save_config(ssid, password, dry_value, wet_value, broker, port, user, mqtt_pass, brightness, dht_enabled, temp_unit_c):
    """Saves new credentials AND calibration to config.json and resets."""
    config = {
        'ssid': ssid, 
        'password': password,
        # Save calibration values
        'dry': dry_value,
        'wet': wet_value,
        # save MQTT values
        'mqtt_broker': broker,
        'mqtt_port': port,
        'mqtt_user': user,
        'mqtt_pass': mqtt_pass,
        'brightness': brightness,
        'dht_enabled': dht_enabled,
        'temp_unit_c': temp_unit_c 
    }
    
    import os
        
    try:
        # 1. Attempt to write the file
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f)
            
        # 2. Force the data to be written to flash
        os.sync() 
            
        print("SUCCESS: Configuration saved to flash.")
        # Print the contents to verify immediately on the serial console
        print(f"Saved Config: {config}") 
        
        # 3. Delay for a minimal amount of time to allow final serial output
        time.sleep_ms(50) 
        
        # 4. Reset the machine to apply changes
        machine.reset()
        
    except Exception as e:
        # CRITICAL: Print any exception that occurs during file I/O
        print(f"FATAL ERROR: Failed to save config or reset: {e}")

def load_current_wifi_config():
    """Utility to load current working Wi-Fi credentials."""
    try:
        with open(CONFIG_FILE, 'r') as f:
            config = json.load(f)
            return config.get('ssid'), config.get('password')
    except:
        return None, None
    
def load_current_config_details():
    """Utility to load current working MQTT credentials."""
    try:
        with open(CONFIG_FILE, 'r') as f:
            config = json.load(f)
            return (
                config.get('mqtt_broker', MQTT_BROKER),
                config.get('mqtt_port', MQTT_PORT),
                config.get('mqtt_user', MQTT_USER),
                config.get('mqtt_pass', MQTT_PASSWORD),
                config.get('brightness', BRIGHTNESS_LEVEL),
                config.get('dht_enabled', DHT_ENABLED),
                config.get('temp_unit_c', TEMP_UNIT_C)

            )
    except:
        # Return global defaults if file doesn't exist or is invalid
        return (MQTT_BROKER, MQTT_PORT, MQTT_USER, MQTT_PASSWORD, BRIGHTNESS_LEVEL, DHT_ENABLED, TEMP_UNIT_C)
    
def sub_callback(topic, msg):
    """Handles incoming MQTT messages (e.g., commands)."""
    print(f"MQTT Received Topic: {topic.decode()}")
    print(f"MQTT Received Message: {msg.decode()}")
    
    # Example: If another device sends a command to reboot this device
    if topic == TOPIC_SUB_COMMAND and msg.decode() == "reboot":
        print("Received reboot command. Resetting...")
        machine.reset()
        
    # Add more logic here to handle incoming configuration updates if desired.

def mqtt_connect():
    """Connects to the MQTT broker."""
    global mqtt_client
    # Skip connection if configuration is incomplete
    if not boot.MQTT_BROKER or boot.MQTT_BROKER == "":
        print("MQTT Broker not configured. Skipping connection.")
        return None
        
    try:
        # Check if client needs user/pass
        user = boot.MQTT_USER if boot.MQTT_USER else None
        password = boot.MQTT_PASSWORD if boot.MQTT_PASSWORD else None
        
        mqtt_client = MQTTClient(
            client_id=MQTT_CLIENT_ID, 
            server=boot.MQTT_BROKER, 
            port=boot.MQTT_PORT, 
            user=user, 
            password=password,
            keepalive=60 
        )
        mqtt_client.set_callback(sub_callback) 
        mqtt_client.connect()
        mqtt_client.subscribe(TOPIC_SUB_COMMAND)
        print(f"MQTT Connected to {boot.MQTT_BROKER}. Subscribed to {TOPIC_SUB_COMMAND.decode()}")
        return mqtt_client
    except Exception as e:
        print(f"ERROR: Failed to connect to MQTT broker: {e}")
        return None

def mqtt_publish(payload):
    """Attempts to publish data, reconnecting/checking messages if necessary."""
    global mqtt_client
    print(f"Publishing MQTT data... {payload}")
    if mqtt_client is None:
        mqtt_client = mqtt_connect()
        if mqtt_client is None:
            return 
            
    try:
        # Check for incoming messages before publishing (essential for subscription logic)
        mqtt_client.check_msg() 
        mqtt_client.publish(TOPIC_PUB, payload.encode('utf-8'), retain=False, qos=0)
        
    except OSError as e:
        # Broker disconnected (commonly error code 104 or 113)
        if e.args[0] in (104, 113): 
            print(f"MQTT Disconnected ({e}). Reconnecting...")
            mqtt_client = None
            time.sleep_ms(100)
        else:
            print(f"MQTT Publish/Check Error: {e}")

def handle_config_submission(request):
    print(request)
    """Parses form data from the request, including calibration and MQTT fields."""
    
    # Check for the submission signature: GET request containing parameters AND the required 'dry='
    if 'GET /?' in request and 'dry=' in request: 
        
        # FIX: Ensure robust extraction of the query string regardless of path
        try:
            # Find the index of '?'
            q_start = request.find('?')
            # Find the index of the space after the path/query string
            q_end = request.find(' ', q_start)
            
            # Extract the raw query string part (e.g., ssid=&pass=...)
            query_string = request[q_start + 1: q_end] 
            
            params = query_string.split('&')
        except Exception as e:
            print(f"ERROR: Failed to extract query string: {e}")
            return False # Fail gracefully
            
        # Add your parameter printing back here to confirm data is being seen
        print(f"*** Query String Being Parsed: {query_string} ***")
        
        # New variable storage
        new_ssid, new_password = None, None
        dry_val, wet_val = None, None
        broker, port, user, mqtt_pass = None, None, None, None
        brightness = None
        dht_checkbox_val = None 
        temp_unit_val = None

        for param in params:
            # Use find to cleanly separate key and value, handling cases where the value is missing
            if '=' in param:
                key, value = param.split('=', 1)
            else:
                continue # Skip if it's not a key=value pair

            # --- Update the assignment logic ---
            if key == 'ssid': new_ssid = value
            elif key == 'pass': new_password = value
            elif key == 'dry': dry_val = value
            elif key == 'wet': wet_val = value
            elif key == 'broker': broker = value
            elif key == 'port': port = value
            elif key == 'user': user = value
            elif key == 'mqtt_pass': mqtt_pass = value
            elif key == 'brightness': brightness = value
            elif key == 'dht_enabled': dht_checkbox_val = value
            elif key == 'temp_unit': temp_unit_val = value

        # --- CALIBRATION CHECK (REQUIRED) ---
        if not dry_val or not wet_val: return False 
        try:
            dry_val = int(dry_val)
            wet_val = int(wet_val)
        except ValueError:
            return False 

        # --- WIFI HANDLING (USE OLD VALUES IF NEW ONES ARE EMPTY) ---
        current_ssid, current_password = load_current_wifi_config()
        final_ssid = url_decode(new_ssid) if new_ssid else current_ssid
        final_password = url_decode(new_password) if new_password else current_password
        if not final_ssid or not final_password: return False # Must have valid Wi-Fi

        # --- MQTT HANDLING ---
        
        # Load existing MQTT config for fallback
        current_broker, current_port, current_user, current_mqtt_pass, current_brightness = load_current_config_details()

        # Determine final MQTT values (Use new if provided, otherwise fallback)
        decoded_broker = url_decode(broker).strip() if broker else ""
        final_port = int(port) if port else current_port
        final_user = url_decode(user).strip() if user else current_user
        final_mqtt_pass = url_decode(mqtt_pass).strip() if mqtt_pass else current_mqtt_pass
        
        if len(decoded_broker) > 0:
            # Use the newly submitted, decoded value
            final_broker = decoded_broker
        else:
            # If the submitted field was blank, use the currently loaded value
            final_broker = current_broker

        # --- BRIGHTNESS HANDLING (Required, must be 0-255) ---
        if not brightness: return False
        try:
            final_brightness = int(brightness)
            if not (0 <= final_brightness <= 255):
                print("ERROR: Brightness must be 0-255.")
                return False
        except ValueError:
            print("ERROR: Brightness must be an integer.")
            return False
        
        # --- DHT ENABLED HANDLING ---
        final_dht_enabled = True if dht_checkbox_val == 'true' else False

        # --- TEMP UNIT HANDLING ---
        # True if 'C' is selected, False if 'F' is selected
        final_temp_unit_c = True if temp_unit_val == 'C' else False

        # Update global variables immediately (optional, but good for testing)
        global CALIBRATION_DRY, CALIBRATION_WET, BRIGHTNESS_LEVEL, DHT_ENABLED, TEMP_UNIT_C
        CALIBRATION_DRY = dry_val
        CALIBRATION_WET = wet_val
        BRIGHTNESS_LEVEL = final_brightness
        DHT_ENABLED = final_dht_enabled
        TEMP_UNIT_C = final_temp_unit_c

        # Save all values and reboot
        save_config(final_ssid, final_password, dry_val, wet_val, final_broker, final_port, final_user, final_mqtt_pass, final_brightness, final_dht_enabled, final_temp_unit_c)
        return True
    return False

def create_config_page(message=""):
    global CALIBRATION_DRY, CALIBRATION_WET
    
    # Load current Wi-Fi status for pre-filling the form
    current_ssid, _ = load_current_wifi_config()
    current_broker, current_port, current_user, _, current_brightness, current_dht_enabled, current_temp_unit_c  = load_current_config_details() 
    
    # Checkbox state logic
    dht_checked = "checked" if current_dht_enabled else ""
    c_checked = "checked" if current_temp_unit_c else ""
    f_checked = "checked" if not current_temp_unit_c else ""
    """Generates the HTML for the configuration portal."""
    html = f"""<!DOCTYPE html>
<html>
<head>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <link rel="icon" href="data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 100 100%22><text y=%22.9em%22 font-size=%2290%22>🪴</text></svg>" />
    <title>WiFi Config</title>
    <style>
        body {{ font-family: Arial, sans-serif; text-align: center; margin: 20px; background-color: #f4f4f4; }}
        .container {{ background-color: #ffffff; padding: 30px; border-radius: 8px; box-shadow: 0 4px 8px rgba(0,0,0,0.1); max-width: 400px; margin: 0 auto; }}
        input[type=text], input[type=password] {{ width: 100%; padding: 12px 20px; margin: 8px 0; display: inline-block; border: 1px solid #ccc; border-radius: 4px; box-sizing: border-box; }}
        input[type=submit] {{ width: 100%; background-color: #4CAF50; color: white; padding: 14px 20px; margin: 8px 0; border: none; border-radius: 4px; cursor: pointer; }}
        .message {{ color: red; font-weight: bold; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Moisture Sensor Config</h1>
        <p>Leave WiFi fields blank to keep current connection.</p>
        <div class="message">{message}</div>
<form action="/" method="get">
            <h2>WiFi Credentials</h2>
            <label for="ssid">WiFi SSID (Current: {current_ssid or 'N/A'}):</label>
            <input type="text" id="ssid" name="ssid" value="" placeholder="Leave blank to keep existing SSID">
            
            <label for="pass">Password:</label>
            <input type="password" id="pass" name="pass" value="" placeholder="Leave blank to keep existing password">
            
            <h2>Calibration Values (Raw ADC)</h2>
            <label for="dry">Dry Reading (0% Moisture):</label>
            <input type="text" id="dry" name="dry" value="{CALIBRATION_DRY}" required>
            <label for="wet">Wet Reading (100% Moisture):</label>
            <input type="text" id="wet" name="wet" value="{CALIBRATION_WET}" required>

            <h2>MQTT Broker Settings</h2>
            <label for="broker">Broker Address:</label>
            <input type="text" id="broker" name="broker" value="{current_broker}">
            
            <label for="port">Port:</label>
            <input type="text" id="port" name="port" value="{current_port}" placeholder="1883">

            <label for="user">Username (optional):</label>
            <input type="text" id="user" name="user" value="{current_user}">

            <label for="mqtt_pass">Password (optional):</label>
            <input type="password" id="mqtt_pass" name="mqtt_pass" value="">

            <h2>Peripheral Settings</h2>
            <label for="brightness">NeoPixel Brightness (0-255):</label>
            <input type="text" id="brightness" name="brightness" value="{current_brightness}" placeholder="50" required>
            
            <label for="dht_enabled" style="display:block; margin-top:15px;">
                <input type="checkbox" id="dht_enabled" name="dht_enabled" value="true" {dht_checked}> 
                Enable DHT22 Temperature/Humidity Sensor
            </label>

            <h3 style="margin-top:20px;">Temperature Unit</h3>
            <label style="margin-right:20px;">
                <input type="radio" name="temp_unit" value="C" {c_checked} required> Celsius (°C)
            </label>
            <label>
                <input type="radio" name="temp_unit" value="F" {f_checked}> Fahrenheit (°F)
            </label>

            
            <input type="submit" value="Save Settings & Reboot">
        </form>
    </div>
</body>
</html>"""
    return html

# --- Data Display Functions (Unchanged, but kept for clarity) ---

def create_data_page():
    """Generates the HTML content with current sensor data."""
    if current_moisture_percent < 20:
        status_color = "#e74c3c" # Red (Very Dry)
        status_text = "VERY DRY - NEEDS WATER!"
    elif current_moisture_percent < 50:
        status_color = "#f39c12" # Orange (Moderately Dry)
        status_text = "IDEAL - Check again soon."
    else:
        status_color = "#2ecc71" # Green (Moist/Wet)
        status_text = "MOIST - No need to water."

    # Helper to convert C to F
    current_temp_f = round((current_temp_c * 9/5) + 32, 1) if current_temp_c else 0.0
    
    # Determine which unit to display
    if TEMP_UNIT_C:
        display_temp = current_temp_c
        unit_symbol = "°C"
    else:
        display_temp = current_temp_f
        unit_symbol = "°F"

    # Conditional DHT HTML Section
    dht_html = ""
    if DHT_ENABLED:
        dht_html = f"""
            <h2>Environmental Data</h2>
            <div class="data">Temperature: <strong>{display_temp}{unit_symbol}</strong></div>
            <div class="data">Humidity: <strong>{current_humidity}%</strong></div>
        """
        
    lt = time.localtime()
    time_string = "{:02d}:{:02d}:{:02d}".format(lt[3], lt[4], lt[5])

    # --- START OF CORRECTED HTML HEADER ---
    html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <meta http-equiv="refresh" content="15">
    <link rel="icon" href="data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 100 100%22><text y=%22.9em%22 font-size=%2290%22>🪴</text></svg>" />
    <title>ESP32 Moisture Monitor</title>
    <style>
        body {{ font-family: Arial, sans-serif; text-align: center; margin: 20px; background-color: #f4f4f4; }}
        .container {{ background-color: #ffffff; padding: 20px; border-radius: 8px; box-shadow: 0 4px 8px rgba(0,0,0,0.1); max-width: 400px; margin: 0 auto; }}
        h1 {{ color: #333; }}
        .data {{ margin: 15px 0; padding: 10px; border: 1px solid #ddd; border-radius: 4px; }}
        .moisture-bar {{ height: 30px; line-height: 30px; color: white; border-radius: 4px; transition: width 0.5s; }}
        .status {{ margin-top: 20px; font-weight: bold; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Soil Moisture Sensor</h1>
        <p>Last Updated: {time_string}</p>
        {dht_html}
        <h2>Moisture Level</h2>
        <div style="background-color:#eee; border-radius:4px;">
            <div class="moisture-bar" style="width: {current_moisture_percent}%; min-width: 15%; background-color: {status_color};">{current_moisture_percent}%</div>
        </div>
        <div class="status" style="color: {status_color};">{status_text}</div>

        <h2>Raw Data</h2>
        <div class="data">Raw Reading: <strong>{current_raw_reading}</strong></div>
        <div class="data">Dry: {CALIBRATION_DRY}, Wet: {CALIBRATION_WET}</div>
        <p style="font-size: small; color: #777;"><a href="/config">Configuration</a> | Page refreshes every 15s. | Device ID: {SHORT_DEVICE_ID}</p>
    </div>
</body>
</html>"""
    # --- END OF CORRECTED HTML HEADER ---
    return html 

# --- Main Runtime ---

def run_project():
    
    # Determine the mode (STA or AP)
    sta_if = network.WLAN(network.STA_IF)
    ap_if = network.WLAN(network.AP_IF)
    
    is_config_mode = ap_if.active() # True if AP is running from boot.py
    
    # --- MQTT SETUP: Attempt connection only if NOT in config mode ---
    if not is_config_mode:
        mqtt_connect() 

    # Start the server socket
    s = None # Initialize to None for safer closing
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind(('', WEB_PORT))
        s.listen(5)
        
        # This is CRITICAL for non-blocking server operation
        s.settimeout(1.0) 
        
        print(f"Web server running on port {WEB_PORT}.")
    except Exception as e:
        print(f"FATAL: Could not start web server: {e}")
        if s: s.close()
        return # Exit the function if the server can't start

    last_read_time = time.ticks_ms()
    
    while True:
        # Check if it's time to read the sensor (only do this in STA mode or if a configuration page is not being served)
        if not is_config_mode and time.ticks_diff(time.ticks_ms(), last_read_time) > READING_DELAY_MS:
            read_moisture()
            print(f"Sensor Read: Raw={current_raw_reading}, Moisture={current_moisture_percent}%")
            try:
                read_moisture()
                read_dht()
                
                # --- MQTT PUBLISH BLOCK ---
                if mqtt_client:
                    print("Publishing MQTT data...")
                    payload_data = {
                        "raw": current_raw_reading,
                        "moisture_percent": current_moisture_percent,
                        "device_id": SHORT_DEVICE_ID,
                        "timestamp": time.time() 
                    }
                    
                    if DHT_ENABLED:
                        payload_data["temperature_c"] = current_temp_c
                        payload_data["humidity_percent"] = current_humidity
                    
                    payload = json.dumps(payload_data)
                    mqtt_publish(payload)
                # -------------------------
                
            except Exception as e:
                print(f"ERROR: Sensor reading/MQTT failed: {e}")
            last_read_time = time.ticks_ms()
            
        # Handle incoming web connections
        try:
            conn, addr = s.accept()
            request = conn.recv(1024).decode()
            
            # 1. Check for form submission first
            if 'GET /?' in request and 'dry=' in request:
                print("Processing CONFIGURATION SUBMISSION...")

                # Submission logic
                if handle_config_submission(request):
                    conn.send(RESPONSE_HEADER_OK.encode())
                    conn.send(create_config_page("Configuration Saved. Device Resetting...").encode())
                    conn.close() 
                else:
                    conn.send(RESPONSE_HEADER_OK.encode())
                    conn.send(create_config_page("Error: Invalid input. Check calibration values.").encode())
                    conn.close()
            elif "GET /config" in request or ap_if.active():
                print("Serving Configuration Page.")
                # Serve the config page normally
                conn.send(RESPONSE_HEADER_OK.encode())
                conn.send(create_config_page().encode())
                conn.close()
            # 2. If it's not a submission, serve the data page normally
            else:
                conn.send(RESPONSE_HEADER_OK.encode())
                conn.send(create_data_page().encode())
                conn.close()
            
        # CATCH SPECIFIC OS ERRORS (like timeout or disconnects)
        except OSError as e:
            # Common non-fatal socket error codes:
            # 110: ETIMEDOUT (General Timeout)
            # 11: EAGAIN (Resource temporarily unavailable/non-blocking timeout)
            # 35: EWOULDBLOCK (Operation would block/non-blocking timeout)
            # 116: ETIMEDOUT (Specific Timeout, commonly seen on ESP32)
            if len(e.args) == 2 and e.args[0] in (110, 11, 35, 113, 116): 
                pass # Ignore the expected timeout or resource error
            else:
                # Only print if it's a truly unexpected error
                print(f"UNEXPECTED Socket Error: {e}")
                # Optional: Add conn.close() here if you suspect a partial connection
            
        # CATCH ALL OTHER PYTHON EXCEPTIONS
        except Exception as e:
            print(f"Runtime Exception in Main Loop: {e}")
            # If a connection was established, ensure it's closed even if page serving failed
            try:
                if 'conn' in locals():
                    conn.close()
            except:
                pass
        finally:
            # Guarantee the connection is closed whether or not an error occurred
            if 'conn' in locals():
                try:
                    conn.close()
                except:
                    pass

# Run the project
if __name__ == '__main__':
    run_project()