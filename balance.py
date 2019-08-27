#!/usr/bin/env python3

import asyncio
import stegos


async def my_app():
    node01 = stegos.StegosClient(node_id='node01',
                                 uri='ws://localhost:3145',
                                 accounts={
                                     '1': '7fCTXenNEh14D4y2ciiaQm4oGDbw7HcbzhUad8dHkrfLuFitR5D'
                                 },
                                 master_key='dev01',
                                 api_key='YvjaSV59G9jseRh7+dDEBA==')

    await node01.connect()

    print("Waiting for sync!")
    await node01.wait_sync()
    balance = await node01.get_balance('1')
    print(f"Node01 balance: {balance}")

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(my_app())
