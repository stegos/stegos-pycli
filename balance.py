#!/usr/bin/env python3

import asyncio
import stegos


async def my_app():
    node01 = stegos.StegosClient(node_id='node01',
                                 uri='ws://localhost:3155',
                                 accounts={
                                     'heap': 'str1np4ndacy0rm8rjfewn67mj37ny0g9wynh3a7jctuetxpe6afgeks4f9cmg'
                                 },
                                 master_key='Oothi2loowu0aixe',
                                 api_key='a1iBv2rDko8m5R2r5lTv8Q==',
                                 debug=True)

    await node01.connect()
    await node01.subscribe_status()

    print("Waiting for sync!")
    await node01.wait_sync()
    balance = await node01.get_balance('heap')
    print(f"Node01 balance: {balance}")

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(my_app())
