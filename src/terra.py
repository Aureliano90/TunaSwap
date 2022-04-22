from typing import Any, Iterable, Tuple, Union
from functools import wraps
from heapq import heappop, heappush
from terra_sdk.core import AccAddress, Coin, Coins, Dec, TxLog
from terra_sdk.core.market.msgs import MsgSwap
from terra_sdk.core.wasm.msgs import MsgExecuteContract
from terra_sdk.key.mnemonic import MnemonicKey
from src.consts import *
from src.wallet import *
from pprint import pprint
import requests
import base64
import json

if testnet:
    light_clinet_address = 'https://bombay-lcd.terra.dev'
    chain_id = 'bombay-12'
    gas_prices = requests.get('https://bombay-fcd.terra.dev/v1/txs/gas_prices').json()
else:
    light_clinet_address = 'https://lcd.terra.dev'
    chain_id = 'columbus-5'
    gas_prices = requests.get('https://fcd.terra.dev/v1/txs/gas_prices').json()
terra = AsyncLCDClient(chain_id=chain_id,
                       url=light_clinet_address,
                       gas_prices=Coins(uusd=gas_prices['uusd']),
                       gas_adjustment='1.2')


def base64str_decode(msg: str) -> Any:
    """Decode base64 string
    """
    return json.loads(base64.b64decode(msg.encode('utf-8')).decode('utf-8'))


def base64str_encode(obj: Any) -> str:
    """Encode Python object to base64 string
    """
    return base64.b64encode(json.dumps(obj).encode('utf-8')).decode('utf-8')


seed_path = r'wall-e'
# Store your seed phrases in 'seed_path'
try:
    with open(seed_path) as w:
        seed = w.readline()

    if len(seed.split()) > 1:
        # Encode plain seed phrases
        with open(seed_path, 'w') as w:
            seed = base64str_encode(seed)
            w.write(seed)
except OSError:
    seed = MnemonicKey().mnemonic
    print(f"Generated new seed phrase in {seed_path}. Go fund it.\n{seed}")
    with open(seed_path, 'w') as w:
        w.write(base64str_encode(seed))
    exit()

loop = asyncio.get_event_loop_policy().get_event_loop()
mk = MnemonicKey(base64str_decode(seed))
wallet = loop.run_until_complete(AsyncWallet(terra, mk))


def from_Dec(
        value: Dec | Coins,
        token=''
) -> float | Coins:
    """Convert `Dec` to `float` accounting for the decimals
    """
    if isinstance(value, Dec):
        return float(Dec.with_prec(int(value), tokens_info[token.lower()]['decimals']).to_short_str())
    elif isinstance(value, Coins):
        coins = []
        for coin in value:
            token = from_denom(coin.denom)
            amount = Dec.with_prec(int(coin.amount), tokens_info[token]['decimals'])
            coins.append(Coin(token, amount))
        return Coins(coins)
    else:
        raise ValueError


Numeric = Union[int, float, Dec]


def to_Dec(
        value: Numeric,
        token: str
) -> Dec:
    """Convert `int`/`float` to `Dec` accounting for the decimals
    """
    if isinstance(value, Dec):
        return value
    return Dec(value * pow(10, tokens_info[token.lower()]['decimals']))


def convert_params(method):
    """Convert order size to `Dec` in methods
    """

    @wraps(method)
    def wrapper(
            self,
            bid,
            bid_size,
            *args,
            **kwargs):
        bid = bid.lower()
        bid_size = to_Dec(bid_size, bid)
        return method(self,
                      bid,
                      bid_size,
                      *args,
                      **kwargs)

    return wrapper


def get_denom(token: str) -> str:
    """Get denomination from token symbol
    """
    return tokens_info[token]['denom'] if token in native_tokens else token


def from_denom(denom: str) -> str:
    """Get token symbol from denomination
    """
    for token in native_tokens:
        if tokens_info[token]['denom'] == denom:
            return token
    return denom


def get_dex(token: str) -> str:
    """Get DEXes trading `token`
    """
    return tokens_info[token]['dex']


