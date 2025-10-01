import machine
import time
import socket
import network
import json

# --- Global Sensor Data ---
current_raw_reading = 0
current_moisture_percent = 0.0

# --- Sensor Configuration ---
SENSOR_PIN = 9          
CALIBRATION_DRY = 8191  # Your highest observed Raw ADC value for DRY soil
CALIBRATION_WET = 4300  # Your lowest observed Raw ADC value for WET soil
READING_DELAY_MS = 5000 

# --- Web Server Configuration ---
WEB_PORT = 80
RESPONSE_HEADER_OK = 'HTTP/1.0 200 OK\r\nContent-type: text/html\r\n\r\n'
RESPONSE_HEADER_REDIRECT = 'HTTP/1.0 302 Found\r\nLocation: /\r\n\r\n'
CONFIG_FILE = "config.json"

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

def save_config(ssid, password):
    """Saves new credentials to config.json and resets."""
    config = {'ssid': ssid, 'password': password}
    try:
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f)
        print(f"Config saved for SSID: {ssid}. Resetting...")
        time.sleep(1)
        machine.reset()
    except Exception as e:
        print(f"Failed to save config: {e}")

def handle_config_submission(request):
    """Parses form data from the request."""
    # Look for query parameters in a GET request (e.g., /?ssid=X&pass=Y)
    if 'GET /?ssid=' in request:
        params = request.split(' ')[1].split('?')[1].split('&')
        
        ssid = None
        password = None
        
        for param in params:
            key, value = param.split('=')
            if key == 'ssid':
                ssid = value
            elif key == 'pass':
                password = value
        
        if ssid and password:
            # Decode the URL-encoded characters before saving!
            decoded_ssid = url_decode(ssid)
            decoded_password = url_decode(password)
            
            save_config(decoded_ssid, decoded_password)
            return True
    return False

def create_config_page(message=""):
    """Generates the HTML for the configuration portal."""
    html = f"""<!DOCTYPE html>
<html>
<head>
    <meta name="viewport" content="width=device-width, initial-scale=1">
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
        <h1>Moisture Sensor WiFi Config</h1>
        <p>Enter your network credentials to connect the sensor.</p>
        <div class="message">{message}</div>
        <form action="/" method="get">
            <label for="ssid">WiFi SSID:</label>
            <input type="text" id="ssid" name="ssid" required>
            <label for="pass">Password:</label>
            <input type="password" id="pass" name="pass" required>
            <input type="submit" value="Connect and Save">
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
        
    lt = time.localtime()
    time_string = "{:02d}:{:02d}:{:02d}".format(lt[3], lt[4], lt[5])

    # --- START OF CORRECTED HTML HEADER ---
    html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <meta http-equiv="refresh" content="15">
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

        <h2>Moisture Level</h2>
        <div style="background-color:#eee; border-radius:4px;">
            <div class="moisture-bar" style="width: {current_moisture_percent}%; min-width: 15%; background-color: {status_color};">{current_moisture_percent}%</div>
        </div>
        <div class="status" style="color: {status_color};">{status_text}</div>

        <h2>Raw Data</h2>
        <div class="data">Raw Reading: <strong>{current_raw_reading}</strong></div>
        <div class="data">Dry: {CALIBRATION_DRY}, Wet: {CALIBRATION_WET}</div>
        <p style="font-size: small; color: #777;"><a href="/config">Change WiFi</a> | Page refreshes every 15s.</p>
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
            last_read_time = time.ticks_ms()
            
        # Handle incoming web connections
        try:
            conn, addr = s.accept()
            request = conn.recv(1024).decode()
                   
            # --- Handle Configuration Mode (AP) ---
            if is_config_mode:
                if handle_config_submission(request):
                    # Submission handled (saved config and reset)
                    conn.send(RESPONSE_HEADER_OK.encode())
                    conn.send(create_config_page("Configuration Saved. Device Resetting...").encode())
                else:
                    # Serve the config page
                    conn.send(RESPONSE_HEADER_OK.encode())
                    conn.send(create_config_page().encode())

            # --- Handle Data Mode (STA) ---
            else:
                # Allows user to manually access the config page via a link on the main page
                if "GET /config" in request:
                    conn.send(RESPONSE_HEADER_OK.encode())
                    conn.send(create_config_page("Current WiFi is working. To change it, enter new credentials:").encode())
                else:
                    # Serve the main data page
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