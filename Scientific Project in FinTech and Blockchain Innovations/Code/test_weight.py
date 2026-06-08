"""
test_weight.py - HX711 Hardware Calibration Utility

This standalone script is used to configure the physical load cell before 
deploying the main oracle middleware. Because every physical piece of metal 
(load cell) bends slightly differently under mechanical stress, the system 
must be mathematically calibrated to translate raw analog-to-digital 
outputs into human-readable metric mass (grams).
"""

import time
import sys
from hx711 import HX711
import RPi.GPIO as GPIO

# === HARDWARE PIN CONFIGURATION ===
# Ensure these match the actual physical wiring to the Raspberry Pi GPIO headers
DT = 5
SCK = 6

def clean_and_exit():
    """Safely closes the GPIO pins to prevent electrical shorts or locked resources upon exit."""
    print("Cleaning up...")
    GPIO.cleanup()
    sys.exit()

try:
    # Initialize the Analog-to-Digital Converter
    hx = HX711(DT, SCK)
    hx.reset()
    hx.power_up()
    
    print("========================================")
    print("   HX711 Calibration Utility")
    print("========================================")
    
    # === STEP 1: ESTABLISH THE ZERO OFFSET (TARE) ===
    # This step calculates the baseline electrical resistance when the scale is completely empty.
    print("\n[STEP 1] Empty the scale completely.")
    input("Press ENTER to continue when the scale is empty...")
    
    print("Reading zero offset... please wait.")
    time.sleep(2) # Give the physical strain gauges a moment to settle
    
    # Take a burst of 20 raw readings to average out minor environmental vibrations
    zero_readings = []
    for _ in range(20):
        val = hx.get_raw_data()
        if val:
            # Handle cases where the library returns a list of channel data
            if isinstance(val, list):
                val = sum(val) / len(val)
            zero_readings.append(val)
        time.sleep(0.05)
        
    if not zero_readings:
        print("Error: Could not read from sensor. Check wiring.")
        clean_and_exit()
        
    # Average the readings to establish the permanent baseline
    zero_offset = sum(zero_readings) / len(zero_readings)
    print(f"-> ZERO_OFFSET calculated: {zero_offset}")
    
    
    # === STEP 2: CALCULATE THE CALIBRATION FACTOR (SCALAR) ===
    # This step determines how much the raw integer changes per actual gram of physical weight.
    print("\n[STEP 2] Place a KNOWN WEIGHT on the scale.")
    print("For best results, use a precision calibration weight (e.g., 100g or 200g).")
    known_weight_str = input("Enter the weight in grams (e.g., 100) and press ENTER: ")
    
    try:
        known_weight = float(known_weight_str)
    except ValueError:
        print("Invalid weight entered. Please run the script again.")
        clean_and_exit()
        
    print(f"Reading weight of {known_weight}g... please wait.")
    time.sleep(2) # Allow the scale to physically settle under the new mass
    
    # Take another burst of 20 raw readings with the weight applied
    weight_readings = []
    for _ in range(20):
        val = hx.get_raw_data()
        if val:
            if isinstance(val, list):
                val = sum(val) / len(val)
            weight_readings.append(val)
        time.sleep(0.05)
        
    raw_with_weight = sum(weight_readings) / len(weight_readings)
    print(f"-> Raw value with weight: {raw_with_weight}")
    
    # Apply the fundamental calibration formula: C = (Raw - Zero) / Known_Mass
    calibration_factor = (raw_with_weight - zero_offset) / known_weight
    
    # === STEP 3: OUTPUT RESULTS ===
    # These values must be manually pasted into the main weight.py execution script
    print("\n========================================")
    print("   CALIBRATION COMPLETE")
    print("========================================")
    print("Open your 'weight.py' file and update the variables to:")
    print(f"\nZERO_OFFSET = {zero_offset:.2f}")
    print(f"CALIBRATION_FACTOR = {calibration_factor:.2f}\n")
    
except (KeyboardInterrupt, SystemExit):
    clean_and_exit()
finally:
    # Ensure hardware resources are safely released even if an error occurs
    GPIO.cleanup()