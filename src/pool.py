from math import sqrt
from functools import singledispatch
from src.terra import *
import attr


def quadratic_root(a: float, b: float, c: float):
    s = sqrt(b ** 2 - 4 * a * c)
    a = 1 / (2 * a)
    return (-b + s) * a, (-b - s) * a


@attr.s(repr=False, slots=True)
class Swap:
    """Dataclass of a swap
    """
    dex: str = attr.ib(converter=find_dex)
    bid: str = attr.ib()
    bid_size: Numeric = attr.ib(converter=Dec, eq=False)
    ask: str = attr.ib()
    ask_size: Numeric = attr.ib(converter=Dec, eq=False)
    spread: Dec = attr.ib(converter=Dec, default=0, eq=False)
    commission: Dec = attr.ib(converter=Dec, default=0, eq=False)

    def float_bid(self):
        return from_Dec(self.bid_size, self.bid)

    def float_ask(self):
        return from_Dec(self.ask_size, self.ask)

    def float_commission(self):
        return from_Dec(self.commission, self.ask)

    def __repr__(self):
        return f"From {self.float_bid()} {self.bid} To {self.float_ask()}" \
               f" {self.ask} on {self.dex}\n" \
               f"Rate {self.float_ask() / self.float_bid():.6f} {self.ask} per {self.bid}\n" \
               f"Spread {float(self.spread):.3%} Commission {self.float_commission()} {self.ask}"


