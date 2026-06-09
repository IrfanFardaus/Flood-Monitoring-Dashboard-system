print("+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=")
print("\n\t   Flood Monitoring Dashboard")
print("\n\t\t\tBy:\n")
print("\t[Muhammad Irfan Bin Mohd Fardaus]")
print("\t\t   (2026)\n")
print("+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=")

# Import libraries
from machine import Pin, ADC, I2C, UART
from micropyGPS import MicropyGPS
from ajsr04m import AJSR04M
from utime import sleep
import _thread
import network
import urequests
import sh1106
import json
import ntptime
import time
import gc

# configuration
led_green = Pin(4, Pin.OUT)
led_yellow = Pin(13, Pin.OUT)
led_red = Pin(14, Pin.OUT)

btn1 = Pin(33, Pin.IN, Pin.PULL_UP)
btn2 = Pin(27, Pin.IN, Pin.PULL_UP)
btn3 = Pin(26, Pin.IN, Pin.PULL_UP)

sensor1 = AJSR04M(trigger_pin=5, echo_pin=18)
sensor2 = AJSR04M(trigger_pin=19, echo_pin=23)

turbidity_adc = ADC(Pin(34))
turbidity_adc.atten(ADC.ATTN_11DB) # Full range: 0-3.3V (0-4095)

gps_uart = UART(2, baudrate=9600, tx=17, rx=16)
my_gps = MicropyGPS()

i2c = I2C(0, scl=Pin(22), sda=Pin(21))
oled = sh1106.SH1106_I2C(128, 64, i2c, rotate=180)

# Firestore configuration (Extracted from your old URL: flood-monitoring-fe2af)
PROJECT_ID = 'flood-monitor-c6977'

# IMPORTANT: You must get this from Firebase Console -> Project Settings -> Web API Key
API_KEY = 'AIzaSyAM-x6ZCqqxDx6ZDCE1JefDHwzLXvDq5M0' 

# Parameter
WIFI_SSID = 'Nothing'
WIFI_PASS = 'jackfruit'
DEVICE_ID = "SENSOR_001"  # Unique identifier for this device
sensor_height = 100 # Default sensor installation height from ground (cm)
SETTINGS_FILE = 'settings.json' # File to store persistent data
settings_requested = False
last_btn3_press = 0
upload_in_progress = False

# Function blocks

def connect_wifi():
    """Connect to Wi-Fi and sync local time."""
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if not wlan.isconnected():
        oled.fill(0)
        oled.text("Connecting WiFi...", 0, 0)
        oled.show()
        wlan.connect(WIFI_SSID, WIFI_PASS)
        while not wlan.isconnected():
            time.sleep(0.5)
    
    oled.fill(0)
    oled.text("WiFi Connected!", 0, 0)
    oled.show()
    time.sleep(1)

    # --- ADDED: Sync board time with internet ---
    try:
        print("Syncing time via NTP...")
        ntptime.settime()
        print("Time synced!")
    except Exception as e:
        print("Failed to sync time:", e)

def load_settings():
    """Loads configuration from a JSON file in flash memory."""
    global sensor_height
    try:
        with open(SETTINGS_FILE, 'r') as f:
            data = json.load(f)
            sensor_height = data.get('sensor_height', 100)
            print(f"[SYSTEM] Loaded settings: Height = {sensor_height}cm")
    except OSError:
        # File doesn't exist yet, which is normal on first boot
        print("[SYSTEM] No settings file found. Using default and creating file.")
        save_settings()
    except Exception as e:
        print(f"[ERROR] Failed to load settings: {e}")

def save_settings():
    """Saves current configuration to a JSON file in flash memory."""
    try:
        with open(SETTINGS_FILE, 'w') as f:
            json.dump({'sensor_height': sensor_height}, f)
        print(f"[SYSTEM] Saved settings: Height = {sensor_height}cm")
    except Exception as e:
        print(f"[ERROR] Failed to save settings: {e}")

def read_turbidity():
    """Reads analog value and converts to a dummy percentage."""
    val = turbidity_adc.read()
    # Basic mapping from 0-4095 to 0-100%. Adjust formula based on sensor calibration.
    percentage = 100.0 - ((val / 4095.0) * 100.0)
    if percentage < 0:
        percentage = 0.0
    elif percentage > 100:
        percentage = 100.0
    return percentage

