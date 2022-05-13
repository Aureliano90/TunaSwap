# TunaSwap

A high level interface for swapping tokens on [Terra(Luna)](https://www.terra.money/)
blockchain based on the [Terra.py SDK](https://github.com/terra-money/terra.py)

## Disclaimer

This project is by no means affiliated with any dog shit on Binance Smart Chain. The author does not assume
responsibilities for the use of the code, nor is warranty granted.

## Features

* Support [Terraswap](https://app.terraswap.io/Swap), [Astroport](https://app.astroport.fi/swap)
  , [Loop](https://dex.loop.markets/), [Prism](https://prismprotocol.app/swap) and native swaps using Terra's built-in
  market module
* Fully async
* Simulate and predict actual trading price locally
* Find the best route with the least spread for a swap
* Create, sign and broadcast transactions
* Limit order and stop loss order
* Manage Anchor LTV

## Usage Examples

Simulate swap result on a specific pair

```
>>> from order import *
>>> await Pool('bLuna', 'Luna', 'terra_swap').simulate('LUNA', 100)
```

```
From 100.0 luna To 100.708998 bluna
Rate 1.007090 bluna per luna
Spread 0.330% Commission 0.303036 bluna
```

Find the best route with the least spread for a swap

```
>>> await Dex('terra_swap').dijkstra_routing('nLuna', 100, 'bLuna')
```

```
Route(100.0 nluna -> 191475.553937 psi -> 7275.843784 ust -> 89.299495 luna -> 89.618139 bluna on terra_swap)
```

Meanwhile, Terraswap gives

<p align="center">
  <img width="400" height="600" src="https://raw.githubusercontent.com/Aureliano90/TunaSwap/main/multi_hop_swap.jpg" alt='multi_hop_swap'>
</p>

`OrderBook` accepts and executes limit order or stop loss order.

```
>>> book = OrderBook('astro_swap')
>>> book.submit(StopLoss('', 'bluna', 1, 'ust', price=1000))
>>> book.submit(LimitOrder('', 'ust', 100, 'luna', price=0.001))
>>> task = asyncio.create_task(book.start(broker=True))
```

```
Open stop order 1: 1000.0 ust -> 1.0 luna on astro_swap
Trigger price 0.001 luna per ust
Open limit order 2: 1.0 luna -> 1000.0 ust on astro_swap
Limit price 1000 ust per luna

1   Query price
2   Place order
3   Cancel order
4   Pending orders
q   Quit
```

Create, sign and broadcast transaction

```
>>> msgs = await Dex('terra_swap').swap('nLuna', 100, 'bLuna')
>>> tx = await wallet.create_and_sign_tx(msgs, memo='')
>>> result = await wallet.broadcast(tx)
```

Query pair info on DEX

```
>>> await pair_query('terra_swap', 'ust', 'bluna')
```

```
{'asset_infos': [{'token': {'contract_addr': 'terra1kc87mu460fwkqte29rquh4hc20m54fxwtsx7gp'}},
                 {'native_token': {'denom': 'uusd'}}],
 'contract_addr': 'terra1qpd9n7afwf45rkjlpujrrdfh83pldec8rpujgn',
 'liquidity_token': 'terra1qmr8j3m9x53dhws0yxhymzsvnkjq886yk8k93m'}
```

Validate local pairs' info with blockchain

```
>>> await validate_pool_info()
```

## Installation

Install Python 3.10+ and required packages.

```
pip install -r requirements.txt
```

Save seed phrases in a specific file or generate new ones.

Set `testnet = False` in `consts.py` for mainnet.

```
python main.py
```

## License

This project is licensed under the AGPL-3.0 License.
See [LICENSE](https://github.com/Aureliano90/TunaSwap/blob/main/LICENSE) for full disclosure.

Permissions of this license are conditioned on making available complete source code of licensed works and
modifications, which include larger works using a licensed work, under the same license. Copyright and license notices
must be preserved. Contributors provide an express grant of patent rights. When a modified version is used to provide a
service over a network, the complete source code of the modified version must be made available.
