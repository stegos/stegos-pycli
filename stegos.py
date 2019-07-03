#!/usr/bin/env python3

import asyncio
import base64
import binascii
import json
import sys
import websockets

from Crypto.Cipher import AES
from Crypto.Util import Counter
from Crypto import Random


key_bytes = 16


def encrypt(key, plaintext):
    assert len(key) == key_bytes

    # Choose a random, 16-byte IV.
    iv = Random.new().read(AES.block_size)

    # Convert the IV to a Python integer.
    iv_int = int(binascii.hexlify(iv), 16)

    # Create a new Counter object with IV = iv_int.
    ctr = Counter.new(AES.block_size * 8, initial_value=iv_int)

    # Create AES-CTR cipher.
    aes = AES.new(key, AES.MODE_CTR, counter=ctr)

    # Encrypt and return IV and ciphertext.
    ciphertext = aes.encrypt(plaintext)
    return iv+ciphertext


def decrypt(key, ciphertext):
    assert len(key) == key_bytes

    # Convert the IV to a Python integer.
    iv_int = int(binascii.hexlify(ciphertext[:16]), 16)

    # Create a new Counter object with IV = iv_int.
    ctr = Counter.new(AES.block_size * 8, initial_value=iv_int)

    # Create AES-CTR cipher.
    aes = AES.new(key, AES.MODE_CTR, counter=ctr)

    # Decrypt and return the plaintext.
    plaintext = aes.decrypt(ciphertext[16:])
    return plaintext


class StegosClient:
    id = 1

    def __init__(self, node_id='node01', uri='ws://localhost:3145', api_key='', wallet='', wallet_key=''):
        """ Create StegosClient object
        Attributes:
            node_id (String): used in the debug prints
            uri (String): WebSocket endpoint to connect to
            api_key (String): Encryption key for Websocket messages
            wallet (String): node's Wallet address (unused ATM)
            wallet_key (String): node's wallet key (used to decrypt key, stored on node)
        """
        self.prefix = node_id
        self.uri = uri
        self.api_key = base64.b64decode(api_key)
        self.wallet = wallet
        self.wallet_key = wallet_key
        self.websocket = None
        self.debug = True

    def next_id(self):
        self.id = self.id + 1
        return int(self.id)

    async def send_msg(self, msg):
        if self.websocket is None:
            return
        if self.debug:
            d = json.dumps(msg, indent=2)
            print(f"{self.prefix} Out: {d}")
        await self.websocket.send(str(base64.standard_b64encode(encrypt(self.api_key, json.dumps(msg))), "utf-8"))

    async def recv_msg(self):
        if self.websocket is None:
            return
        resp = await self.websocket.recv()
        resp = decrypt(self.api_key, base64.b64decode(resp))
        resp = json.loads(resp)
        if self.debug:
            d = json.dumps(resp, indent=2)
            print(f"{self.prefix} In: {d}")
        return resp

    async def connect(self):
        self.websocket = await websockets.connect(self.uri)

    async def wait_sync(self):
        waiting_sync = True
        while waiting_sync:
            resp = await self.recv_msg()
            if 'notification' in resp.keys() and resp['notification'] == 'sync_changed' and resp['is_synchronized']:
                waiting_sync = False
                print(f"{self.prefix} is synchronized!")

    async def get_balance(self):
        if self.websocket is None:
            return None
        req = {
            "request": "balance_info",
            "id": self.next_id(),
        }
        await self.send_msg(req)
        waiting_balance = True
        while waiting_balance:
            resp = await self.recv_msg()
            if 'id' in resp.keys() and resp['id'] == self.id and 'balance' in resp.keys():
                waiting_balance = False
        return resp['balance']

    async def payment_with_confitmation(self, address, amount):
        req = create_payment(address, amount, self.wallet_key)
        req['id'] = self.next_id()
        await self.send_msg(req)
        waiting_tx_hash = True
        while waiting_tx_hash:
            resp = await self.recv_msg()
            if 'id' in resp.keys() and resp['id'] == self.id and 'response' in resp.keys():
                tx_hash = resp['tx_hash']
                waiting_tx_hash = False

        print(f"tx_hash={tx_hash}")
        req = {
            'request': 'wait_for_commit',
            'tx_hash': tx_hash,
            'id': self.next_id(),
        }
        await self.send_msg(req)
        waiting_for_confirm = True
        while waiting_for_confirm:
            resp = await self.recv_msg()
            if 'id' in resp.keys() and resp['id'] == self.id and resp['response'] == 'transaction_committed' and resp['result'] == 'committed':
                waiting_for_confirm = False

        print(f"Commmited: {tx_hash}")

    async def secure_payment_with_confitmation(self, address, amount):
        req = create_secure_payment(address, amount, self.wallet_key)
        req['id'] = self.next_id()
        await self.send_msg(req)
        waiting_vs_start = True
        while waiting_vs_start:
            resp = await self.recv_msg()
            if 'id' in resp.keys() and resp['id'] == self.id and 'response' in resp.keys():
                if resp['response'] == 'value_shuffle_started':
                    vs_session_id = resp['session_id']
                    waiting_vs_start = False
                    print(
                        f"{self.prefix} In: ValueShuffle Session ID: {vs_session_id}")
                else:
                    print(f"{self.prefix} Failed to start ValueShuffle!")
                    sys.exit(-1)
        req = {
            'request': 'wait_for_commit',
            'tx_hash': vs_session_id,
            'id': self.next_id(),
        }
        await self.send_msg(req)
        waiting_for_confirm = True
        while waiting_for_confirm:
            resp = await self.recv_msg()
            if 'id' in resp.keys() and resp['id'] == self.id and resp['response'] == 'transaction_committed' and resp['result'] == 'committed':
                waiting_for_confirm = False
                print(f"{self.prefix} In: Transaction committed: {vs_session_id}")

# create dictionary with complete payment request


def create_payment(address, amount, password):
    req = {
        "request": "payment",
        "password": password,
        "payment_fee": 1_000,
        "recipient": address,
        "amount": amount * 1_000_000,
        "comment": "",
        "locked_timestamp": None,
        "with_certificate": False,
    }
    return req

# create dictionary with complete secure payment request


def create_secure_payment(address, amount, password):
    req = {
        "request": "secure_payment",
        "password": password,
        "payment_fee": 1_000,
        "recipient": address,
        "amount": amount * 1_000_000,
        "comment": "",
        "locked_timestamp": None,
    }
    return req
