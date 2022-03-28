import sys
from aggregator import *

assert sys.version_info >= (3, 8), print('Python version >=3.8 is required.\nYour Python version: ', sys.version)


async def main():
    async with terra:
        # pprint(await terra.tendermint.node_info())
        # pprint(await terra.tendermint.block_info()['block'])
        # pprint(await terra.bank.total())
        # pprint(terra.last_request_height)

        print(f'Address {wallet.key.acc_address}')
        # print(f'{await wallet.account_number_and_sequence()=}')
        print(f'{wallet.account_number=}')
        print(f'{wallet.sequence=}')

        from_token = 'Luna'
        to_token = 'bLuna'
        pool = Pool(from_token, to_token, 'astro_swap')
        bid = to_Dec(10, from_token)
        # # Simulate swap result on a specific pair
        trade = await pool.simulate(from_token, bid)
        print(trade)
        # trade = await Pool('UST', 'Luna', 'native_swap').simulate('ust', 10)
        # print(trade)
        # Wrap simulation result to a message
        msgs = await pool.trade_to_msg(trade)
        # Simulate and wrap
        # msgs = await Pool(from_token, to_token, 'astro_swap').swap_msg(from_token, bid)

        # from_token = 'nluna'
        # to_token = 'bluna'
        # bid = to_Dec(100, from_token)
        # Find the best route with the least spread for a swap
        # routing = await Dex('terra_swap').dijkstra_routing(from_token, bid, to_token)
        # print(routing)
        # Wrap trading route to a message
        # msgs = await Dex('astro_swap').route_to_msg(routing)
        # Find and wrap
        # msgs = await Dex('astro_swap').swap_msg(from_token, bid, to_token)

        # Check token balance
        balance = await token_balance(from_token)
        print(f'{balance=}')
        if balance < bid:
            print(f'Insufficient balance of {from_token}')
            exit(1)

        # Make transaction message
        pprint(f'{msgs=}')
        if hasattr(msgs, 'execute_msg'):
            if from_token.lower() in native_tokens:
                pprint(msgs.execute_msg)
            else:
                pprint(msgs.execute_msg)
                pprint(base64str_decode(msgs.execute_msg['send']['msg']))

        # Estimate transaction fee
        fee = await estimate_fee(msgs, memo='')
        if fee:
            pprint(f'{fee=}')
        exit()

        # Create, sign and broadcast transaction
        tx = await create_and_sign_tx(msgs, memo='')
        pprint(tx)
        result = await terra.tx.broadcast(tx)
        # for log in result.logs:
        #     for event in log.events:
        #         pprint(event)
        pprint(result)

        # Query pair info on DEX
        pprint(await pair_query('astro_swap', 'ust', 'luna'))

        # Validate local pairs info with blockchain
        await validate_pool_info()

        pprint(f'{wallet.sequence=}')


if __name__ == '__main__':
    # pprint(base64str_decode(''))
    # exit()
    loop.run_until_complete(main())