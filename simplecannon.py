#!/usr/bin/env python3

import asyncio
import json
import stegos

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
    return client


async def loop_payment(client, source, target, start_amount):
    amount = start_amount
    while True:
        await client.payment_with_confirmation(source, target, amount)
        amount = amount + 1


async def my_app(nodes):
    clients = []
    for n in range(0, len(nodes)):
        account_id = list(nodes[n]['accounts'].keys())[0]
        dest_node = (n+1) % len(nodes)
        dest_addr = nodes[dest_node]['accounts'][list(
            nodes[dest_node]['accounts'].keys())[0]]
        ws_client = await client_from_node(nodes[n])
        gen_info = {
            "source_id": account_id,
            "dest_addr": dest_addr,
            "ws_client": ws_client,
        }
        clients.append(gen_info)

    for c in clients:
        balance = await c['ws_client'].get_balance(c['source_id'])
        assert balance > 0

    for c in clients:
        asyncio.ensure_future(loop_payment(
            c['ws_client'], c['source_id'], c['dest_addr'], 10))


if __name__ == '__main__':
    start_http_server(8890)
    nodes = load_nodes("sample.json")
    loop = asyncio.get_event_loop()
    loop.run_until_complete(my_app(nodes))
    loop.run_forever()
