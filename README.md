# Stegos WebSocket API Python client example (WIP)

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

* stegos.py - Module which defines StegosClient class, implementing Websocket Stegos API
* balance.py - example get balance script
* payout.py - create payments to 3 last nodes in the local cluster
