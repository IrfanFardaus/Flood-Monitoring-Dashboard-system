import network
import time
import urequests
import json

# --- Configuration ---
WIFI_SSID = "MSI"
WIFI_PASSWORD = "hinge123"

# Pointing to a new node called "counter_test"
FIREBASE_URL = "https://flood-monitoring-fe2af-default-rtdb.asia-southeast1.firebasedatabase.app/counter_test.json"

# --- Connect to Wi-Fi ---
def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if not wlan.isconnected():
        print("Connecting to Wi-Fi...")
        wlan.connect(WIFI_SSID, WIFI_PASSWORD)
        
        timeout = 10
        while not wlan.isconnected() and timeout > 0:
            time.sleep(1)
            timeout -= 1
            
    if wlan.isconnected():
        print("Connected to Wi-Fi! IP:", wlan.ifconfig()[0])
        return True
    else:
        print("Failed to connect to Wi-Fi")
        return False

# --- Counter Logic ---
def run_counter_test(iterations=5):
    print("\nStarting Counter Test...")
    
    for i in range(iterations):
        print(f"\n--- Loop {i + 1} of {iterations} ---")
        
        # 1. Read the current count
        current_count = 0
        try:
            response = urequests.get(FIREBASE_URL)
            if response.status_code == 200:
                data = response.json()
                # Check if data exists and has our 'count' key
                if data and "count" in data:
                    current_count = data["count"]
            response.close()
        except Exception as e:
            print("Error reading from Firebase:", e)

        # 2. Increment the count
        new_count = current_count + 1
        print(f"Incrementing: {current_count} -> {new_count}")

        # 3. Write the new count back to Firebase
        payload = {"count": new_count}
        try:
            # We use PUT here to completely overwrite the 'counter_test' node
            response = urequests.put(FIREBASE_URL, json=payload)
            if response.status_code == 200:
                print("Firebase updated successfully!")
            else:
                print(f"Failed to update. Status Code: {response.status_code}")
            response.close()
        except Exception as e:
            print("Error writing to Firebase:", e)
            
        # Wait 3 seconds before the next loop to avoid spamming the database
        time.sleep(3)

# --- Main Execution ---
if connect_wifi():
    # Run the test 5 times
    run_counter_test(iterations=5)
    print("\nTest Complete!")