def update_gps():
    """Safely updates GPS data without fragmenting RAM"""
    while gps_uart.any():
        gps_uart.read(gps_uart.any())
        
    start_time = time.ticks_ms()
    
    while time.ticks_diff(time.ticks_ms(), start_time) < 2000:
        if gps_uart.any():
            raw_data = gps_uart.read()
            for byte in raw_data:
                my_gps.update(chr(byte))

def btn3_isr(pin):
    """Interrupt Service Routine for Button 3"""
    global settings_requested, last_btn3_press
    current_time = time.ticks_ms()
    
    if time.ticks_diff(current_time, last_btn3_press) > 300:
        settings_requested = True
        last_btn3_press = current_time

btn3.irq(trigger=Pin.IRQ_FALLING, handler=btn3_isr)

def format_firestore_doc(data):
    """Converts a standard Python dictionary into the strict Firestore Document format."""
    fields = {}
    for key, value in data.items():
        if isinstance(value, bool):
            fields[key] = {"booleanValue": value}
        elif isinstance(value, int):
            fields[key] = {"integerValue": value}
        elif isinstance(value, float):
            fields[key] = {"doubleValue": value}
        else:
            fields[key] = {"stringValue": str(value)} # Convert tuples (like GPS) to string
    return {"fields": fields}

def write_to_firestore(collection, data):
    global upload_in_progress
    
    url = f"https://firestore.googleapis.com/v1/projects/{PROJECT_ID}/databases/(default)/documents/{collection}?key={API_KEY}"
    firestore_payload = format_firestore_doc(data)
    
    print("Uploading record to Firestore...")
    gc.collect() # Clean up memory before heavy network task
    
    try:
        response = urequests.post(url, json=firestore_payload)
        if response.status_code == 200:
            print("Upload Successful!")
        else:
            print(f"Failed. Status Code: {response.status_code}")
        response.close()
    except Exception as e:
        # If Wi-Fi drops, it will fail here instead of crashing the whole board
        print("Error sending data:", e)
    finally:
        # CRITICAL: The 'finally' block always runs, even if the 'try' block crashed.
        # This guarantees the lock is released so the next cycle can upload.
        upload_in_progress = False
        # Thread naturally dies here    



