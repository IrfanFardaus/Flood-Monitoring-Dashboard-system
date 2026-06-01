print("+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=")
print("\n\t   Flood Monitoring Dashboard")
print("\n\t\t\tBy:\n")
print("\t[Muhammad Irfan Bin Mohd Fardaus]")
print("\t\t   (2026)\n")
print("+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=")

# Import libraries
import network
import ujson
import time
from machine import Pin, ADC, I2C, UART
from micropyGPS import MicropyGPS
from ajsr04m import AJSR04M
from utime import sleep
import urequests
import sh1106
import gc

# ==========================================
# Configuration
# ==========================================

FIREBASE_URL = 'https://flood-monitoring-fe2af-default-rtdb.asia-southeast1.firebasedatabase.app/'
FIREBASE_SECRET = '9pIyP8XCd9SvTQitIjXYvbSsL07qQqo3X0AZti78'

led_green = Pin(4, Pin.OUT)
led_yellow = Pin(13, Pin.OUT)
led_red = Pin(14, Pin.OUT)

btn1 = Pin(25, Pin.IN, Pin.PULL_UP)
btn2 = Pin(26, Pin.IN, Pin.PULL_UP)
btn3 = Pin(27, Pin.IN, Pin.PULL_UP)
btn4 = Pin(33, Pin.IN, Pin.PULL_UP)

sensor1 = AJSR04M(trigger_pin=5, echo_pin=18)
sensor2 = AJSR04M(trigger_pin=19, echo_pin=23)

turbidity_adc = ADC(Pin(34))
turbidity_adc.atten(ADC.ATTN_11DB) # Full range: 0-3.3V (0-4095)

gps_uart = UART(2, baudrate=9600, tx=17, rx=16)
my_gps = MicropyGPS()

i2c = I2C(0, scl=Pin(22), sda=Pin(21))
oled = sh1106.SH1106_I2C(128, 64, i2c)

# Parameter
DEVICE_ID = "SENSOR_001"  # Unique identifier for this device
sensor_height = 100.0 # Default sensor installation height from ground (cm)

# ==========================================
# Function blocks
# ==========================================

def write_to_firebase(path, data):
    """Writes data to a specific path in the Realtime Database via REST."""
    url = f"{FIREBASE_URL}{path}.json?auth={FIREBASE_SECRET}"
    print(f"Sending data to: {path}...")
    gc.collect()
    try:
        response = urequests.patch(url, json=data)
        if response.status_code == 200:
            print("Data written successfully!")
        else:
            print(f"Failed. Status Code: {response.status_code}")
            print("Response:", response.text)
        response.close()
    except Exception as e:
        print("Error sending data:", e)

def read_turbidity():
    """Reads analog value and converts to a dummy percentage."""
    val = turbidity_adc.read()
    percentage = 100.0 - ((val / 4000.0) * 100.0)
    if percentage < 0:
        percentage = 0.0
    elif percentage > 100:
        percentage = 100.0
    return percentage

def update_gps():
    """Safely updates GPS data without fragmenting RAM"""
    # 1. Flush the UART buffer of old, backed-up data
    while gps_uart.any():
        gps_uart.read(gps_uart.any())
        
    start_time = time.ticks_ms()
    
    # 2. Listen for up to 2 seconds for fresh NMEA sentences
    while time.ticks_diff(time.ticks_ms(), start_time) < 2000:
        if gps_uart.any():
            raw_data = gps_uart.read()
            for byte in raw_data:
                # Feed characters into the library one by one
                my_gps.update(chr(byte))

# def get_memory_safe_gps():
#     # 1. Flush the backed-up UART buffer so we don't read a massive string
#     while gps_uart.any():
#         gps_uart.read(gps_uart.any())
    
#     lat, lon = 0.0, 0.0
#     start_time = time.ticks_ms()
    
#     # 2. Only listen to the GPS for a maximum of 2 seconds
#     while time.ticks_diff(time.ticks_ms(), start_time) < 2000:
#         if gps_uart.any():
#             try:
#                 # Read strictly one line at a time
#                 line = gps_uart.readline() 
#                 if line:
#                     # Decode only if necessary, otherwise work with bytes to save RAM
#                     sentence = line.decode('utf-8').strip() 
                    
