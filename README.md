# TunaSwap

A high level interface for swapping tokens on [Terra(Luna)](https://www.terra.money/)
blockchain based on the [Terra.py SDK](https://github.com/terra-money/terra.py)

## Disclaimer

This project is by no means affiliated with any dog shit on Binance Smart Chain. The author does not assume
responsibilities for the use of the code, nor is warranty granted.

## Features

* Support [TerraSwap](https://app.terraswap.io/Swap), [Astroport](https://app.astroport.fi/swap)
  , [Loop](https://dex.loop.markets/) and native swaps using Terra's built-in market module
* Fully async for best performance
* Calculate token price on DEX trading pairs
* Simulate and predict actual trading price locally
* Find the best route with the least spread for a swap
* Create, sign and broadcast swap transactions

## Usage Examples

Simulate swap result on a specific pair

```
>>> from dex import *
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
Route: ('nluna', 'psi', 'ust', 'luna', 'bluna')
From 100.0 nluna To 89.795696 bluna on terra_swap
Rate 0.897957 bluna per nluna
Spread 10.338% Commission 10.353 bluna
```

On the other hand, TerraSwap gives

<p align="center">
  <img width="800" height="400" src="https://raw.githubusercontent.com/Aureliano90/TunaSwap/main/multi_hop_swap.jpg" alt='multi_hop_swap'>
</p>

Check token balance

```
>>> await token_balance(from_token)
```

Make transaction message

```
>>> msgs = await Dex('terra_swap').swap_msg('nLuna', 100, 'bLuna')
```

Estimate transaction fee

```
>>> await estimate_fee(msgs, memo='')
```

Create, sign and broadcast transaction

```
>>> tx = await create_and_sign_tx(msgs, memo='')
>>> result = await terra.tx.broadcast(tx)
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

Install Python 3.8+ and required packages.

```
pip install -r requirements.txt
```

## License

This project is licensed under the AGPL-3.0 License.
See [LICENSE](https://github.com/Aureliano90/TunaSwap/blob/main/LICENSE) for full disclosure.

Permissions of this license are conditioned on making available complete source code of licensed works and
modifications, which include larger works using a licensed work, under the same license. Copyright and license notices
must be preserved. Contributors provide an express grant of patent rights. When a modified version is used to provide a
service over a network, the complete source code of the modified version must be made available.

## Support

Improvements may be suggested, especially how to safely store and load seed phrases. Pull requests are welcome. Donation
is appreciated.

Terra address: terra1dgl5w2zqeq9s6puuq9tflylj9zfpf5zfngsj30