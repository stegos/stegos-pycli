#!/usr/bin/env python3

import asyncio
import json
import stegos


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
    return client


async def my_app(heap_node, nodes):
    node01 = await client_from_node(heap_node)

    my_account = list(heap['accounts'].keys())[0]
    print("Waiting for sync!")
    await node01.wait_sync()
    balance = await node01.get_balance('heap')
    print(f"Node01 balance before payments: {balance}")
    for n in nodes:
        for id in n['accounts'].keys():
            await node01.payment_with_confirmation(my_account, n['accounts'][id], 100_000, comment="Initial payout")

    balance = await node01.get_balance('heap')
    print(f"Node01 balance after payments: {balance}")

if __name__ == '__main__':
    heap = {
        "node_id": "heap",
        "accounts": {
            "heap": "7f9nY9R4LYwmTuc3oEVhDETx6pq5uMpxYzS7nX4F5jNVn6MTcF1"
        },
        "key_password": "demo",
        "api_token": "09DmvBtLXUNnnysvZVBmkg==",
        "uri": "ws://127.0.0.1:3155",
    }

    nodes = load_nodes("sample.json")
    loop = asyncio.get_event_loop()
    loop.run_until_complete(my_app(heap, nodes))
