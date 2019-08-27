#!/usr/bin/env python

import asyncio
import json
import stegos

BOT_ACCOUNTS = 5


def load_nodes(path):
    f = open(path, "r")
    encoded = f.read()
    return json.loads(encoded)


async def client_from_node(node):
    client = stegos.StegosClient(node_id=node['node_id'],
                                 uri=node['uri'],
                                 master_key=node['key_password'],
                                 api_key=node['api_token'])

    await client.connect()
    return client


async def my_app(nodes):
    for i in range(0, 7):
        node = await client_from_node(nodes[i])
        print("Waiting for sync!")
        await node.wait_sync()

        ids = await node.list_accounts()
        print(f"Node0{i+1} has accounts: {ids}")
        if len(ids) < BOT_ACCOUNTS:
            for n in range(0, BOT_ACCOUNTS - len(ids)):
                account_info = await node.create_account()
                nodes[i]['accounts'][account_info['account_id']
                                     ] = account_info['account_address']
        else:
            for id in ids:
                address = await node.get_address(id)
                nodes[i]['accounts'][id] = address

    out = open("out.json", "w")
    out.write(json.dumps(nodes, indent=2))


if __name__ == '__main__':
    nodes = load_nodes("sample.json")
    loop = asyncio.get_event_loop()
    loop.run_until_complete(my_app(nodes))
