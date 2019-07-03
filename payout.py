#!/usr/bin/env python3

import asyncio
import stegos


async def my_app():
    node01 = stegos.StegosClient(node_id='node01',
                                 uri='ws://localhost:3145',
                                 wallet='7fCTXenNEh14D4y2ciiaQm4oGDbw7HcbzhUad8dHkrfLuFitR5D',
                                 wallet_key='dev01',
                                 api_key='YvjaSV59G9jseRh7+dDEBA==')
    await node01.connect()

    print("Waiting for sync!")
    await node01.wait_sync()
    balance = await node01.get_balance()
    print(f"Node01 balance before payments: {balance}")
    await node01.payment_with_confitmation(
        '7eknF4uTc35Jo6zoe8PZkxNKgM5KkdEqfsBhJNHpA6pQsW17DBp', 10_000)
    await node01.payment_with_confitmation(
        '7dzcEh46KVyrdJoiTjzju6sfbGhjF3iYRKq6mCrpfjx3JzTbdfy', 10_000)
    await node01.payment_with_confitmation(
        '7eAPAJdYytmS32wmdzqjqmC69j8L2WPPHTAiUrB37qKVPvY44tx', 10_000)
    balance = await node01.get_balance()
    print(f"Node01 balance after payments: {balance}")

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(my_app())