def find_dex(s: str) -> str:
    """Fuzzy Search
    """
    s = s.lower()
    for dex in dexes:
        if dex.find(s) >= 0:
            return dex
    return ''


def get_contract(token: str) -> AccAddress | str:
    """Get contract address for `token`
    """
    try:
        return tokens_info[token]['contract']
    except KeyError:
        return ''


def from_contract(contract: str) -> str:
    """Get token symbol from `contract` address
    """
    for token, info in tokens_info.items():
        if 'contract' in info and info['contract'] == contract:
            return token


def asset_info(token: str, dex: str) -> Dict:
    """Asset info in swap message
    """
    token = token.lower()
    if dex == 'prism_swap':
        if token in native_tokens:
            return {'native': get_denom(token)}
        else:
            return {'cw20': get_contract(token)}
    else:
        if token in native_tokens:
            return {'native_token': {'denom': get_denom(token)}}
        else:
            return {'token': {'contract_addr': get_contract(token)}}


def gas_fee(tx: Tx) -> Fee:
    """Self-explanatory
    """
    return tx.auth_info.fee


async def token_balance(token: str) -> Dec:
    """Query `token` balance
    """
    token = token.lower()
    try:
        if token in native_tokens:
            coins, _ = await terra.bank.balance(wallet.key.acc_address)
            return coins.get(get_denom(token)).amount
        else:
            msg = {'balance': {'address': wallet.key.acc_address}}
            return Dec((await terra.wasm.contract_query(get_contract(token), msg))['balance'])
    except LCDResponseError as exc:
        print(exc)
        return Dec(0)


async def coins_balance() -> Coins | None:
    """Query native tokens balance
    """
    try:
        coins, _ = await terra.bank.balance(wallet.key.acc_address)
        return coins
    except LCDResponseError as exc:
        print(exc)
        return None


async def pair_query(
        dex: str,
        token1: str,
        token2: str
) -> Dict:
    """Query pair info on DEX
    """
    msg = {'pair': {'asset_infos': [asset_info(token1, dex),
                                    asset_info(token2, dex)]}}
    try:
        return await terra.wasm.contract_query(factory[dex], msg)
    except LCDResponseError as exc:
        print(exc)
        raise


async def validate_pool_info():
    """Validate local pools' info with blockchain
    """
    pairs = [(pair, dex) for pair in pools_info for dex in pools_info[pair] if dex != 'native_swap']
    queries = [pair_query(dex, *pair.pair) for pair, dex in pairs]
    response = await asyncio.gather(*queries, return_exceptions=True)
    result = {(pair, dex): res for (pair, dex), res in zip(pairs, response)}

    for pair in pools_info:
        for dex, info in pools_info[pair].items():
            if dex != 'native_swap':
                if isinstance(result[(pair, dex)], Exception):
                    print(f"{pair} isn't registered in {dex} factory contract."
                          f"Doesn't mean it's fake.")
                    continue
                assert result[(pair, dex)]['contract_addr'] == info['contract'], \
                    f"Incorrect {pair} contract on {dex}\n" \
                    f"{info['contract']}\n" \
                    f"Correct one: {result[(pair, dex)]['contract_addr']}"
                if dex == 'astro_swap':
                    if 'stable' in result[(pair, dex)]['pair_type']:
                        assert info['stable'], f"{pair} is a stable pair on {dex}."
                        assert info['fee'] == 0.0005, f"{pair} on {dex} has 0.05% fee."
                        continue
                assert not info['stable'], f"{pair} is not stable pair."
                assert info['fee'] == 0.003, f"{pair} on {dex} has 0.3% fee."
    print("Validated all pools' info")


async def multicall_query(queries: List[Dict]) -> List[Dict]:
    """Aggregate multiple queries using Multicall contract
    """
    nmsgs = 0
    tasks = []
    while nmsgs < len(queries):
        aggregate = {'aggregate': {'queries': queries[nmsgs:nmsgs + 20]}}
        tasks.append(terra.wasm.contract_query(multicall, aggregate))
        nmsgs += 20
    res = []
    for i in await asyncio.gather(*tasks):
        res.extend(i['return_data'])
    return res
