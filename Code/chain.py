"""
chain.py - Web3 Integration and Smart Contract Bridge

This module acts as the communication layer between the off-chain Python middleware 
(Raspberry Pi) and the on-chain Ethereum smart contract (Sepolia Testnet).
It handles formatting physical data, cryptographic signing, and broadcasting 
transactions to the decentralized network.
"""

from web3 import Web3
import os

# === INFRASTRUCTURE CONFIGURATION ===
# RPC_URL connects the edge device to an Ethereum node via Alchemy.
# Note: In a production enterprise environment, the API key should also be an environment variable.
RPC_URL = "https://eth-sepolia.g.alchemy.com/v2/GTljbg2WyhcicYnMe0ZcB"

# PRIVATE_KEY is strictly loaded from the environment to maintain Operational Security (OpSec).
# This prevents credential leakage in source code repositories.
PRIVATE_KEY = os.getenv("PRIVATE_KEY")

# Checksum addresses ensure Ethereum handles the hex strings with correct casing to prevent routing errors.
ACCOUNT_ADDRESS = Web3.to_checksum_address("0x39fBABa1c7FE3cd8272ea1758Cd9aF3196c6De2c")
CONTRACT_ADDRESS = Web3.to_checksum_address("0x9554Fc3417eF54f67c1dC222aBc940361080BBfc")

# === APPLICATION BINARY INTERFACE (ABI) ===
# The ABI acts as the translation manual, telling Web3.py exactly how to encode 
# and decode data when interacting with the compiled Solidity contract.
ABI = [
    {
        "inputs": [
            {"internalType": "uint256", "name": "newWeight", "type": "uint256"},
            {"internalType": "bytes32", "name": "proofHash", "type": "bytes32"}
        ],
        "name": "reportWeight",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "currentState",
        "outputs": [{"internalType": "uint8", "name": "", "type": "uint8"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "pledgedWeight",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "currentWeight",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function"
    }
]
    
# Initialize the Web3 connection provider
w3 = Web3(Web3.HTTPProvider(RPC_URL))

# Instantiate the contract object for interaction
contract = w3.eth.contract(
    address=Web3.to_checksum_address(CONTRACT_ADDRESS),
    abi=ABI
)


# === STATE-CHANGING OPERATIONS (WRITES) ===

def submit_weight(weight, proof_hash):
    """
    Submits the new physical weight and the visual proof hash to the blockchain.
    This is a state-changing transaction that incurs EVM gas fees.
    """
    # Sanitize the input to ensure we don't send negative weights or floats to Solidity's uint256
    safe_weight = max(0, int(weight))
    
    # Convert the standard string hash into a 32-byte format required by the smart contract
    proof_bytes32 = Web3.to_bytes(hexstr="0x" + proof_hash)
    
    # Fetch the current transaction count (nonce) to prevent replay attacks and sequencing errors
    nonce = w3.eth.get_transaction_count(ACCOUNT_ADDRESS)

    # Build the raw transaction payload
    tx = contract.functions.reportWeight(
        safe_weight,
        proof_bytes32
    ).build_transaction({
        "from": ACCOUNT_ADDRESS,
        "nonce": nonce,
        "gas": 300000,                           # Hard gas limit to prevent infinite execution loops
        "gasPrice": w3.to_wei("10", "gwei"),     # Set network fee 
        "chainId": 11155111                      # 11155111 is the official network ID for Sepolia Testnet
    })

    # Cryptographically sign the transaction using the edge device's private key
    signed_tx = w3.eth.account.sign_transaction(tx, PRIVATE_KEY)
    
    # Broadcast to the decentralized network's mempool
    tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
    
    # Return the human-readable transaction hash for the UI audit trail
    return w3.to_hex(tx_hash)


# === READ-ONLY OPERATIONS (FREE API CALLS) ===

def get_contract_state():
    """
    Queries the current official state directly from the Ethereum ledger.
    Because these use .call(), they are read-only operations that cost zero gas.
    """
    state = contract.functions.currentState().call()
    pledged = contract.functions.pledgedWeight().call()
    current = contract.functions.currentWeight().call()
    
    return state, pledged, current

def get_event_history():
    """
    Queries the EVM transaction logs to build an immutable audit trail for the UI.
    Events are a highly efficient way to store historical state transitions on-chain.
    """
    try:
        # Create a filter to search the entire chain history for 'WeightReported' events
        event_filter = contract.events.WeightReported.create_filter(fromBlock='earliest')
        entries = event_filter.get_all_entries()
        
        history = []
        # Grab only the 5 most recent events to prevent overloading the frontend memory
        for entry in entries[-5:]: 
            args = entry['args']
            history.append({
                "weight": args['weight'],
                "ratio": args['ratioPercent'],
                "state": args['state'], # Maps to Solidity Enum: 0=ACTIVE, 1=L1, 2=L2, 3=L3
                "tx_hash": Web3.to_hex(entry['transactionHash'])
            })
            
        # Reverse the list so the newest events appear at the top of the UI dashboard
        return list(reversed(history)) 
        
    except Exception as e:
        print("Error fetching history:", e)
        return []