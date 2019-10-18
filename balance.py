#!/usr/bin/env python3

import asyncio
import logging
import stegos


async def my_app():
    node01 = stegos.StegosClient(node_id='node01',
                                 uri='ws://localhost:3155',
                                 accounts={
                                     'heap': "stt16rw4yknx8sa80sp9dw0qzq72l9xd058hty7pm8y0ufjtnrv68yrs0rrrmg"
                                 },
                                 master_key="tOpSeCrEt",
                                 api_key="eXl6bfjMOmUkoqmbWnL/sw==",
                                 debug=True)

    await node01.connect()
    await node01.subscribe_status()

    print("Waiting for sync!")
    await node01.wait_sync()
    balance = await node01.get_balance('heap')
    print(f"Node01 balance: {balance}")

if __name__ == '__main__':
    # Configure logging
    logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                        level=logging.INFO)

    loop = asyncio.get_event_loop()
    loop.run_until_complete(my_app())
