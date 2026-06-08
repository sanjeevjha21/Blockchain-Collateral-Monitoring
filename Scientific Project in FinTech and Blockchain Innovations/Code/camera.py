"""
camera.py - Visual Proof Generation Module

This script handles the hardware integration with the Raspberry Pi Camera Module.
In a trustless oracle architecture, raw data (weight) can be spoofed by physical tampering.
This module mitigates that risk by capturing real-time visual evidence ("proof of reserve") 
the exact moment a significant weight drop is detected by the off-chain middleware.
"""

import time
import subprocess
from pathlib import Path

# === CONFIGURATION ===
# Define the local directory where visual evidence will be stored.
# In a production environment, these images would later be pinned to IPFS.
IMAGES_DIR = Path("static/images")

# Ensure the storage directory exists on startup. If it doesn't, create it.
IMAGES_DIR.mkdir(parents=True, exist_ok=True)

def capture_image():
    """
    Triggers the Raspberry Pi camera to take a high-resolution photo.
    
    Returns:
        str: The relative file path of the newly captured image.
    """
    # Generate a unique Unix timestamp to serve as the file identifier
    ts = int(time.time())
    filename = IMAGES_DIR / f"asset_{ts}.jpg"

    # Execute the native Raspberry Pi OS camera command (libcamera-still).
    # -t 1000: Gives the camera sensor 1000 milliseconds (1 second) to warm up 
    #          and adjust auto-exposure/white balance before capturing.
    # -o: Specifies the output file path.
    cmd = ["rpicam-still", "-t", "1000", "-o", str(filename)]
    
    # Run the command via the operating system. 
    # check=True ensures that if the camera hardware fails or is disconnected, 
    # the script will throw a Python exception rather than failing silently.
    subprocess.run(cmd, check=True)

    # Return the path string so the main App.py middleware can bundle it into the JSON proof
    return str(filename)