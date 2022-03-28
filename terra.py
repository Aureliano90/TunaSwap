from typing import Union, Any
from terra_sdk.client.lcd import AsyncLCDClient, AsyncWallet as _AsyncWallet, LCDClient
from terra_sdk.client.lcd.api.tx import CreateTxOptions, SignerOptions
from terra_sdk.exceptions import LCDResponseError
from terra_sdk.key.key import Key
from terra_sdk.key.mnemonic import MnemonicKey
from terra_sdk.core import AccAddress, Coin, Coins, Dec, Tx
from terra_sdk.core.wasm.msgs import MsgExecuteContract
from terra_sdk.core.msg import Msg
from terra_sdk.core.fee import Fee
from terra_sdk.core.market.msgs import MsgSwap
from consts import *
from heapq import heappop, heappush
from pprint import pprint
import asyncio
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
                       gas_adjustment='1.5')


def base64str_decode(msg: str) -> Any:
    """Decode base64 string
    """
    return json.loads(base64.b64decode(msg.encode('utf-8')).decode('utf-8'))


def base64str_encode(obj: Any) -> str:
    """Encode Python object to base64 string
    """
    return base64.b64encode(json.dumps(obj).encode('utf-8')).decode('utf-8')


class async_property(property):
    """Descriptor for the async version of property
    """

    def __init__(self, fget):
        name = fget.__name__
        _name = f'_{name}'

        def setter(instance, value):
            setattr(instance, _name, value)

        async def _fget(instance):
            coro = fget(instance)
            setter(instance, await coro)
            return getattr(instance, _name)

        def getter(instance):
            attr = getattr(instance, _name, False)
            if not attr:
                if loop.is_running():
                    task = loop.create_task(_fget(instance), name=f'wallet.{name}')
                    return task
                else:
                    return loop.run_until_complete(_fget(instance))
            return attr

        super().__init__(getter, setter, doc=fget.__doc__)


class AsyncWallet(_AsyncWallet):
    """Custom AsyncWallet initialized by `await AsyncWallet(lcd, key)`\n
    `wallet.sequence` is automatically incremented.
    """
    account_number = async_property(_AsyncWallet.account_number)
    # Nonce
    sequence = async_property(_AsyncWallet.sequence)

    def __init__(self, lcd, key: Key):
        super(AsyncWallet, self).__init__(lcd, key)
        self._account_number = None
        self._sequence = None

    def __await__(self):
        yield from asyncio.create_task(self.account_number_and_sequence())
        return self

    async def account_number_and_sequence(self) -> dict:
        try:
            res = await super(AsyncWallet, self).account_number_and_sequence()
            self._account_number, self._sequence = res['account_number'], res['sequence']
            return dict(account_number=self.account_number, sequence=self.sequence)
        except LCDResponseError as exc:
            if 'key not found' in exc.message:
                print('Fund address to generate account.')
                # https://faucet.terra.money/
            else:
                raise

    async def create_and_sign_tx(self, options: CreateTxOptions) -> Tx:
        if not hasattr(options, 'account_number') or not hasattr(options, 'sequence'):
            await self.account_number_and_sequence()
        options.account_number = self.account_number
        options.sequence = self.sequence
        tx = await super(AsyncWallet, self).create_and_sign_tx(options)
        self.sequence = self.sequence + 1
        return tx


# Store your seed phrases in 'wall-e'
try:
    with open('wall-e') as w:
        seed = w.readline()

    if len(seed.split()) > 1:
        # Encode plain seed phrases
        with open('wall-e', 'w') as w:
            seed = base64str_encode(seed)
            w.write(seed)
except OSError:
    seed = MnemonicKey().mnemonic
    print(f"Generated new seed phrase in 'wall-e'. Go fund it.\n{seed}")
    with open('wall-e', 'w') as w:
        w.write(base64str_encode(seed))
    exit()

loop = asyncio.get_event_loop_policy().get_event_loop()
mk = MnemonicKey(base64str_decode(seed))
wallet = loop.run_until_complete(AsyncWallet(terra, mk))


def from_Dec(value: Dec, token: str) -> float:
    """Convert Dec to float accounting for the decimals
    """
    return float(Dec.with_prec(int(value), tokens_info[token.lower()]['decimals']).to_short_str())


def to_Dec(value: Union[int, float, Dec], token: str) -> Dec:
    """Convert int/float to Dec accounting for the decimals
    """
    if isinstance(value, Dec):
        return value
    return Dec(value * pow(10, tokens_info[token.lower()]['decimals']))


def get_denom(token: str):
    if token in native_tokens:
        return tokens_info[token]['denom']


def get_dex(token: str):
    return tokens_info[token]['dex']


def get_contract(token: str):
    if token not in native_tokens:
        return tokens_info[token]['contract']


def asset_info(token: str) -> dict:
    token = token.lower()
    if token in native_tokens:
        return {'native_token': {'denom': get_denom(token)}}
    else:
        return {'token': {'contract_addr': get_contract(token)}}


async def create_and_sign_tx(msgs: Union[Msg, list[Msg]], **options) -> Union[Tx, None]:
    if isinstance(msgs, Msg):
        msgs = [msgs]
    try:
        return await wallet.create_and_sign_tx(CreateTxOptions(msgs=msgs, **options))
    except LCDResponseError as exc:
        print(exc)
        return None


def gas_fee(tx: Tx) -> Fee:
    return tx.auth_info.fee


async def estimate_fee(msgs: Union[Msg, list[Msg]], **options) -> Union[Fee, None]:
    """Estimate gas fee
    """
    if isinstance(msgs, Msg):
        msgs = [msgs]
    sigOpt = [
        SignerOptions(
            address=wallet.key.acc_address,
            sequence=wallet.sequence,
            public_key=wallet.key.public_key,
        )]
    try:
        return await terra.tx.estimate_fee(sigOpt, CreateTxOptions(msgs=msgs, **options))
    except LCDResponseError as exc:
        print(exc)
        return None


async def token_balance(token: str) -> Dec:
    """Query token balance
    """
    try:
        if token in native_tokens:
            coins, _ = await terra.bank.balance(wallet.key.acc_address)
            return coins.get(get_denom(token)).amount
        else:
            msg = {'balance': {'address': wallet.key.acc_address}}
            return Dec((await terra.wasm.contract_query(get_contract(token), msg))['balance'])
    except LCDResponseError as exc:
        print(exc)
        exit(1)


async def coins_balance() -> Coins:
    """Query native tokens balance
    """
    coins, _ = await terra.bank.balance(wallet.key.acc_address)
    return coins


async def pair_query(dex: str, token1: str, token2: str) -> dict:
    """Query pair info on dex
    """
    msg = {'pair': {'asset_infos': [asset_info(token1), asset_info(token2)]}}
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