def main():
    global sensor_height, settings_requested, upload_in_progress

    led_green.value(0)
    led_yellow.value(0)
    led_red.value(0)
    load_settings()
    connect_wifi()

    danger_start_ticks = None
    warning_start_ticks = None
    THREE_MINUTES_MS = 180000

    while True:
        if btn3.value() == 0: 
            sleep(0.2) 
            
            # Setting Loop
            while True:
                oled.fill(0)
                oled.rect(0, 0, 128, 64, 1)
                oled.text(" SETTING MODE ", 10, 5)
                oled.hline(0, 16, 128, 1)
                oled.text(f"Height: {sensor_height}cm", 8, 30)
                oled.text("[+] [-] [SAVE]", 8, 50)
                oled.show()
                
                if btn1.value() == 0:   
                    sensor_height += 1
                    sleep(0.2)
                elif btn2.value() == 0: 
                    sensor_height -= 1
                    sleep(0.2)
                elif btn3.value() == 0: 
                    save_settings()
                    oled.fill(0)
                    oled.rect(10, 20, 108, 24, 1)
                    oled.text("SAVED!", 40, 28)
                    oled.show()
                    settings_requested = False
                    sleep(1)
                    break

        else:
            dist_left = sensor1.distance_cm()
            dist_right = sensor2.distance_cm()
            update_gps()

            unix_seconds = time.time() + 946684800
            timestamp_ms = int(unix_seconds * 1000)

            # flood level calculation
            depth_left = abs(sensor_height - dist_left)
            depth_right = abs(sensor_height - dist_right)
            avg_depth = (depth_left + depth_right) / 2.0

            # turbidity percentage
            turb_percent = read_turbidity()
            if turb_percent >= 50:
                turb_status = "Muddy"
            elif turb_percent >= 2:
                turb_status = "Dirty"
            else:
                turb_status = "Clean"

            # Severity status
            severity_status = ""
            if abs(dist_left - dist_right) <= 10.0: # tolerence check
                
                current_ticks = time.ticks_ms()

                # Track how long depth has been >= 40cm
                if avg_depth >= 40.0:
                    if danger_start_ticks is None:
                        danger_start_ticks = current_ticks
                else:
                    danger_start_ticks = None # Reset timer if it drops below 40

                # Track how long depth has been >= 15cm
                if avg_depth >= 15.0:
                    if warning_start_ticks is None:
                        warning_start_ticks = current_ticks
                else:
                    warning_start_ticks = None # Reset timer if it drops below 15

                # Evaluate flowchart conditions
                if avg_depth >= 40.0 and danger_start_ticks is not None and time.ticks_diff(current_ticks, danger_start_ticks) >= THREE_MINUTES_MS:
                    severity_status = "DANGER"
                    led_green.value(0)
                    led_yellow.value(0)
                    led_red.value(1)
                elif avg_depth >= 15.0 and warning_start_ticks is not None and time.ticks_diff(current_ticks, warning_start_ticks) >= THREE_MINUTES_MS:
                    severity_status = "WARNING"
                    led_green.value(0)
                    led_yellow.value(1)
                    led_red.value(0)
                else:
                    # Default Safe state (includes the first 3 minutes of a flood before it triggers)
                    severity_status = "SAFE"
                    led_green.value(1)
                    led_yellow.value(0)
                    led_red.value(0)
            else:
                severity_status = "INVALID"
                led_green.value(0)
                led_yellow.value(0)
                led_red.value(0)

            # Determine GPS status (Checks if GPS has a valid lock)
            if my_gps.valid: 
                gps_status_text = "GPS:OK"
            else:
                gps_status_text = "GPS:NO"
            # OLED DASHBOARD


            print(f"[ULTRASONIC] Left: {dist_left:.1f}cm | Right: {dist_right:.1f}cm")
            print(f"[DATA] Sensor Height Base: {sensor_height}cm | Current Depth: {avg_depth:.1f}cm")
            print(f"[TURBIDITY] Raw: {turb_percent:.1f}% | Status: {turb_status}")
            print(f"[LONGITUDE] {my_gps.longitude}")
            print(f"[LATITUDE] {my_gps.latitude}")
            print(f"[SEVERITY] Level: {severity_status}")
            print("-------------------------")



            oled.fill(0)
            
            oled.text("FLOOD M", 0, 0)
            oled.text(gps_status_text, 76, 0)
            oled.hline(0, 10, 128, 1) 
            
            oled.text(f"Depth: {avg_depth:.1f} cm", 0, 15)
            oled.text(f"Water: {turb_status}", 0, 27)
            oled.text(f"{turb_percent:.0f}%", 100, 27)
            
            
            oled.text("Alert:", 0, 41)
            oled.rect(50, 38, 70, 13, 1) 
            oled.text(severity_status, 54, 41)
            
            oled.hline(0, 54, 128, 1) 
            oled.text(f"L:{dist_left:.0f}cm  R:{dist_right:.0f}cm", 0, 57)
            oled.show()

            sensor_data = {
                "device_id": str(DEVICE_ID),        
                "depth_cm": float(avg_depth),
                "turbidity_percent": float(turb_percent),
                "turbidity_status": str(turb_status),
                "severity": str(severity_status),
                "timestamp": int (timestamp_ms), 
                "latitude": float(my_gps.latitude),   
                "longitude": float(my_gps.longitude), 
            }
            
            # Push payload to the database (Collection: "sensor_history")
            if not upload_in_progress:
                # Lock it immediately so the next loop cycle ignores it
                upload_in_progress = True 
                _thread.start_new_thread(write_to_firestore, ("sensor_history", sensor_data))
            else:
                # Optional: Print to console so you know it skipped properly
                print("[WARNING] Upload still in progress, skipping this data point.")

            for _ in range(50):
                if settings_requested:
                    break 
                time.sleep(0.1)

if __name__ == "__main__":
    main()