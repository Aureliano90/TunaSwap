from src.order import *
import sys

assert sys.version_info >= (3, 8), print('Python version >=3.8 is required.\nYour Python version: ', sys.version)


async def main():
    async with terra:
        # pprint(await terra.tendermint.node_info())
        # pprint(await terra.tendermint.block_info())
        # pprint(await block_height())
        # pprint(await terra.bank.total())
        # async for height in listen_new_block():
        #     print(loop.time(), height)
        # exit(0)

        print(f'Address {wallet.key.acc_address}')
        # print(f'{await wallet.account_number_and_sequence()=}')
        # print(f'{wallet.account_number=}')
        # print(f'{wallet.sequence=}')

        from_token = 'Luna'
        to_token = 'bLuna'
        pool = Pool(from_token, to_token, 'astro_swap')
        bid = to_Dec(10, from_token)
        # Simulate swap result on a specific pair
        trade = await pool.simulate(from_token, bid)
        print(trade)
        # Reverse simulation
        trade = await pool.reverse_simulate(to_token, trade.ask_size)
        print(trade)
        # Wrap simulation result to a message
        msgs = await pool.swap_to_msg(trade)
        # Simulate and wrap
        # msgs = await Pool(from_token, to_token, 'astro_swap').swap(from_token, bid)

        # from_token = 'nluna'
        # to_token = 'bluna'
        bid = to_Dec(100, from_token)
        # Find the best route with the least spread for a swap
        routing = await Dex('terra_swap').dijkstra_routing(from_token, bid, to_token)
        print(routing)
        # Wrap trading route to a message
        # msgs = await Dex('terra_swap').route_to_msg(routing)
        # Find and wrap
        # msgs = await Dex('terra_swap').swap(from_token, bid, to_token)

        book = OrderBook('astro_swap')
        # Start accepting orders
        # book.submit(StopLoss('', 'bluna', 1, 'ust', price=1000))
        # book.submit(LimitOrder('', 'ust', 100, 'luna', price=0.001))
        task = asyncio.create_task(book.start(broker=True))
        await task

        # Check token balance
        balance = await token_balance(from_token)
        print(f'{balance=}')
        if balance < bid:
            print(f'Insufficient balance of {from_token}')
            exit(1)

        pprint(msgs)
        for msg in msgs:
            if hasattr(msg, 'execute_msg'):
                if from_token.lower() in native_tokens:
                    pprint(msg.execute_msg)
                else:
                    pprint(msg.execute_msg)
                    pprint(base64str_decode(msg.execute_msg['send']['msg']))

        # Estimate transaction fee
        fee = await wallet.estimate_fee(msgs, memo='')
        if fee:
            print(f'{fee.amount=}')
        exit()

        # Create, sign and broadcast transaction
        tx = await wallet.create_and_sign_tx(msgs, fee=fee, memo='')
        # pprint(tx)
        result = await wallet.broadcast(tx)
        # for log in result.logs:
        #     for event in log.events:
        #         pprint(event)
        pprint(result)
        save_tx(result)
        txhash = result.txhash
        tx = retrieve_tx(txhash)
        print(f'{calculate_profit(tx)=}')

        # Query pair info on DEX
        pprint(await pair_query('astro_swap', 'ust', 'luna'))

        # Validate local pairs info with blockchain
        await validate_pool_info()

        pprint(f'{wallet.sequence=}')


if __name__ == '__main__':
    # pprint(base64str_decode(''))
    # exit()
    loop.run_until_complete(main())