class Pool:
    """Class representing an AMM liquidity pool
    """
    __slots__ = ('amp', 'amount1', 'amount2', 'contract', 'dex', 'fee', 'last_query', 'luna_ust', 'pair', 'stable',
                 'token1', 'token2', 'tx_fee')

    def __init__(self, *args):
        @singledispatch
        def init(*args):
            raise TypeError(*args)

        @init.register(str)
        def _(token1: str, token2: str, dex=''):
            return Pair(token1, token2), find_dex(dex)

        @init.register(Pair)
        def _(pair, dex=''):
            return pair, find_dex(dex)

        @init.register(Swap)
        def _(swap):
            return Pair(swap.bid, swap.ask), swap.dex

        self.pair, self.dex = init(*args)
        self.token1, self.token2 = self.pair.pair
        assert self.token1 != self.token2
        assert self.token1 in tokens_info, f"No token info {self.token1}"
        assert self.token2 in tokens_info, f"No token info {self.token2}"
        self.amp = self.amount1 = self.amount2 = Dec(0)
        self.last_query = 0
        # Terra Market module swap
        if self.dex == 'native_swap':
            self.luna_ust = Dec(0)
            self.stable = False
        else:
            try:
                self.contract = AccAddress(pools_info[self.pair][self.dex]['contract'])
                self.fee = pools_info[self.pair][self.dex]['fee']
                self.tx_fee = pools_info[self.pair][self.dex]['tx_fee']
                self.stable = pools_info[self.pair][self.dex]['stable']
            except KeyError:
                self.pair_info(self.dex)

    def __repr__(self):
        return f'Pool{self.pair.pair} on {self.dex}'

    def __hash__(self):
        return hash(str(self))

    def __eq__(self, other):
        return hash(self) == hash(other)

    def pair_info(self, dex):
        """Find pair info from smart contract
        """
        assert dex != 'native_swap'
        if self.pair in pools_info:
            # dex isn't specified.
            for dex, info in pools_info[self.pair].items():
                print(f'Using {dex}')
                self.dex = dex
                self.contract = AccAddress(info['contract'])
                self.fee = info['fee']
                self.tx_fee = info['tx_fee']
                self.stable = info['stable']
                return
        else:
            print(f"Can't find {self.pair} info locally. Querying blockchain.")
            from terra_sdk.client.lcd import LCDClient
            c = LCDClient(chain_id=chain_id, url=light_clinet_address)

            if dex:
                try:
                    msg = ABI.pair(self.pair, dex)
                    asset_infos = c.wasm.contract_query(factory[dex], msg)
                except LCDResponseError as exc:
                    print(f"Exception in {type(self).__name__}.pair_info\n{exc}")
                    raise
            else:
                # Query all factory contracts
                for dex in factory:
                    try:
                        msg = ABI.pair(self.pair, dex)
                        asset_infos = c.wasm.contract_query(factory[dex], msg)
                        break
                    except LCDResponseError as exc:
                        print(f"Exception in {type(self).__name__}.pair_info\n{exc}")
                else:
                    print('Pair is not found on any DEX.')
                    raise ValueError
            self.dex = dex
            self.contract = AccAddress(asset_infos['contract_addr'])
            self.tx_fee = 0
            self.fee = 0.003
            self.stable = False
            if 'pair_type' in asset_infos and 'stable' in asset_infos['pair_type']:
                self.fee = 0.0005
                self.stable = True

    @staticmethod
    def _token_amount(
            response: Dict,
            token: str
    ) -> Dec:
        """Get token amount in pool
        """

        def flatten(dict):
            for key, value in dict.items():
                if isinstance(value, Dict):
                    yield from flatten(value)
                else:
                    yield value

        for asset in response['assets']:
            if get_denom(token) in flatten(asset['info']):
                return Dec(asset['amount'])
            if get_contract(token) in flatten(asset['info']):
                return Dec(asset['amount'])

    async def query(self):
        """Query liquidity
        """
        if self.dex == 'native_swap':
            if (loop.time() - self.last_query) > 6:
                delta, params, rates = await asyncio.gather(terra.market.terra_pool_delta(), terra.market.parameters(),
                                                            terra.oracle.exchange_rates())
                self.last_query = loop.time()
                base_pool = params['base_pool']
                self.fee = params['min_stability_spread']
                luna_sdt = rates.get('usdr').amount
                self.luna_ust = rates.get('uusd').amount
                sdt_ust = self.luna_ust / luna_sdt
                self.amount1 = base_pool * base_pool / (base_pool + delta) / luna_sdt
                self.amount2 = (base_pool + delta) * sdt_ust
        else:
            if self.stable:
                pool, config = await multicall_query(self.multicall_query_msg())
                self.amp = Dec(base64str_decode(config['params'])['amp'])
            else:
                pool = await terra.wasm.contract_query(self.contract, ABI.self('pool'))
            self.amount1 = self._token_amount(pool, self.token1)
            self.amount2 = self._token_amount(pool, self.token2)

    def multicall_query_msg(self) -> List[ABI.multicall_query]:
        """Query message
        """
        assert self.dex != 'native_swap'
        pool = ABI.multicall_query(self.contract, ABI.self('pool'))
        msgs = [pool]
        if self.stable:
            config = ABI.multicall_query(self.contract, ABI.self('config'))
            msgs.append(config)
        return msgs

    def parse_multicall_res(self, msgs: List[Dict]):
        """Update pool information
        """
        for data in msgs:
            if 'assets' in data:
                self.amount1 = self._token_amount(data, self.token1)
                self.amount2 = self._token_amount(data, self.token2)
            elif 'params' in data:
                self.amp = Dec(base64str_decode(data['params'])['amp'])

    async def xy(self, token_in: str) -> (Dec, Dec):
        """Initial liquidity
        """
        if self.dex == 'native_swap':
            await self.query()
            if token_in == 'luna':
                return self.amount1, self.amount2
            elif token_in == 'ust':
                return self.amount2, self.amount1
            else:
                raise ValueError
        else:
            if self.amount1 == Dec(0) or self.amount2 == Dec(0):
                await self.query()
            if token_in == self.token1:
                return self.amount1, self.amount2
            elif token_in == self.token2:
                return self.amount2, self.amount1
            else:
                raise ValueError

    @convert_params
    async def _constant_product_swap(
            self,
            bid: str,
            bid_size: Numeric
    ) -> Dec:
        """Calculate receive amount in constant product amm
        """
        xi, yi = await self.xy(bid)
        return bid_size * yi / (xi + bid_size)

    @convert_params
    async def _stable_swap(
            self,
            bid: str,
            bid_size: Numeric
    ) -> Dec:
        """Calculate receive amount in a stable swap
        """
        xi, yi = await self.xy(bid)
        A2 = self.amp * 2
        D = S = xi + yi
        P4 = xi * yi * 4
        # Newton's method, x -= f(x) / f'(x)
        # f(D) =  D^3 / 4P + 2A(D - S) - D
        # f'(D) = 3D^2 / 4P + 2A - 1
        D2 = D * D
        e = (D2 * D / P4 + A2 * (D - S) - D) / (3 * D2 / P4 + A2 - 1)
        D -= e
        while abs(e) > 1:
            D2 = D * D
            e = (D2 * D / P4 + A2 * (D - S) - D) / (3 * D2 / P4 + A2 - 1)
            D -= e
        # Curve v1
        # x + y + D / 2A = D + D^3 / 8Axy
        # y + x + D / 2A - D - D^3 / 8Axy = 0
        # y^2 + (x + D / 2A - D) y - D^3 / 8Ax = 0
        xf = xi + bid_size
        b = xf + D / A2 - D
        c = - D * D * D / (4 * A2 * xf)
        yf = max(quadratic_root(1, float(b), float(c)))
        return yi - yf

    async def price(self, bid: str) -> Dec:
        """Marginal price of token_in in token_out
        """
        xi, yi = await self.xy(bid)
        if self.dex == 'native_swap':
            return self.luna_ust if bid == 'luna' else self.luna_ust.__rtruediv__(1)
        else:
            if self.stable:
                bid_size = Dec(10 ** 6)
                return await self._stable_swap(bid, bid_size) / bid_size
            else:
                return yi / xi

    @convert_params
    async def simulate(
            self,
            bid: str,
            bid_size: Numeric
    ) -> Swap:
        """Simulate the swap locally
        """
        ask = self.pair.other(bid)
        expected = await self.price(bid) * bid_size
        # Market swap
        if self.dex == 'native_swap':
            ask_size = await self._constant_product_swap(bid, bid_size)
            # The minimum spread charged on Terra<>Luna swaps to prevent leaking value from front-running attacks.
            spread = max((expected - ask_size) / expected, self.fee)
            commission = expected * spread
        else:
            # Stable swap
            if self.stable:
                ask_size = await self._stable_swap(bid, bid_size)
            # Constant product swap
            else:
                ask_size = await self._constant_product_swap(bid, bid_size)
            commission = ask_size * self.fee
            spread = (expected - ask_size + commission) / expected
        ask_size = expected * (1 - spread)
        return Swap(self.dex,
                    bid,
                    bid_size,
                    ask,
                    ask_size,
                    spread,
                    commission)

    @convert_params
    async def reverse_simulate(
            self,
            ask: str,
            ask_size: Numeric
    ) -> Swap:
        """Simulate the swap in reverse
        """
        bid = self.pair.other(ask)
        expected = ask_size / (1 - self.fee)
        # Market swap
        if self.dex == 'native_swap':
            bid_size = - await self._constant_product_swap(ask, - ask_size)
            # The minimum spread charged on Terra<>Luna swaps to prevent leaking value from front-running attacks.
            minimum = await self.price(ask) * expected
            if minimum > bid_size:
                bid_size = minimum
            else:
                expected = await self.price(bid) * bid_size
            commission = expected - ask_size
        else:
            # Stable swap
            if self.stable:
                bid_size = - await self._stable_swap(ask, - expected)
            # Constant product swap
            else:
                bid_size = - await self._constant_product_swap(ask, - expected)
            commission = expected * self.fee
            expected = await self.price(bid) * bid_size
        spread = (expected - ask_size) / expected
        return Swap(self.dex,
                    bid,
                    bid_size,
                    ask,
                    ask_size,
                    spread,
                    commission)

    async def swap_to_msg(
            self,
            swap: Swap,
            minimum_receive=Dec(0)
    ) -> List[Msg]:
        """Wrap simulation result to a message
        """
        bid, bid_size, ask, ask_size = swap.bid, swap.bid_size, swap.ask, swap.ask_size

        if self.dex == 'native_swap':
            offer_coin = Coin(get_denom(bid), bid_size.whole)
            ask_denom = get_denom(self.pair.other(bid))
            if minimum_receive == Dec(0):
                if ask_size != Dec(0):
                    minimum_receive = ask_size * (1 - slippage)
                else:
                    return await self.swap(bid, bid_size)
            assert_msg = MsgExecuteContract(wallet.key.acc_address,
                                            assert_limit_order,
                                            ABI.assert_limit_order(ask_denom, offer_coin, minimum_receive),
                                            Coins([offer_coin]))
            swap_msg = MsgSwap(wallet.key.acc_address, offer_coin, ask_denom)
            return [assert_msg, swap_msg]
        else:
            if ask_size == Dec(0):
                return await self.swap(bid, bid_size)
            if minimum_receive == Dec(0):
                spread = Dec(slippage)
            else:
                spread = (ask_size - minimum_receive) / ask_size
            belief_price = bid_size / ask_size
            msg = ABI.swap(self.dex, bid, bid_size, belief_price, spread)
            # Message for native tokens
            if bid in native_tokens:
                return [MsgExecuteContract(wallet.key.acc_address,
                                           self.contract,
                                           msg,
                                           Coins({get_denom(bid): bid_size.whole}))]
            # Message for CW20 tokens
            else:
                return [MsgExecuteContract(wallet.key.acc_address,
                                           get_contract(bid),
                                           ABI.send(self.contract, bid_size, msg))]

    @convert_params
    async def swap(
            self,
            bid: str,
            bid_size: Numeric,
            minimum_receive=Dec(0)
    ) -> List[Msg]:
        """Single swap message
        """
        swap = await self.simulate(bid, bid_size)
        return await self.swap_to_msg(swap, minimum_receive)


async def multi_pools_query(pools: Iterable[Pool]):
    """Query multiple pools
    """
    native_swap = None
    for pool in pools:
        if pool.dex == 'native_swap':
            native_swap = pool
            break
    pools = [pool for pool in pools if pool.dex != 'native_swap']
    msgs = []
    for pool in pools:
        msgs += pool.multicall_query_msg()
    task = asyncio.create_task(multicall_query(msgs))
    if native_swap:
        await native_swap.query()
    res = await task
    i = 0
    for pool in pools:
        if pool.stable:
            pool.parse_multicall_res(res[i:i + 2])
            i += 2
        else:
            pool.parse_multicall_res(res[i:i + 1])
            i += 1
