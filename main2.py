from machine import UART, Pin
from ajsr04m import AJSR04M
from utime import sleep
import network
from micropyGPS import MicropyGPS
import urequests  # Required for HTTP requests

# --- CONFIGURATION ---
FIREBASE_URL = "https://flood-monitoring-fe2af-default-rtdb.asia-southeast1.firebasedatabase.app/vehicle_1.json"
# Replace with your actual Firebase URL. Keep the '/vehicle_1.json' at the end.

# --- PIN SETUP ---
LED_RED = Pin(14, Pin.OUT)
LED_YELLOW = Pin(13, Pin.OUT)
LED_GREEN = Pin(4, Pin.OUT)
TRIG1 = Pin(5, Pin.IN)
ECHO1 = Pin(18, Pin.IN)
TRIG2 = Pin(19, Pin.IN)
ECHO2 = Pin(23, Pin.IN)

flood_measure_front = AJSR04M(trigger_pin=TRIG1, echo_pin=ECHO1)
flood_measure_back = AJSR04M(trigger_pin=TRIG2, echo_pin=ECHO2)
gps_serial = UART(2, baudrate=9600, tx=17, rx=16)
my_gps = MicropyGPS()

# --- PARAMETERS ---
tolerance = 5.0
mount_height = 60.0
warn_level = 5.0
danger_level = 25.0

def set_leds(r, b, g):
    LED_RED.value(r)
    LED_BLUE.value(b)
    LED_GREEN.value(g)

def convert_to_decimal(degree_data):
    # micropyGPS returns [degrees, minutes, direction]
    # Decimal = Degrees + (Minutes / 60)
    if degree_data[0] == 0: return 0.0 # No lock yet
    
    decimal = degree_data[0] + (degree_data[1] / 60.0)
    if degree_data[2] == 'S' or degree_data[2] == 'W':
        decimal = -decimal
    return decimal

def send_to_firebase(depth, status, lat, lng):
    #   JSON format data
    data = {
        "depth_cm": depth,
        "status": status,
        "latitude": lat,
        "longitude": lng,
        "timestamp": { ".sv": "timestamp" }
    }
    try:
        #   Sends data to Firebase
        print("Sending to Firebase...")
        response = urequests.patch(FIREBASE_URL, json=data)
        response.close()
        print("Data sent!")
    except Exception as e:
        print("Firebase Error:", e)

# --- MAIN LOOP ---
while True:
    # 1. Read Sensors
    front_sensor = flood_measure_front.distance_cm()
    back_sensor = flood_measure_back.distance_cm()
    
    front_depth = mount_height - front_sensor
    back_depth = mount_height - back_sensor
    avg_depth = (front_depth + back_depth) / 2
    
    status_msg = "UNKNOWN"
    
    # 2. Process Flood Logic
    print(f"Front {front_sensor:.2f}cm | Back {back_sensor:.2f}cm")
    print(f"Average {avg_depth:.2f}cm")

    if abs(front_sensor - back_sensor) <= tolerance:
        if avg_depth >= danger_level:
            status_msg = "DANGER"
            print(f">> STATUS: {status_msg}")
            set_leds(1, 0, 0)
        elif avg_depth >= warn_level:
            status_msg = "WARNING"
            print(f">> STATUS: {status_msg}")
            set_leds(0, 1, 0)
        else:
            status_msg = "SAFE"
            print(f">> STATUS: {status_msg}")
            set_leds(0, 0, 1)
    else:
        status_msg = "INVALID"
        print(">> STATUS: INVALID (Mismatch)")

    # 3. Process GPS
    # We read all available characters from GPS to update the object
    while gps_serial.any():
        data = gps_serial.read()
        for byte in data:
            my_gps.update(chr(byte))

    # Convert GPS data for the web
    current_lat = convert_to_decimal(my_gps.latitude)
    current_lng = convert_to_decimal(my_gps.longitude)

    # 4. Send to Cloud
    # Only send if we have a valid WiFi connection
    send_to_firebase(avg_depth, status_msg, current_lat, current_lng)
    
    sleep(5)