import machine
import time
import network
import urequests
import sh1106
import math
from micropyGPS import MicropyGPS

# --- CONFIGURATION ---
WIFI_SSID = 'MSI'
WIFI_PASS = 'hinge123'
FIREBASE_URL = 'https://flood-monitoring-fe2af-default-rtdb.asia-southeast1.firebasedatabase.app/data.json' # Replace with your RTDB URL
settings_requested = False
last_btn4_press = 0

# --- PIN INITIALIZATION ---

# 1. OLED Display (I2C)
i2c = machine.I2C(0, scl=machine.Pin(22), sda=machine.Pin(21))
oled = sh1106.SH1106_I2C(128, 64, i2c)

# 2. GPS Module (UART2)
# TX2 = 17, RX2 = 16 (ESP32 side)
gps_uart = machine.UART(2, baudrate=9600, tx=17, rx=16)
my_gps = MicropyGPS(8, 'dd')

# 3. Ultrasonic Sensors
trig1 = machine.Pin(5, machine.Pin.OUT)
echo1 = machine.Pin(18, machine.Pin.IN)

trig2 = machine.Pin(19, machine.Pin.OUT)
echo2 = machine.Pin(23, machine.Pin.IN)

# 4. Turbidity Sensor
turbidity_adc = machine.ADC(machine.Pin(34))
turbidity_adc.atten(machine.ADC.ATTN_11DB) # Full range: 0-3.3V (0-4095)

# 5. LEDs
led_green = machine.Pin(4, machine.Pin.OUT)
led_yellow = machine.Pin(13, machine.Pin.OUT)
led_red = machine.Pin(14, machine.Pin.OUT)

# 6. Push Buttons (Assuming active-low with internal Pull-Ups)
btn1 = machine.Pin(25, machine.Pin.IN, machine.Pin.PULL_UP) # +1 Height
btn2 = machine.Pin(26, machine.Pin.IN, machine.Pin.PULL_UP) # -1 Height
btn3 = machine.Pin(27, machine.Pin.IN, machine.Pin.PULL_UP) # Save
btn4 = machine.Pin(33, machine.Pin.IN, machine.Pin.PULL_UP) # Menu / Select

# Global variables
sensor_height = 100.0 # Default sensor installation height from ground (cm)

# --- HELPER FUNCTIONS ---

def connect_wifi():
    """Connect to Wi-Fi as per flowchart initialization."""
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

def get_distance(trig, echo):
    """Read distance from AJ-SR04M in cm."""
    trig.value(0)
    time.sleep_us(2)
    trig.value(1)
    time.sleep_us(10)
    trig.value(0)
    
    duration = machine.time_pulse_us(echo, 1, 30000) # 30ms timeout
    if duration < 0:
        return 0.0
    distance = (duration / 2) / 29.1
    return distance

def read_turbidity():
    """Reads analog value and converts to a dummy percentage."""
    val = turbidity_adc.read()
    # Basic mapping from 0-4000 to 0-100%. Adjust formula based on sensor calibration.
    percentage = 100.0 - ((val / 4000.0) * 100.0)
    if percentage < 0:
        percentage = 0.0
    elif percentage > 100:
        percentage = 100.0
    return percentage

def get_gps_location():
    """Reads UART buffer, parses NMEA sentences, and returns formatted coordinates."""
    
    # Read all available characters in the UART buffer
    while gps_uart.any():
        raw_data = gps_uart.read(1) # Read one byte at a time
        if raw_data:
            try:
                # Decode the byte to a string character and feed it to the parser
                char = raw_data.decode('utf-8')
                
                # --- NEW TRY/EXCEPT BLOCK ---
                try:
                    my_gps.update(char) 
                except IndexError:
                    # Ignore incomplete NMEA sentences that crash the parser
                    pass
                except Exception as e:
                    # Catch any other parsing math/value errors from corrupted data
                    pass
                # ----------------------------

            except UnicodeError:
                # Ignore garbled serial data during startup or poor connection
                pass
                
    # Retrieve the formatted latitude and longitude strings from the parser
    lat_str = my_gps.latitude_string()
    lon_str = my_gps.longitude_string()
    
    # If the GPS doesn't have a fix yet, it will output "0.0° N, 0.0° W"
    if my_gps.latitude[0] == 0.0 and my_gps.longitude[0] == 0.0:
        return "Waiting for Fix..."
    
    return f"Lat: {lat_str}, Lon: {lon_str}"

def send_to_firebase(turb_stat, loc, sev, avg_depth):
    """Sends payload to Firebase Realtime Database."""
    payload = {
        "turbidity_status": turb_stat,
        "location": loc,
        "severity": sev,
        "flood_level_cm": avg_depth
    }
    try:
        response = urequests.put(FIREBASE_URL, json=payload)
        response.close()
    except Exception as e:
        print("Firebase Error:", e)

