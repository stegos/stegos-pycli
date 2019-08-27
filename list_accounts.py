#!/usr/bin/env python

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
                                 master_key=node['key_password'],
                                 api_key=node['api_token'])

    await client.connect()
    return client


async def my_app(nodes):
    full_nodes = []
    for n in nodes:
        client = await client_from_node(n)
        ids = await client.list_accounts()
        for id in ids.keys():
            n['accounts'][id] = ids[id]

        full_nodes.append(n)

    out = open("out.json", "w")
    out.write(json.dumps(full_nodes, indent=2))


if __name__ == '__main__':
    nodes = load_nodes("sample.json")
    loop = asyncio.get_event_loop()
    loop.run_until_complete(my_app(nodes))
