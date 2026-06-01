from machine import ADC, Pin
import time

# === Configuration ===
TURBIDITY_PIN = 34  # Use an ADC-capable pin on ESP32
ADC_ATTEN = ADC.ATTN_11DB  # Full range: 0 - 3.3V
ADC_WIDTH = ADC.WIDTH_12BIT  # 0 - 4095 resolution
VREF = 3.3  # ESP32 ADC reference voltage

# === Initialize ADC ===
adc = ADC(Pin(TURBIDITY_PIN))
adc.atten(ADC_ATTEN)
adc.width(ADC_WIDTH)

def read_voltage():
    """Read sensor voltage from ADC."""
    raw = adc.read()
    voltage = (raw / 4095) * VREF
    return voltage

def voltage_to_ntu(voltage):
    """
    Linear calibration for ESP32.
    Replace V_CLEAR and V_MUDDY with the actual voltages you measured!
    """
    V_CLEAR = 2.8  # The voltage you measured in clean water
    V_MUDDY = 1.5  # The voltage you measured in highly turbid water
    
    # If water is cleaner than our baseline, return 0
    if voltage >= V_CLEAR:
        return 0.0
    # If water is dirtier than our baseline, return max NTU (e.g., 3000)
    elif voltage <= V_MUDDY:
        return 3000.0
    else:
        # Linearly map the voltage between 0 and 3000 NTU
        ntu = (V_CLEAR - voltage) / (V_CLEAR - V_MUDDY) * 3000.0
        return ntu

# === Main Loop ===
try:
    while True:
        voltage = read_voltage()
        ntu = voltage_to_ntu(voltage)
        print("Voltage: {:.2f} V | Turbidity: {:.2f} NTU".format(voltage, ntu))
        time.sleep(1)

except KeyboardInterrupt:
    print("Measurement stopped.")
