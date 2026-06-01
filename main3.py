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
import urequests
import sh1106

# configuration
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
my_gps = MicropyGPS(8, 'dd')

i2c = I2C(0, scl=Pin(22), sda=Pin(21))
oled = sh1106.SH1106_I2C(128, 64, i2c)

# Parameter
DEVICE_ID = "SENSOR_001"  # Unique identifier for this device
sensor_height = 100.0 # Default sensor installation height from ground (cm)

# Function blocks

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

def get_gps_data():
    try:
        while gps_uart.any():
            data = gps_uart.read()
            for byte in data:
                stat = my_gps.update(chr(byte))
    except Exception as e:
        print(f"An error occurred: {e}")



def main():
    global sensor_height

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
            get_gps_data()

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
            print(f"[LONGITUDE] {my_gps.longitude_string()}")
            print(f"[LATITUDE] {my_gps.latitude_string()}")
            print(f"[SEVERITY] Level: {severity_status}")
            print(f"[SYSTEM] Time: {my_gps.timestamp}")
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
            
            sleep(5)

if __name__ == "__main__":
    main()