"""
ACC.py - Ethereum Account Utility Script

This is a standalone local utility script used during the setup phase of the 
hardware oracle. It mathematically derives the public Ethereum wallet address 
from a raw private key. 

In this project, the Raspberry Pi needs a specific public address to be funded 
with Sepolia Testnet ETH so it can pay for "gas fees" when submitting weight data.
"""

from web3 import Web3
from eth_account import Account

# === SECURITY WARNING ===
# This script is strictly for local, offline testing and configuration. 
# For the main application (chain.py), the private key is loaded securely { The private key has been withheld from the code to ensure compliance with data privacy constraints} 
# via environment variables to maintain strict Operational Security (OpSec).
PRIVATE_KEY = ""

# Derive the cryptographic account object locally from the raw private key string.
# This process utilizes the Elliptic Curve Digital Signature Algorithm (ECDSA) 
# and happens entirely offline—it does not require an RPC connection to the blockchain.
acct = Account.from_key(PRIVATE_KEY)

# Print the derived public wallet address.
# This is the string you will copy into your chain.py file as the 'ACCOUNT_ADDRESS',
# and the address you will send Sepolia Testnet ETH to from a faucet.
print("Derived Public Address:", acct.address)