import machine
import time
import network
import urequests
import sh1106
import math
import ntptime
from micropyGPS import MicropyGPS

# --- CONFIGURATION ---
WIFI_SSID = 'MSI'
WIFI_PASS = 'hinge123'
FIREBASE_URL = 'https://flood-monitoring-fe2af-default-rtdb.asia-southeast1.firebasedatabase.app/node_01.json' # Replace with your RTDB URL
DEVICE_ID = 'NODE_01' # Unique identifier for this device
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
            
    # Synchronize time with NTP server once connected
    try:
        ntptime.settime()
        print("[SYSTEM] Time synced via NTP")
    except Exception as e:
        print(f"[ERROR] NTP sync failed: {e}")
    
    oled.fill(0)
    oled.text("WiFi Connected!", 0, 0)
    oled.show()
    time.sleep(1)

def get_timestamp():
    """Returns current timestamp adjusted for UTC+8."""
    try:
        # Add 8 hours (8 * 3600 seconds) for standard UTC+8 timezone
        t = time.time() + 28800
        tm = time.localtime(t)
        # Format: YYYY-MM-DD HH:MM:SS
        return f"{tm[0]:04d}-{tm[1]:02d}-{tm[2]:02d} {tm[3]:02d}:{tm[4]:02d}:{tm[5]:02d}"
    except Exception:
        return "Time Not Synced"

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
    percentage = 100.0 - ((val / 4000.0) * 100.0)
    if percentage < 0:
        percentage = 0.0
    elif percentage > 100:
        percentage = 100.0
    return percentage

def get_gps_location():
    """Reads UART buffer, parses NMEA sentences, and returns formatted coordinates."""
    while gps_uart.any():
        raw_data = gps_uart.read(1)
        if raw_data:
            try:
                char = raw_data.decode('utf-8')
                try:
                    my_gps.update(char) 
                except IndexError:
                    pass
                except Exception as e:
                    pass
            except UnicodeError:
                pass
                
    lat_str = my_gps.latitude_string()
    lon_str = my_gps.longitude_string()
    
    if my_gps.latitude[0] == 0.0 and my_gps.longitude[0] == 0.0:
        return "Waiting for Fix..."
    
    return f"Lat: {lat_str}, Lon: {lon_str}"

def send_to_firebase(turb_stat, loc, sev, avg_depth):
    """Sends payload including Device ID and Timestamp to Firebase RTDB."""
    payload = {
        "device_id": DEVICE_ID,
        "timestamp": get_timestamp(),
        "turbidity_status": turb_stat,
        "location": loc,
        "severity": sev,
        "flood_level_cm": avg_depth
    }
    try:
        response = urequests.put(FIREBASE_URL, json=payload)
        response.close()
        print(f"[FIREBASE] Data uploaded at {payload['timestamp']}")
    except Exception as e:
        print("Firebase Error:", e)

def btn4_isr(pin):
    """Interrupt Service Routine for Button 4"""
    global settings_requested, last_btn4_press
    current_time = time.ticks_ms()
    
    if time.ticks_diff(current_time, last_btn4_press) > 300:
        settings_requested = True
        last_btn4_press = current_time

btn4.irq(trigger=machine.Pin.IRQ_FALLING, handler=btn4_isr)

# --- MAIN LOGIC ---

def main():
    global sensor_height, settings_requested
    
    # 1. Initiate components & load saved data
    led_green.value(0)
    led_yellow.value(0)
    led_red.value(0)
    
    # Connect to Wi-Fi to sync the time
    connect_wifi()

    while True:
        # if settings_requested: 
        #     time.sleep(0.2) 
            
        #     # Setting Loop
        #     while True:
        #         oled.fill(0)
        #         oled.rect(0, 0, 128, 64, 1)
        #         oled.text(" SETTING MODE ", 10, 5)
        #         oled.hline(0, 16, 128, 1)
        #         oled.text(f"Height: {sensor_height}cm", 8, 30)
        #         oled.text("[+] [-] [SAVE]", 8, 50)
        #         oled.show()
                
        #         if btn1.value() == 0:   
        #             sensor_height += 1
        #             time.sleep(0.2)
        #         elif btn2.value() == 0: 
        #             sensor_height -= 1
        #             time.sleep(0.2)
        #         elif btn3.value() == 0: 
        #             oled.fill(0)
        #             oled.rect(10, 20, 108, 24, 1)
        #             oled.text("SAVED!", 40, 28)
        #             oled.show()
        #             time.sleep(1)
        #         elif btn4.value() == 0: 
        #             settings_requested = False 
        #             time.sleep(0.2)
        #             break

        # else:
        # --- NORMAL OPERATION FLOW ---
        dist_left = get_distance(trig1, echo1)
        dist_right = get_distance(trig2, echo2)
        location = get_gps_location()
        
        depth_left = sensor_height - dist_left
        depth_right = sensor_height - dist_right
        avg_depth = (depth_left + depth_right) / 2.0
        
        turb_percent = read_turbidity()
        if turb_percent >= 5:
            turb_status = "Dirty"
        elif turb_percent >= 2:
            turb_status = "Cloudy"
        else:
            turb_status = "Clean"
            
        severity_status = ""
        if abs(dist_left - dist_right) <= 5.0: 
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
            severity_status = "ERROR"
            led_green.value(0)
            led_yellow.value(0)
            led_red.value(0)

        print(f"[ULTRASONIC] Left: {dist_left:.1f}cm | Right: {dist_right:.1f}cm")
        print(f"[DATA] Sensor Height Base: {sensor_height:.1f}cm | Current Depth: {avg_depth:.1f}cm")
        print(f"[TURBIDITY] Raw: {turb_percent:.1f}% | Status: {turb_status}")
        print(f"[GPS] {location}")
        print(f"[SEVERITY] Level: {severity_status}")
        print(f"[SYSTEM] Time: {get_timestamp()}")
        print("-------------------------")

        # --- FANCY OLED DASHBOARD ---
        oled.fill(0)
        gps_icon = "OK" if "Lat" in location else "NO"
        oled.text("FLOOD M", 0, 0)
        oled.text(f"GPS:{gps_icon}", 70, 0)
        oled.hline(0, 10, 128, 1) 
        
        oled.text(f"Depth: {avg_depth:.1f} cm", 0, 15)
        oled.text(f"Water: {turb_status}", 0, 27)
        
        oled.text("Alert:", 0, 41)
        oled.rect(50, 38, 70, 13, 1) 
        oled.text(severity_status, 54, 41)
        
        oled.hline(0, 54, 128, 1) 
        oled.text(f"L:{dist_left:.0f}cm  R:{dist_right:.0f}cm", 0, 57)
        oled.show()
        
        # Uncomment to activate Firebase uploading
        send_to_firebase(turb_status, location, severity_status, avg_depth)
        
        for _ in range(50):
            if settings_requested:
                break 
            time.sleep(0.1)

# Start execution
if __name__ == "__main__":
    main()