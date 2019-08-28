#!/usr/bin/env python3

import asyncio
import base64
import binascii
import json
import logging
import prometheus_client as prom
import sys
import time
import websockets

from Crypto.Cipher import AES
from Crypto.Util import Counter
from Crypto import Random


key_bytes = 16

SNOWBALL_TIMINGS = prom.Gauge(
    'snowball_duration', 'How long transaction took', ['account'])
SNOWBALL_COUNTS = prom.Counter('snowball_success_count',
                               'How many successful Snowball transactions processed', ['account'])


class StegosClient:
    id = 1

    def __init__(self, node_id='node01', uri='ws://localhost:3145', accounts={}, api_key='', master_key=''):
        """ Create StegosClient object
        Attributes:
            node_id (String): used in the debug logging.infos
            accounts: map account_id(Sting) -> account_address(String)
            uri (String): WebSocket endpoint to connect to
            api_key (String): Encryption key for Websocket messages
            master_key (String): node's wallets key (used to decrypt key, stored on node)
        """
        self.prefix = node_id + ' (Idle)'
        self.node_id = node_id
        self.uri = uri
        self.api_key = base64.b64decode(api_key)
        self.master_key = master_key
        self.accounts = accounts
        self.websocket = None
        self.debug = True
        self.pending_txs = {}
        self.balance = 0

    def next_id(self):
        self.id = self.id + 1
        return int(self.id)

    async def connect(self):
        backoff_timer = 5
        while True:
            try:
                self.websocket = await websockets.connect(self.uri, ping_timeout=None)
                break
            except Exception as e:
                logging.info(
                    F"Node: {self.node_id}, Connect Exceprion: {e}, Retrying in {backoff_timer} secs..")
                await asyncio.sleep(backoff_timer)
                backoff_timer = min(60, backoff_timer + 10)

    async def send_msg(self, msg):
        if self.websocket is None:
            return
        if self.debug:
            d = json.dumps(msg, indent=2)
            logging.info(f"{self.prefix} Out: {d}")
        await self.websocket.send(str(base64.standard_b64encode(encrypt(self.api_key, json.dumps(msg))), "utf-8"))

    async def recv_msg(self):
        if self.websocket is None:
            return
        resp = await self.websocket.recv()
        resp = decrypt(self.api_key, base64.b64decode(resp))
        resp = json.loads(resp)
        if resp['type'] == 'balance_changed' or resp['type'] == 'balance_info':
            self.balance = resp['balance']

        if self.debug:
            if resp['type'] in ['rollback_micro_block', 'new_micro_block']:
                pass
            else:
                if resp['type'] == 'sync_changed':
                    logging.info(
                        f"{self.prefix} In: epoch:{resp['epoch']}, offset:{resp['offset']}, synced:{resp['is_synchronized']}")
                else:
                    d = json.dumps(resp, indent=2)
                    logging.info(f"{self.prefix} In: {d}")
        return resp

    async def wait_sync(self):
        while True:
            resp = await self.recv_msg()
            if resp['type'] == 'sync_changed' and resp['is_synchronized']:
                logging.info(f"{self.prefix} is synchronized!")
                break

    async def list_accounts(self):
        if self.websocket is None:
            return None
        req = {
            "type": "list_accounts",
            "id": self.next_id(),
        }
        await self.send_msg(req)
        while True:
            resp = await self.recv_msg()
            if resp['type'] == 'accounts_info':
                return resp['accounts']

    async def get_address(self, account_id):
        if self.websocket is None:
            return None
        req = {
            "type": "account_info",
            "account_id": account_id,
            "id": self.next_id(),
        }
        await self.send_msg(req)
        while True:
            resp = await self.recv_msg()
            if resp['type'] == 'account_info':
                return resp['account_address']

    async def create_account(self):
        if self.websocket is None:
            return None
        req = {
            "type": "create_account",
            "password": self.master_key,
            "id": self.next_id(),
        }
        await self.send_msg(req)
        while True:
            resp = await self.recv_msg()
            if resp['type'] == 'account_created':
                account_id = resp['account_id']
                break

        address = await self.get_address(account_id)
        result = {
            "account_id": account_id,
            "account_address": address,
        }
        return result

    async def unseal(self, account_id):
        if self.websocket is None:
            return None
        req = {
            "type": "unseal",
            "account_id": account_id,
            "password": self.master_key,
            "id": self.next_id(),
        }
        await self.send_msg(req)
        while True:
            resp = await self.recv_msg()
            if resp['type'] == 'unsealed' and resp['id'] == self.id:
                result = True
                break
            if resp['type'] == 'error' and resp['id'] == self.id and resp['error'] == 'Already unsealed':
                result = True
                break
            if resp['type'] == 'error' and resp['id'] == self.id:
                result = False
                break

        # Wait for account to be synced
        while True:
            resp = await self.recv_msg()
            if resp['type'] == 'sync_changed':
                break

        return result

    async def get_balance(self, account_id):
        if self.websocket is None:
            return None
        req = {
            "type": "balance_info",
            "account_id": account_id,
            "id": self.next_id(),
        }
        await self.send_msg(req)
        while True:
            resp = await self.recv_msg()
            if resp['type'] == 'error' and resp['id'] == self.id and resp['error'] == 'Account is sealed':
                await self.unseal(account_id)
                req['id'] = self.next_id()
                await self.send_msg(req)
                continue
            if 'id' in resp.keys() and resp['id'] == self.id and 'balance_info' == resp['type']:
                return resp['balance']

    async def payment_with_confirmation(self, source, address, amount, comment='', use_certificate=False):
        """
        Create regular payment and wait for TX to be included in microblock
        source: account_id to be used for payment
        address: account_address of recipient
        amount: number of tokens
        """
        req = {
            "type": "payment",
            "account_id": source,
            "payment_fee": 1_000,
            "recipient": address,
            "amount": int(amount * 1_000_000),
            "comment": comment,
            "locked_timestamp": None,
            "with_certificate": use_certificate,
            "id": self.next_id(),
        }
        await self.send_msg(req)
        while True:
            self.prefix = self.node_id + " (waiting for tx creation)"
            resp = await self.recv_msg()
            if 'id' in resp.keys() and resp['id'] == self.id:
                if resp['type'] == 'transaction_created':
                    tx = {}
                    for o in resp['outputs']:
                        if o['recipient'] == address and o.get('rvalue', '0xdeadbeef') != '0xdeadbeef':
                            tx = {
                                'recipient': address,
                                'utxo': o['utxo'],
                                'amount': o['amount'],
                            }
                            if use_certificate:
                                tx['rvalue'] = o['rvalue']
                    tx_hash = resp['tx_hash']
                    break
                if resp['type'] == 'error':
                    result = {
                        "success": False,
                        "message": resp['error']
                    }
                    return result

        logging.info(f"tx_hash={tx_hash}")
        status = await self.wait_tx(tx_hash)
        self.prefix = self.node_id + "(Idle)"
        if status:
            logging.info(f"{self.prefix} tx: {tx_hash} included in microblock")
            result = {
                'success': True,
                'tx': tx
            }
            return result
        else:
            logging.info(f"{self.prefix} tx: {tx_hash} failed")
            result = {
                'success': False,
                'message': "Transaction failed!",
            }

    async def secure_payment_with_confirmation(self, source, address, amount):
        if self.balance <= amount:
            print(
                f"{self.prefix}]{source} balance is too low: balance={self.balance}, amount={amount}")
            sys.exit(-1)
        start_time = time.monotonic()
        req = {
            "type": "secure_payment",
            "account_id": source,
            "payment_fee": 1_000,
            "recipient": address,
            "amount": int(amount * 1_000_000),
            "comment": "",
            "locked_timestamp": None,
            "id": self.next_id(),
        }
        await self.send_msg(req)
        state = 'vs req sent'
        self.prefix = f"{self.node_id}[{source}] ({state})"
        while True:
            resp = await self.recv_msg()
            elapsed = time.monotonic() - start_time
            self.prefix = f"{self.node_id}[{source}] ({state}) elapsed: {elapsed}"
            if resp['type'] == 'snowball_started' and resp['account_id'] == source:
                state = "vs started"
            if resp['type'] == 'snowball_created' and resp['account_id'] == source:
                tx_hash = resp['tx_hash']
                state = f"vs created: {tx_hash}"
            if resp['type'] == 'transaction_created' and resp['id'] == self.id:
                tx_hash = resp['tx_hash']
                state = f"tx created: {tx_hash}"
                break
            if resp['type'] == 'error' and resp.get('id') == self.id:
                print(f"Error happened: error={resp['error']}")
                return False

        status = await self.wait_tx(tx_hash)

        if status:
            logging.info(
                f"{self.prefix}[{source}] tx: {tx_hash} included in microblock")
            SNOWBALL_TIMINGS.labels(account=self.accounts[source]).set(
                time.monotonic() - start_time)
            SNOWBALL_COUNTS.labels(account=self.accounts[source]).inc()
        else:
            logging.info(f"{self.prefix}[{source}] tx: {tx_hash} failed")

        self.prefix = self.node_id + f"[{source}]" + "(Idle)"
        return True

    async def wait_tx(self, tx_hash):
        state = f"waiting commit: tx={tx_hash}"
        start_time = time.monotonic()
        while True:
            resp = await self.recv_msg()
            elapsed = time.monotonic() - start_time
            self.prefix = f"{self.node_id} ({state}) elapsed: {elapsed}"
            if resp['type'] == 'transaction_status' and resp['tx_hash'] == tx_hash:
                if resp['status'] == 'accepted':
                    continue
                if resp['status'] in ['rejected', 'conflicted', 'rollback']:
                    return False
                if resp['status'] in ['prepared', 'committed']:
                    return True
                return False

            elapsed = time.monotonic() - start_time
            logging.info(f"{self.prefix} Elapsed: {elapsed}")


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
