from machine import Pin, ADC
import time

# --- Setup Analog Pin (A0) ---
# We use Pin 34, which is a dedicated input pin on the ESP32.
turbidity_analog = ADC(Pin(34))

# Set the ADC attenuation to read the full 0 to 3.3V range.
# Without this, the ESP32 caps its reading at about 1.0V.
turbidity_analog.atten(ADC.ATTN_11DB) 

# --- Setup Digital Pin (D0) ---
# Optional: Reads the threshold trigger (adjusted via the blue screw on the board)
turbidity_digital = Pin(32, Pin.IN)

print("Starting Turbidity Sensor Readings...")
print("-" * 35)

while True:
    # 1. Read the raw analog value (returns a number between 0 and 4095)
    raw_adc = turbidity_analog.read()
    
    # 2. Convert the raw value to an approximate voltage (0V to 3.3V)
    # Note: This represents the voltage *after* your voltage divider.
    voltage = raw_adc * (3.3 / 4095.0)
    
    # 3. Read the digital alert state
    # Usually, 1 (HIGH) means clear water, 0 (LOW) means it crossed the dirty threshold.
    is_dirty = turbidity_digital.value() == 0
    
    # 4. Print the formatted results to the console
    if is_dirty:
        alert_status = "⚠️ ALERT: Turbidity Threshold Exceeded!"
    else:
        alert_status = "✅ Normal (Clear)"

    print(f"Raw: {raw_adc:4d} | Volts: {voltage:.2f}V | Status: {alert_status}")
    
    # Wait 1 second before the next reading
    time.sleep(1)