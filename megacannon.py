#!/usr/bin/env python3

import asyncio
import json
import logging
import stegos
import sys
import websockets

from logging.handlers import RotatingFileHandler
from prometheus_client import start_http_server


def load_nodes(path):
    f = open(path, "r")
    encoded = f.read()
    return json.loads(encoded)


async def client_from_node(node):
    client = stegos.StegosClient(node_id=node['node_id'],
                                 uri=node['uri'],
                                 accounts=node['accounts'],
                                 master_key=node['key_password'],
                                 api_key=node['api_token'])

    await client.connect()
    await client.subscribe_status()
    return client


async def loop_payment(client, source, target, start_amount):
    amount = start_amount
    while True:
        try:
            if await client.secure_payment_with_confirmation(source, target, amount):
                amount = amount + 0.001
            else:
                # sleep 5 sec after the error
                await asyncio.sleep(5)
        except websockets.exceptions.ConnectionClosedError:
            print(
                f"Node: {client.node_id} closed connection. Re-connecting....")
            await client.connect()
            await client.wait_sync()
        except Exception as e:
            print(f"Node: {client.node_id} failed: {e}. Terminating...")
            sys.exit(1)


async def my_app(nodes):
    clients = []
    for n in range(0, len(nodes)):
        accounts = list(nodes[n]['accounts'].keys())
        accounts.sort()
        for i in range(0, len(accounts)):
            client = {
                "socket": await client_from_node(nodes[n]),
                "source": accounts[i],
                "dest": nodes[n]['accounts'][accounts[(i+1) % len(accounts)]],
            }
            clients.append(client)
            print(
                f"clients lients[{i}]: source={client['source']}, dest={client['dest']}")

    for c in clients:
        await c['socket'].wait_sync()
        b = await c['socket'].get_balance(c['source'])
        assert b > 0

    for c in clients:
        c['socket'].wait_sync()
        asyncio.ensure_future(loop_payment(
            c['socket'], c['source'], c['dest'], 0.01))


if __name__ == '__main__':
    start_http_server(8891)
    logging.basicConfig(format='%(asctime)s %(message)s', level=logging.DEBUG)
    # add a rotating handler
    handler = RotatingFileHandler(
        'megacannon.log', maxBytes=100*1024*1024, backupCount=5)
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logging.getLogger('').addHandler(handler)
    logging.getLogger('websockets').addHandler(logging.NullHandler())
    logging.getLogger('websockets').setLevel(logging.CRITICAL)
    nodes = load_nodes("vst.json")
    loop = asyncio.get_event_loop()
    loop.run_until_complete(my_app(nodes))
    loop.run_forever()
