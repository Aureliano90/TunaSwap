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
                       gas_adjustment=1.2)


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
    l = s.lower()
    for dex in dexes:
        if dex.find(l) >= 0:
            return dex
    return s


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


async def token_balance(token: str) -> Dec:
    """Query `token` balance
    """
    token = token.lower()
    try:
        if token in native_tokens:
            coins, _ = await terra.bank.balance(wallet.key.acc_address)
            return coins.get(get_denom(token)).amount
        else:
            msg = ABI.balance(wallet.key.acc_address)
            return Dec((await terra.wasm.contract_query(get_contract(token), msg))['balance'])
    except LCDResponseError as exc:
        print(f"Exception in {token_balance.__name__}\n{exc}")
        return Dec(0)


async def coins_balance() -> Coins | None:
    """Query native tokens balance
    """
    try:
        coins, _ = await terra.bank.balance(wallet.key.acc_address)
        return coins
    except LCDResponseError as exc:
        print(f"Exception in {coins_balance.__name__}\n{exc}")
        return None


async def pair_query(
        dex: str,
        token1: str,
        token2: str
) -> Dict:
    """Query pair info on DEX
    """
    dex = find_dex(dex)
    msg = ABI.pair(Pair(token1, token2), dex)
    try:
        return await terra.wasm.contract_query(factory[dex], msg)
    except LCDResponseError as exc:
        print(f"Exception in {pair_query.__name__}\n{exc}")
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
                    print(f"{pair} isn't registered in {dex} factory contract. Doesn't mean it's fake.")
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


class ABI(Dict):
    """ABI for WASM messages
    """

    @classmethod
    def self(cls, query: str):
        return cls({query: {}})

    @classmethod
    def balance(cls, address: AccAddress):
        return cls({
            'balance': {
                'address': address
            }
        })

    @classmethod
    def send(
            cls,
            contract: AccAddress,
            amount: Dec,
            msg: Dict
    ):
        return cls({
            'send': {
                'contract': contract,
                'amount': amount.whole,
                'msg': base64str_encode(msg)
            }
        })

    @classmethod
    def asset_info(cls, token: str, dex: str):
        token = token.lower()
        if dex == 'prism_swap':
            if token in native_tokens:
                return cls({'native': get_denom(token)})
            else:
                return cls({'cw20': get_contract(token)})
        else:
            if token in native_tokens:
                return cls({'native_token': {'denom': get_denom(token)}})
            else:
                return cls({'token': {'contract_addr': get_contract(token)}})

    @classmethod
    def pair(cls, pair: Pair, dex: str):
        return cls({
            'pair': {
                'asset_infos': [ABI.asset_info(pair.pair[0], dex),
                                ABI.asset_info(pair.pair[1], dex)]
            }
        })

    @classmethod
    def assert_limit_order(
            cls,
            ask_denom: str,
            offer_coin: Coin,
            minimum_receive: Dec
    ):
        return cls({
            'assert_limit_order': {
                'ask_denom': ask_denom,
                'offer_coin': {
                    'denom': offer_coin.denom,
                    'amount': offer_coin.amount.whole if isinstance(offer_coin.amount, Dec) else f'{offer_coin.amount}'
                },
                'minimum_receive': minimum_receive.whole
            }
        })

    @classmethod
    def swap(
            cls,
            dex: str,
            bid: str,
            bid_size: Dec,
            belief_price: Dec,
            spread: Dec
    ):
        return cls({
            'swap': {
                'offer_asset': {
                    'info': ABI.asset_info(bid, dex),
                    'amount': bid_size.whole
                },
                'belief_price': belief_price.to_short_str(),  # optional
                'max_spread': spread.to_short_str(),  # optional
                # 'to': wallet.key.acc_address
            }
        })

    @classmethod
    def native_swap(cls, bid: str, ask: str):
        return cls({
            'native_swap': {
                'offer_denom': get_denom(bid),
                'ask_denom': get_denom(ask)
            }
        })

    @classmethod
    def dex_swap(cls, dex: str, bid: str, ask: str):
        return cls({
            dex: {
                'offer_asset_info': ABI.asset_info(bid, dex),
                'ask_asset_info': ABI.asset_info(ask, dex)
            }
        })

    @classmethod
    def execute_swap_operations(
            cls,
            bid_size: Dec,
            minimum_receive: Dec,
            max_spread: str,
            operations: List[Dict]
    ):
        return cls({
            'execute_swap_operations': {
                'offer_amount': bid_size.whole,
                'minimum_receive': minimum_receive.whole,
                'max_spread': max_spread,
                'operations': operations
            }
        })

    @classmethod
    def lock_collateral(cls, collateral: str, amount: Dec):
        return cls({
            'lock_collateral': {
                'collaterals': [
                    [
                        tokens_info[collateral]['contract'],
                        amount.whole
                    ]
                ]
            }
        })

    @classmethod
    def unlock_collateral(cls, collateral: str, amount: Dec):
        return cls({
            'unlock_collateral': {
                'collaterals': [
                    [
                        tokens_info[collateral]['contract'],
                        amount.whole
                    ]
                ]
            }
        })

    @classmethod
    def withdraw_collateral(cls, amount: Dec):
        return cls({
            'withdraw_collateral': {
                'amount': amount.whole
            }
        })

    @classmethod
    def collaterals(cls, borrower: AccAddress):
        return cls({
            'collaterals': {
                'borrower': borrower
            }
        })

    @classmethod
    def borrow_limit(cls, borrower: AccAddress):
        return cls({
            'borrow_limit': {
                'borrower': borrower
            }
        })

    @classmethod
    def borrower_info(cls, borrower: AccAddress):
        return cls({
            'borrower_info': {
                'borrower': borrower
            }
        })

    @classmethod
    def borrow_stable(cls, amount: Dec):
        return cls({
            'borrow_stable': {
                'borrow_amount': amount.whole
            }
        })

    class multicall_query(Dict):
        def __init__(self, contract: AccAddress, query: Dict):
            super().__init__(address=contract, data=base64str_encode(query), require_success=True)

    @classmethod
    def aggregate(cls, queries: List[multicall_query]):
        return cls({
            'aggregate': {
                'queries': queries
            }
        })


async def multicall_query(queries: List[ABI.multicall_query]) -> List[Dict]:
    """Aggregate multiple queries using Multicall contract
    """
    nmsgs = 0
    tasks = []
    while nmsgs < len(queries):
        aggregate = ABI.aggregate(queries[nmsgs:nmsgs + 20])
        tasks.append(terra.wasm.contract_query(multicall, aggregate))
        nmsgs += 20
    msgs = []
    for response in await asyncio.gather(*tasks):
        msgs.extend(response['return_data'])
    res = []
    for msg in msgs:
        assert msg['success']
        res.append(base64str_decode(msg['data']))
    return res
