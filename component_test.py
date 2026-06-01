from machine import Pin, ADC, I2C, UART, time_pulse_us
from micropyGPS import MicropyGPS
import time
import sh1106

# ==========================================
# 1. HARDWARE INITIALIZATION
# ==========================================

# --- LEDs ---
led1 = Pin(4, Pin.OUT)
led2 = Pin(13, Pin.OUT)
led3 = Pin(14, Pin.OUT)

# --- Buttons ---
# 1 = unpressed (UP), 0 = pressed (DOWN)
btn1 = Pin(25, Pin.IN, Pin.PULL_UP)
btn2 = Pin(26, Pin.IN, Pin.PULL_UP)
btn3 = Pin(27, Pin.IN, Pin.PULL_UP)
btn4 = Pin(33, Pin.IN, Pin.PULL_UP)

# --- Turbidity Sensor ---
turbidity = ADC(Pin(32))
turbidity.atten(ADC.ATTN_11DB)
# CALIBRATION: Change this number to the ADC value you get in clean water!
CLEAN_WATER_BASELINE = 3000 

# --- Ultrasonic Sensors ---
trig1 = Pin(5, Pin.OUT)
echo1 = Pin(18, Pin.IN)
trig2 = Pin(19, Pin.OUT)
echo2 = Pin(23, Pin.IN)

def read_distance(trig, echo):
    trig.value(0)
    time.sleep_us(2)
    trig.value(1)
    time.sleep_us(10)
    trig.value(0)
    try:
        pulse_time = time_pulse_us(echo, 1, 30000)
        if pulse_time > 0:
            return round((pulse_time / 2) / 29.1, 1)
        return -1
    except OSError:
        return -1

# --- GPS & Parser ---
gps_serial = UART(2, baudrate=9600, rx=16, tx=17)
my_gps = MicropyGPS(local_offset=8, location_formatting='dd')

# --- OLED ---
i2c = I2C(0, scl=Pin(22), sda=Pin(21))
try:
    oled = sh1106.SH1106_I2C(128, 64, i2c)
    oled_available = True
except OSError:
    print("OLED not found!")
    oled_available = False

# ==========================================
# 2. HELPER FORMATTING FUNCTIONS
# ==========================================
def get_btn_state(btn):
    return "PRESSED" if btn.value() == 0 else "UP     "

def get_sonar_state(dist):
    return f"{dist} cm" if dist != -1 else "Out of Range"

# ==========================================
# 3. MAIN LOOP
# ==========================================
print("Starting Dashboard...")
last_print_time = time.ticks_ms()

while True:
    # --- Rapidly process GPS Serial Data ---
    if gps_serial.any():
        try:
            raw_data = gps_serial.read().decode('ascii')
            for char in raw_data:
                my_gps.update(char)
        except Exception:
            pass

    # --- Update Sensors & Display Every 1 Second ---
    if time.ticks_diff(time.ticks_ms(), last_print_time) >= 1000:
        last_print_time = time.ticks_ms()

        # Update LEDs
        led1.value(not btn1.value())
        led2.value(not btn2.value())
        led3.value(not btn3.value())
        
        # Calculate Turbidity
        turb_adc = turbidity.read()
        turb_volts = (turb_adc / 4095.0) * 3.3
        if turb_adc >= CLEAN_WATER_BASELINE:
            turb_percent = 0.0
        else:
            turb_percent = 100.0 - ((turb_adc / CLEAN_WATER_BASELINE) * 100.0)

        # Read Ultrasonics
        d1 = read_distance(trig1, echo1)
        d2 = read_distance(trig2, echo2)

        # Process GPS
        lat_val = -my_gps.latitude[0] if my_gps.latitude[1] == 'S' else my_gps.latitude[0]
        lon_val = -my_gps.longitude[0] if my_gps.longitude[1] == 'W' else my_gps.longitude[0]
        has_fix = lat_val != 0.0 or lon_val != 0.0

        # ==========================================
        # PRINT TO CONSOLE (REPL DASHBOARD)
        # ==========================================
        print("\n" + "="*45)
        print(" ESP32 SENSOR DASHBOARD")
        print("="*45)
        
        print(f"[ BUTTONS ] B1: {get_btn_state(btn1)} | B2: {get_btn_state(btn2)}")
        print(f"            B3: {get_btn_state(btn3)} | B4: {get_btn_state(btn4)}")
        print("-" * 45)
        
        print(f"[ WATER   ] ADC: {turb_adc} ({turb_volts:.2f}V)")
        print(f"            Cloudiness: {turb_percent:.1f}%")
        print("-" * 45)
        
        print(f"[ SONAR   ] S1: {get_sonar_state(d1)}")
        print(f"            S2: {get_sonar_state(d2)}")
        print("-" * 45)
        
        if has_fix:
            print(f"[ GPS     ] Status: LOCKED ({my_gps.satellites_in_use} Sats Used)")
            print(f"            Lat: {lat_val:.5f} | Lon: {lon_val:.5f}")
            print(f"            Time: {my_gps.timestamp[0]:02d}:{my_gps.timestamp[1]:02d}:{int(my_gps.timestamp[2]):02d}")
        else:
            print(f"[ GPS     ] Status: SEARCHING... ")
            print(f"            Satellites in View: {my_gps.satellites_in_view}")
        print("="*45)

        # ==========================================
        # PRINT TO OLED
        # ==========================================
        if oled_available:
            oled.fill(0) 
            # Top row: Turbidity
            oled.text(f"Dirt: {turb_percent:.0f}%", 0, 0)
            
            # Second row: Sonar
            s1_txt = str(d1) if d1 != -1 else "---"
            s2_txt = str(d2) if d2 != -1 else "---"
            oled.text(f"D1:{s1_txt} D2:{s2_txt}", 0, 14)
            
            # Third row: Buttons (Using simple 0/1 for space saving on screen)
            oled.text(f"Btns: {not btn1.value()}{not btn2.value()}{not btn3.value()}{not btn4.value()}", 0, 28)
            
            # Bottom rows: GPS
            if has_fix:
                oled.text(f"Lat:{lat_val:.4f}", 0, 44)
                oled.text(f"Lon:{lon_val:.4f}", 0, 54)
            else:
                oled.text(f"GPS: Search({my_gps.satellites_in_view})", 0, 48)
                
            oled.show()