#                     # Example: Look for GPGGA or GPRMC
#                     if sentence.startswith('$GPGGA'):
#                         parts = sentence.split(',')
#                         if len(parts) > 4 and parts[2] != '':
#                             # Basic extraction (you'd add your specific math here)
#                             lat = float(parts[2]) 
#                             lon = float(parts[4])
#                             break # Found it! Stop parsing to save memory
#             except Exception:
#                 pass 
                
#     return lat, lon

def main():
    global sensor_height
    
    # Establish network connection before beginning the main loop
    # connect_wifi()

    led_green.value(0)
    led_yellow.value(0)
    led_red.value(0)

    while True:
        if btn4.value() == 0: 
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
                    oled.fill(0)
                    oled.rect(10, 20, 108, 24, 1)
                    oled.text("SAVED!", 40, 28)
                    oled.show()
                    sleep(1)
                elif btn4.value() == 0: 
                    sleep(0.2)
                    break

        else:
            dist_left = sensor1.distance_cm()
            dist_right = sensor2.distance_cm()
            update_gps()
            # get_gps_data()
            # lat, lon = get_memory_safe_gps()

            # flood level calculation
            depth_left = sensor_height - dist_left
            depth_right = sensor_height - dist_right
            avg_depth = (depth_left + depth_right) / 2.0

            # turbidity percentage
            turb_percent = read_turbidity()
            if turb_percent >= 5:
                turb_status = "Dirty"
            elif turb_percent >= 2:
                turb_status = "Cloudy"
            else:
                turb_status = "Clean"

            # Severity status
            severity_status = ""
            if abs(dist_left - dist_right) <= 5.0: # tolerence check
                if avg_depth >= 25.0:
                    severity_status = "DANGER"
                    led_green.value(0)
                    led_yellow.value(0)
                    led_red.value(1)
                elif avg_depth >= 5.0:
                    severity_status = "WARNING"
                    led_green.value(0)
                    led_yellow.value(1)
                    led_red.value(0)
                else:
                    severity_status = "SAFE"
                    led_green.value(1)
                    led_yellow.value(0)
                    led_red.value(0)
            else:
                severity_status = "INVALID"
                led_green.value(0)
                led_yellow.value(0)
                led_red.value(0)

            print(f"[ULTRASONIC] Left: {dist_left:.1f}cm | Right: {dist_right:.1f}cm")
            print(f"[DATA] Sensor Height Base: {sensor_height:.1f}cm | Current Depth: {avg_depth:.1f}cm")
            print(f"[TURBIDITY] Raw: {turb_percent:.1f}% | Status: {turb_status}")
            print(f"[LONGITUDE] {my_gps.longitude}")
            print(f"[LATITUDE] {my_gps.latitude}")
            print(f"[SEVERITY] Level: {severity_status}")
            # print(f"[SYSTEM] Time: {my_gps.timestamp}")
            print("-------------------------")

            # OLED DASHBOARD
            oled.fill(0)

            oled.text("FLOOD M", 0, 0)
            oled.hline(0, 10, 128, 1) 
            
            oled.text(f"Depth: {avg_depth:.1f} cm", 0, 15)
            oled.text(f"Water: {turb_status}", 0, 27)
            
            oled.text("Alert:", 0, 41)
            oled.rect(50, 38, 70, 13, 1) 
            oled.text(severity_status, 54, 41)
            
            oled.hline(0, 54, 128, 1) 
            oled.text(f"L:{dist_left:.0f}cm  R:{dist_right:.0f}cm", 0, 57)
            oled.show()
            
            # --- FIREBASE INTEGRATION ---
            # Compile current system data into a single payload
            sensor_data = {
                "depth_cm": avg_depth,
                "dist_left_cm": dist_left,
                "dist_right_cm": dist_right,
                "turbidity_percent": turb_percent,
                "turbidity_status": turb_status,
                "severity": severity_status,
                # "latitude": lat,
                # "longitude": lon,
                "timestamp": time.time(),  # Use epoch time for simplicity
                "latitude": my_gps.latitude,
                "longitude": my_gps.longitude,
            }
            
            # Push payload to the database
            write_to_firebase(f"sensors/{DEVICE_ID}", sensor_data)
            
            sleep(5)

if __name__ == "__main__":
    main()