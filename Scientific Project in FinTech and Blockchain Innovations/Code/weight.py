"""
weight.py - Physical Telemetry and Signal Processing Layer

This module manages the direct hardware interface between the Raspberry Pi 
and the 1 kg Load Cell via the HX711 Analog-to-Digital Converter (ADC).
It is responsible for acquiring raw electrical signals, mitigating environmental 
noise through statistical filtering, and computing the final deterministic mass in grams.
"""

import time
from hx711 import HX711
import RPi.GPIO as GPIO

# === HARDWARE PIN CONFIGURATION ===
# DT (Data) and SCK (Serial Clock) pins connecting the HX711 chip to the Raspberry Pi GPIO
DT = 5
SCK = 6

# Initialize the HX711 hardware interface
hx = HX711(DT, SCK)
hx.reset()
hx.power_up()

# === CALIBRATION CONSTANTS ===
# ZERO_OFFSET: The raw digital baseline when the scale is completely empty (tare weight).
# CALIBRATION_FACTOR: The mathematical scalar used to convert the raw digital integer 
#                     from the Wheatstone bridge into a human-readable metric (grams).
# ⚠ Note: These values are strictly specific to the physical load cell used in this deployment.
ZERO_OFFSET = -179526.23
CALIBRATION_FACTOR = 316.41


def read_raw(samples=20):
    """
    Acquires a batch of raw digital readings from the HX711 and applies a 
    localized data sanitization algorithm to filter out environmental noise.
    
    In a warehouse environment, vibrations or thermal drift can cause sudden spikes. 
    This function takes multiple samples, sorts them, and mathematically trims 
    the upper and lower bounds (outliers) before averaging the stable core data.
    """
    vals = []
    
    # 1. Burst Sampling: Quickly gather a set of raw data points
    for _ in range(samples):
        v = hx.get_raw_data()
        if v is None:
            continue
            
        # Handle cases where the HX711 library returns a list of channel readings
        if isinstance(v, list):
            v = sum(v) / len(v)
            
        vals.append(v)
        time.sleep(0.005) # Micro-pause to allow the ADC hardware to cycle

    # If the sensor is disconnected or failing, abort safely
    if not vals:
        return None

    # 2. Outlier Mitigation: Sort the list and calculate the trim amount (top and bottom 20%)
    vals.sort()
    trim_amount = len(vals) // 5 
    
    # Slice off the extreme highs and lows (e.g., machinery vibrations)
    if trim_amount > 0:
        vals = vals[trim_amount:-trim_amount]

    # 3. Deterministic Averaging: Return the highly sanitized baseline
    return sum(vals) / len(vals)


def get_weight_once():
    """
    Executes the signal processing pipeline and applies the calibration formula 
    to return the physical mass.
    
    Formula: W = (V_raw - V_offset) / C_factor
    
    Returns:
        float: The final computed collateral weight in grams (rounded to 2 decimals).
    """
    raw = read_raw()
    
    if raw is None:
        return None
        
    # Apply the calibration math to convert digital voltage differentials into grams
    grams = (raw - ZERO_OFFSET) / CALIBRATION_FACTOR
    
    return round(grams, 2)


def tare():
    """
    Dynamically resets the physical baseline of the scale.
    This zeroing function allows the system to account for the weight of 
    empty pallets or storage containers before the actual collateral is pledged.
    
    Returns:
        bool: True if the tare operation was successful, False otherwise.
    """
    global ZERO_OFFSET
    
    # Take a highly sanitized reading to establish the new zero point
    raw = read_raw(samples=20)
    
    if raw is not None:
        ZERO_OFFSET = raw
        return True
        
    return False