"""
App.py - Core Middleware for the Collateral Risk Oracle

This script serves as the primary execution layer running on the Raspberry Pi.
It performs two main functions simultaneously:
1. Runs a background daemon thread to continuously monitor the physical weight sensor.
2. Serves a Flask web dashboard to display real-time and on-chain metrics to users.
"""

from flask import Flask, render_template, jsonify
import threading
import time

# Custom module imports for hardware interaction and blockchain communication
from weight import get_weight_once, tare
from proof import capture_image, build_proof
from chain import submit_weight, get_contract_state

app = Flask(__name__)

# === CONFIGURATION & THRESHOLDS ===
# REPORT_THRESHOLD: Minimum weight change (in grams) required to trigger a blockchain update.
# This prevents spending gas fees on minor environmental micro-fluctuations.
REPORT_THRESHOLD = 8.0 

# STABILITY_CHECKS: Number of consecutive readings needed to confirm a real weight drop.
# STABILITY_DELAY: Time (in seconds) between stability checks.
STABILITY_CHECKS = 3
STABILITY_DELAY = 0.2

# COOLDOWN: Minimum time (in seconds) between blockchain submissions to prevent spamming.
COOLDOWN = 10

# CHECK_INTERVAL: How often the sensor is polled in the main loop (in seconds).
CHECK_INTERVAL = 0.5

# === GLOBAL STATE ===
last_reported_weight = None
last_report_time = 0

# Dictionary holding the latest telemetry and on-chain data to serve to the frontend UI
latest = {
    "pledged": 0,
    "current": 0,
    "onchain_weight": 0,
    "ratio": 0,
    "state": "ACTIVE",
    "proof": None,
    "proof_hash": None,
    "tx_hash": None,
}

def monitor_loop():
    """
    Asynchronous background loop that continuously monitors physical weight.
    If a significant, stable decrease in weight is detected, it triggers the 
    Oracle reporting process (image capture, proof generation, and blockchain submission).
    """
    global last_reported_weight, last_report_time

    while True:
        time.sleep(CHECK_INTERVAL)

        # Fetch sanitized reading from the HX711 analog-to-digital converter
        current = get_weight_once()
        if current is None:
            print("Sensor read failed or returned None")
            continue

        # Update the live state for the frontend dashboard
        latest["current"] = current
        print(f"Live Sensor Reading: {current}g")

        # Initialize the baseline on the first successful read
        if last_reported_weight is None:
            last_reported_weight = current
            continue

        # Calculate the change in weight
        delta = last_reported_weight - current

        # ASYMMETRIC LOGIC: Handle weight addition
        # If weight is added (negative delta), we silently update the local baseline 
        # to prevent unauthorized weight from artificially inflating the collateral health.
        if delta < -REPORT_THRESHOLD:
            last_reported_weight = current

        # HANDLE WEIGHT REMOVAL: Trigger off-chain reporting if a significant decrease is detected
        elif delta > REPORT_THRESHOLD:
            # Perform stability checks to filter out environmental vibrations or temporary bounces
            confirmed = True
            for _ in range(STABILITY_CHECKS):
                time.sleep(STABILITY_DELAY)
                check = get_weight_once()
                if last_reported_weight - check <= REPORT_THRESHOLD:
                    confirmed = False
                    break

            # If the removal is confirmed and we are not in a cooldown period, report it
            if confirmed and (time.time() - last_report_time > COOLDOWN):
                
                # 1. Capture visual proof of the physical state
                img_path = capture_image()
                
                # 2. Build the JSON payload and compute the SHA-256 cryptographic hash
                proof, proof_hash = build_proof(img_path, current)

                # Update local state with proof details
                latest["proof"] = proof
                latest["proof_hash"] = proof_hash

                # 3. Submit the new weight and cryptographic hash to the Ethereum smart contract
                try:
                    tx_hash = submit_weight(current, proof_hash)
                    latest["tx_hash"] = tx_hash
                    last_report_time = time.time()
                except Exception as e:
                    print("Blockchain error:", e)

                # Update our local baseline to the new, lower weight
                last_reported_weight = current

# === FLASK WEB ROUTES ===

@app.route("/")
def index():
    """
    Serves the main dashboard HTML page.
    Fetches the official, globally recognized state from the Ethereum smart contract.
    """
    try:
        # Query the blockchain for the official state, pledged baseline, and current recognized weight
        state, pledged, onchain_weight = get_contract_state()
        
        # Map the integer state from Solidity enum to human-readable strings
        state_map = {0: "ACTIVE", 1: "FLAGGED_L1", 2: "FLAGGED_L2", 3: "FLAGGED_L3"}

        latest["state"] = state_map[state]
        latest["pledged"] = pledged
        latest["onchain_weight"] = onchain_weight

        # Calculate the official on-chain health ratio
        if pledged > 0:
            latest["ratio"] = round((onchain_weight / pledged) * 100, 2)

    except Exception as e:
        print("State fetch error:", e)

    return render_template("index.html", data=latest)


@app.route("/api/data")
def api_data():
    """
    API endpoint used by the frontend asynchronous polling mechanism 
    to update the UI in real-time without refreshing the page.
    """
    return jsonify(latest)


@app.route("/api/tare", methods=["POST"])
def api_tare():
    """
    API endpoint to manually zero-out (tare) the physical scale.
    """
    success = tare()
    if success:
        return jsonify({"status": "success", "message": "Scale zeroed successfully."})
    return jsonify({"status": "error", "message": "Failed to read sensor."}), 500


if __name__ == "__main__":
    # Start the hardware monitoring loop in a background daemon thread
    threading.Thread(target=monitor_loop, daemon=True).start()
    
    # Start the Flask web server
    app.run(host="0.0.0.0", port=5000)