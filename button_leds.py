from machine import Pin
import time

# Initialize LEDs as output pins
led1 = Pin(4, Pin.OUT)
led2 = Pin(13, Pin.OUT)
led3 = Pin(14, Pin.OUT)

# Initialize Buttons as input pins with internal pull-up resistors
btn1 = Pin(26, Pin.IN, Pin.PULL_UP)
btn2 = Pin(27, Pin.IN, Pin.PULL_UP)
btn3 = Pin(33, Pin.IN, Pin.PULL_UP)

print("ESP32 Button and LED Test Started...")
print("Press a button to light up its corresponding LED. Press Ctrl+C to stop.")

try:
    while True:
        # Read button states: 0 = pressed, 1 = not pressed
        # We invert the button state (not) to turn ON the LED when pressed
        led1.value(not btn1.value())
        led2.value(not btn2.value())
        led3.value(not btn3.value())
        
        # 50ms delay to act as simple software debounce and reduce CPU load
        time.sleep(0.05) 
        
except KeyboardInterrupt:
    # Turn off all LEDs when the script is stopped
    led1.value(0)
    led2.value(0)
    led3.value(0)
    print("\nTest stopped.")