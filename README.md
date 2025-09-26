# Ticket Blockchain Demo

A simple blockchain-based event ticketing system implemented in Python.

## Features
- Issue, transfer, and redeem event tickets
- Verify ticket ownership and validity
- Blockchain ledger with proof-of-work
- ECDSA digital signatures for authenticity
- JSON-based persistence (`chain_store.json`)
- REST API (Flask)

## Installation
```bash
git clone <your-repo-url>
cd ticket-blockchain
pip install flask ecdsa
