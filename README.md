# High-Value Asset Risk Oracle

A hardware-anchored collateral monitoring system that bridges physical assets to the Ethereum blockchain in real time. Built to eliminate the vulnerability window created by periodic human audits in asset-based lending.

---

## How It Works

A Raspberry Pi continuously weighs physical collateral using a precision load cell. The moment an unauthorized weight drop is detected, the system captures a timestamped photo, hashes the evidence using SHA-256, and submits it to an Ethereum smart contract. The contract automatically evaluates the Loan-to-Value (LTV) ratio and escalates the risk state — no human intervention required.


Physical Weight Drop → Visual Proof Captured → SHA-256 Hash → Ethereum Smart Contract → Dashboard Alert


---

## Features

- **Real-time IoT monitoring** — load cell polled every 0.5 seconds with burst-sampling noise filtering
- **Sensor-triggered camera** — photo captured the instant a significant weight change is confirmed
- **On-chain risk escalation** — smart contract deterministically transitions between `ACTIVE`, `FLAGGED_L1`, `FLAGGED_L2`, and `FLAGGED_L3` states
- **Cryptographic proof of reserve** — SHA-256 hash of weight + photo bundle permanently anchored to the blockchain
- **Flask web dashboard** — dual-state view showing live sensor telemetry alongside the official on-chain record

---

## Tech Stack

| Layer | Technology |
|---|---|
| Edge Device | Raspberry Pi 4 |
| Weight Sensor | 5 kg Load Cell + HX711 ADC |
| Camera | Raspberry Pi Camera Module |
| Middleware | Python 3, Flask, Web3.py |
| Blockchain | Solidity `^0.8.20`, Ethereum Sepolia Testnet |
| Frontend | HTML, CSS, JavaScript |

---

## Repository Structure


├── App.py              # Main entry point — sensor loop + Flask dashboard server
├── camera.py           # Captures timestamped visual proof on weight drop
├── weight.py           # HX711 interface — raw ADC → grams conversion with noise filtering
├── chain.py            # Web3.py bridge — signs and submits transactions to Sepolia
├── proof.py            # Builds the JSON evidence payload and computes SHA-256 hash
├── ACC.py              # Local utility — derives Ethereum public address from private key
├── test_weight.py      # Interactive calibration script for the load cell
├── Contract.sol        # Solidity smart contract (CollateralMonitor)
├── requirements.txt    # Python dependencies
└── static/
    └── images/         # Auto-generated — stores visual proof JPEGs


---

## Getting Started

### Prerequisites

- Raspberry Pi 4 running Raspberry Pi OS
- Python 3.9+
- Hardware: 5 kg Load Cell, HX711 module, Raspberry Pi Camera Module
- A wallet funded with Sepolia Testnet ETH ([faucet](https://sepoliafaucet.com/))
- An Ethereum RPC endpoint ([Infura](https://infura.io/) or [Alchemy](https://www.alchemy.com/))

---

### 1. Clone and Install

bash
git clone https://github.com/your-username/your-repo-name.git
cd your-repo-name
pip3 install -r requirements.txt


---

### 2. Wire the Hardware

| Component | Raspberry Pi GPIO |
|---|---|
| HX711 Data (DT) | GPIO 5 |
| HX711 Clock (SCK) | GPIO 6 |
| Load Cell | HX711 input terminals |
| Camera Module | CSI port |

Enable the camera via `raspi-config` → Interface Options → Camera.

---

### 3. Calibrate the Load Cell

Every physical load cell must be calibrated before use. Run the interactive utility:

bash
python3 test_weight.py


Follow the prompts — place a known weight when asked. Copy the two output values into `weight.py`:

python
ZERO_OFFSET = 0.0         # Replace with your output
CALIBRATION_FACTOR = 0.0  # Replace with your output


---

### 4. Deploy the Smart Contract

1. Open [Remix IDE](https://remix.ethereum.org/) and paste the contents of `Contract.sol`
2. Compile with Solidity `^0.8.20`
3. Deploy to **Sepolia Testnet** via MetaMask — pass the pledged baseline weight in grams to the constructor (e.g., `1000` for 1 kg)
4. Copy the deployed contract address for the next step

---

### 5. Configure Environment Variables

> ⚠️ **Never hardcode secrets in source code.** All sensitive values must be set as environment variables.

bash
export PRIVATE_KEY="your_wallet_private_key"
export CONTRACT_ADDRESS="your_deployed_contract_address"
export RPC_URL="https://sepolia.infura.io/v3/your_project_id"


To persist across reboots, add these lines to `~/.bashrc`.

---

### 6. Run

bash
python3 App.py


Access the dashboard at `http://localhost:5000` or `http://<raspberry-pi-ip>:5000` from any device on the network.

---

## Dashboard

| Panel | Description |
|---|---|
| Live Sensor Weight | Current physical reading from the load cell |
| On-Chain Weight | Last weight officially recorded on Ethereum |
| Collateral Ratio | Live LTV health percentage |
| Contract State | Current risk level |
| Proof Hash | SHA-256 hash of the latest evidence bundle |
| Transaction Hash | Ethereum tx ID for the last on-chain submission |

### API Endpoints

| Method | Route | Description |
|---|---|---|
| `GET` | `/` | Main dashboard |
| `GET` | `/api/data` | JSON telemetry — used by frontend polling |
| `POST` | `/api/tare` | Zero out the scale |

---

## Smart Contract

**`CollateralMonitor.sol`** is deployed on the Ethereum Sepolia Testnet.

### Risk State Thresholds

| Collateral Ratio | State |
|---|---|
| ≥ 75% | `ACTIVE` |
| 50% – 74% | `FLAGGED_L1` |
| 25% – 49% | `FLAGGED_L2` |
| < 25% | `FLAGGED_L3` |

### Key Functions

solidity
constructor(uint256 _pledgedWeight)
// Sets the baseline weight on deployment

reportWeight(uint256 newWeight, bytes32 proofHash) external
// Called by the oracle — updates weight, recalculates LTV, transitions state, emits event


---

## Security

- All secrets (`PRIVATE_KEY`, `CONTRACT_ADDRESS`, `RPC_URL`) are loaded exclusively from environment variables — never from source code
- `ACC.py` is a local offline utility for deriving your public address during setup only — clear any key from it after use
- A configurable `REPORT_THRESHOLD` (default `8g`) prevents micro-fluctuations from triggering unnecessary on-chain transactions
- A `COOLDOWN` period (default `10s`) prevents transaction spam


