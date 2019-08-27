# Stegos WebSocket API Python client example (WIP)

## *Disclaimer*

:bangbang: Code is provided as is and corresponds to API implemmented in Stegos Node for Mainnet Beta (as of Aug 26, 2019).

## Setup

Requirements:

* Python 3.7+
* asyncio

Its recommended to setup Python virtual environment like this:

```bash
bash> python -m venv ./client
bash> source ./client/bin/activate
bash> pip install -U -r requirements.txt
```

Provided examples assume we are running 7-node blockchain on `localhost`.

Instructions on running cluster are provided in `README-Testing.md` in the root of Stegos main repo.

On the first cluster run, nodes will create `api_token.txt` file with encryption key, used in all WebSocket communications.

## Files

* sample.json - example of nodes configurations used to setup WebSocket clients
* stegos.py - Module which defines StegosClient class, implementing Websocket Stegos API
* balance.py - example get balance script
* payout.py - create payments to nodes in the local cluster
* list_accounts.py - List existing accounts on the nodes and store updated nodes info
* create_accounts.py - create additional accounts on the nodes
* simplecannon.py - Generate regular payments betweeen nodes in round-robin fashion
* megacannon.py - Generate Snowball payments betweeen nodes in round-robin fashion