def btn4_isr(pin):
    """Interrupt Service Routine for Button 4"""
    global settings_requested, last_btn4_press
    current_time = time.ticks_ms()
    
    # 300ms debounce to prevent ghost presses
    if time.ticks_diff(current_time, last_btn4_press) > 300:
        settings_requested = True
        last_btn4_press = current_time

# Attach the interrupt to Button 4 (Triggers when the pin goes LOW)
btn4.irq(trigger=machine.Pin.IRQ_FALLING, handler=btn4_isr)

# --- MAIN LOGIC ---

def main():
    global sensor_height, settings_requested
    
    # 1. Initiate components & connect Wi-Fi
    led_green.value(0)
    led_yellow.value(0)
    led_red.value(0)
    connect_wifi()

    while True:
        # Check the interrupt flag instead of the physical button
        if settings_requested: 
            time.sleep(0.2) 
            
            # Setting Loop
            while True:
                oled.fill(0)
                oled.text("Settings Mode", 0, 0)
                oled.text(f"Height: {sensor_height}cm", 0, 20)
                oled.show()
                
                if btn1.value() == 0:   
                    sensor_height += 1
                    time.sleep(0.2)
                elif btn2.value() == 0: 
                    sensor_height -= 1
                    time.sleep(0.2)
                elif btn3.value() == 0: 
                    oled.fill(0)
                    oled.text("Height Saved!", 0, 20)
                    oled.show()
                    time.sleep(1)
                elif btn4.value() == 0: # Exit settings
                    settings_requested = False # Reset the flag!
                    time.sleep(0.2)
                    break

        else:
            # --- NORMAL OPERATION FLOW ---
            
            # Read Ultrasonic Sensors
            dist_left = get_distance(trig1, echo1)
            dist_right = get_distance(trig2, echo2)
            
            # Read GPS
            location = get_gps_location()
            
            # Calculate Flood Depth (Height of sensor from ground - distance to water)
            depth_left = sensor_height - dist_left
            depth_right = sensor_height - dist_right
            avg_depth = (depth_left + depth_right) / 2.0
            
            # Read Turbidity
            turb_percent = read_turbidity()
            if turb_percent >= 5:
                turb_status = "Dirty"
            elif turb_percent >= 2:
                turb_status = "Cloudy"
            else:
                turb_status = "Clean"
                
            # Process Tolerance & Severity
            severity_status = ""
            
            if abs(dist_left - dist_right) <= 5.0: # Tolerance 5cm
                if avg_depth >= 25.0:
                    severity_status = "Danger"
                    led_green.value(0)
                    led_yellow.value(0)
                    led_red.value(1)
                elif avg_depth >= 5.0:
                    severity_status = "Warning"
                    led_green.value(0)
                    led_yellow.value(1)
                    led_red.value(0)
                else:
                    severity_status = "Safe"
                    led_green.value(1)
                    led_yellow.value(0)
                    led_red.value(0)
            else:
                severity_status = "Invalid"
                led_green.value(0)
                led_yellow.value(0)
                led_red.value(0)

            # --- PRINT ALL READINGS TO CONSOLE ---
            print(f"[ULTRASONIC] Left Dist: {dist_left:.1f}cm | Depth: {depth_left:.1f}cm")
            print(f"[ULTRASONIC] Right Dist: {dist_right:.1f}cm | Depth: {depth_right:.1f}cm")
            print(f"[DATA] Average Depth: {avg_depth:.1f}cm")
            print(f"[TURBIDITY] Raw: {turb_percent:.1f}% | Status: {turb_status} | value: {turbidity_adc.read()}")
            print(f"[GPS] {location}")
            print(f"[SEVERITY] Level: {severity_status}")
            print(f"[LEDs] Green: {led_green.value()} | Yellow: {led_yellow.value()} | Red: {led_red.value()}")
            print("-------------------------")

            # Update OLED Display
            oled.fill(0)
            oled.text(f"Depth: {avg_depth:.1f}cm", 0, 0)
            oled.text(f"Turb: {turb_status}", 0, 15)
            oled.text(f"Sev: {severity_status}", 0, 30)
            oled.show()
            
            # Send to Firebase
            send_to_firebase(turb_status, location, severity_status, avg_depth)
            
            # This waits 5 seconds total (50 * 0.1s) but checks the flag 10 times a second
            for _ in range(50):
                if settings_requested:
                    break # Exit the delay immediately to open settings
                time.sleep(0.1)

# Start execution
if __name__ == "__main__":
    main()