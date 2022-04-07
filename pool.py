from math import sqrt
from terra import *
import attr


def quadratic_root(a: float, b: float, c: float):
    s = sqrt(b ** 2 - 4 * a * c)
    return (-b + s) / (2 * a), (-b - s) / (2 * a)


@attr.s(repr=False)
class Trade:
    dex: str = attr.ib()
    bid: str = attr.ib()
    bid_size: Numeric = attr.ib(converter=Dec)
    ask: str = attr.ib()
    ask_size: Numeric = attr.ib(converter=Dec)
    spread: Dec = attr.ib(converter=Dec, default=0)
    commission: Dec = attr.ib(converter=Dec, default=0)

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
    def __init__(self, *args):
        if isinstance(args[0], Pair):
            self.pair = args[0]
            dex = args[1]
        else:
            self.pair = Pair(args[0], args[1])
            dex = args[2]
        self.token1, self.token2 = self.pair.pair
        assert self.token1 != self.token2
        assert self.token1 in tokens_info, f"No token info {self.token1}"
        assert self.token2 in tokens_info, f"No token info {self.token2}"
        self.amp = self.amount1 = self.amount2 = Dec(0)
        self.last_query = 0
        if dex == 'native_swap':
            self.dex = dex
            self.luna_ust = Dec(0)
            self.stable = False
        else:
            try:
                self.dex = dex
                self.contract = AccAddress(pools_info[self.pair][dex]['contract'])
                self.fee = pools_info[self.pair][dex]['fee']
                self.tx_fee = pools_info[self.pair][dex]['tx_fee']
                self.stable = pools_info[self.pair][dex]['stable']
            except KeyError:
                if self.pair in pools_info:
                    # dex isn't specified.
                    for dex, info in pools_info[self.pair].items():
                        print(f'Using {dex}')
                        self.dex = dex
                        self.contract = AccAddress(info['contract'])
                        self.fee = info['fee']
                        self.tx_fee = info['tx_fee']
                        self.stable = info['stable']
                        break
                else:
                    # Trading pair isn't available locally.
                    self.pair_info(dex)

    def __repr__(self):
        return f'Pool{self.pair.pair} on {self.dex}'

    def __hash__(self):
        return hash(str(self))

    def __eq__(self, other):
        return True if hash(self) == hash(other) else False

    def pair_info(self, dex):
        """Find pair info from smart contract
        """
        assert dex != 'native_swap'
        print(f"Can't find {self.pair} info locally. Querying blockchain.")
        c = LCDClient(chain_id=chain_id, url=light_clinet_address)
        asset_infos = {}
        if dex:
            try:
                msg = {'pair': {'asset_infos': [asset_info(self.token1), asset_info(self.token2)]}}
                asset_infos = c.wasm.contract_query(factory[dex], msg)
            except LCDResponseError as exc:
                print(exc)
                exit(1)
        else:
            for dex in factory:
                try:
                    msg = {'pair': {'asset_infos': [asset_info(self.token1), asset_info(self.token2)]}}
                    asset_infos = c.wasm.contract_query(factory[dex], msg)
                    break
                except LCDResponseError as exc:
                    print(exc)
            else:
                print('Pair is not found on any DEX.')
                exit(1)
        self.dex = dex
        self.contract = AccAddress(asset_infos['contract_addr'])
        self.tx_fee = 0
        self.fee = 0.003
        self.stable = False
        if 'pair_type' in asset_infos:
            if 'stable' in asset_infos['pair_type']:
                self.fee = 0.0005
                self.stable = True

    @staticmethod
    def _token_amount(
            response: Dict,
            token: str
    ) -> Dec:
        """Get token amount in pool
        """
        for asset in response['assets']:
            try:
                if asset['info']['native_token']['denom'] == get_denom(token):
                    return Dec(asset['amount'])
            except KeyError:
                if asset['info']['token']['contract_addr'] == get_contract(token):
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
            pool = asyncio.create_task(terra.wasm.contract_query(self.contract, {'pool': {}}))
            if self.stable:
                config = await terra.wasm.contract_query(self.contract, {'config': {}})
                self.amp = Dec(base64str_decode(config['params'])['amp'])
            response = await pool
            self.amount1 = self._token_amount(response, self.token1)
            self.amount2 = self._token_amount(response, self.token2)

    def multicall_query_msg(self) -> List[Dict]:
        """Query message
        """
        assert self.dex != 'native_swap'
        pool = {'address': self.contract,
                'data': base64str_encode({'pool': {}}),
                'require_success': True
                }
        msgs = [pool]
        if self.stable:
            config = {'address': self.contract,
                      'data': base64str_encode({'config': {}}),
                      'require_success': True
                      }
            msgs.append(config)
        return msgs

    def parse_multicall_res(self, msgs: List[Dict]):
        """Update pool information
        """
        for msg in msgs:
            assert msg['success']
            data = base64str_decode(msg['data'])
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
        A = self.amp
        D = S = xi + yi
        P = xi * yi
        # Newton's method, x -= f(x) / f'(x)
        e = (D * D * D / 4 / P + 2 * A * (D - S) - D) / (0.75 * D * D / P + 2 * A - 1)
        D += e
        while abs(e) > 1:
            e = (D * D * D / 4 / P + 2 * A * (D - S) - D) / (0.75 * D * D / P + 2 * A - 1)
            D -= e
        # Curve v1
        # x + y + D / 4A = D + D^3 / 16Axy
        # y + x + D / 4A - D - D^3 / 16Axy = 0
        # y^2 + (x + D / 4A - D) y - D^3 / 16Ax = 0
        xf = xi + bid_size
        b = xf + D * (1 / (2 * A) - 1)
        c = - D * D * D / (8 * A * xf)
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
                bid_size = xi / 10 ** 6
                return await self._stable_swap(bid, bid_size) / bid_size
            else:
                return yi / xi

    @convert_params
    async def simulate(
            self,
            bid: str,
            bid_size: Numeric
    ) -> Trade:
        """Simulate the swap locally
        """
        ask = self.token2 if bid == self.token1 else self.token1
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
            spread = (expected - ask_size) / expected + self.fee
            commission = ask_size * self.fee
        ask_size = expected * (1 - spread)
        return Trade(self.dex,
                     bid,
                     bid_size,
                     ask,
                     ask_size,
                     spread,
                     commission)

    async def trade_to_msg(
            self,
            trade: Trade,
            minimum_receive=Dec(0)
    ) -> List[Msg]:
        """Wrap simulation result to a message
        """
        bid, bid_size, ask, ask_size = trade.bid, trade.bid_size, trade.ask, trade.ask_size

        if self.dex == 'native_swap':
            offer_coin = Coin(get_denom(bid), bid_size.whole)
            ask_denom = get_denom(self.pair.other(bid))
            if minimum_receive == Dec(0):
                if ask_size != Dec(0):
                    minimum_receive = ask_size * (1 - slippage)
                else:
                    return await self.swap_msg(bid, bid_size)
            msg = {
                'assert_limit_order': {
                    'ask_denom': ask_denom,
                    'offer_coin': {
                        'denom': offer_coin.denom,
                        'amount': bid_size.whole
                    },
                    'minimum_receive': minimum_receive.whole
                }}
            assert_msg = MsgExecuteContract(wallet.key.acc_address,
                                            assert_limit_order,
                                            msg,
                                            Coins([offer_coin]))
            msg_swap = MsgSwap(wallet.key.acc_address, offer_coin, ask_denom)
            return [assert_msg, msg_swap]
        else:
            if ask_size == Dec(0):
                return await self.swap_msg(bid, bid_size)
            if minimum_receive == Dec(0):
                spread = str(slippage)
            else:
                spread = ((ask_size - minimum_receive) / ask_size).to_short_str()
            belief_price = bid_size / ask_size
            msg = {
                'swap': {
                    'offer_asset': {
                        'info': asset_info(bid),
                        'amount': bid_size.whole
                    },
                    'belief_price': belief_price.to_short_str(),  # optional
                    'max_spread': spread,  # optional
                    # 'to': wallet.key.acc_address
                }}
            # Message for native tokens
            if bid in native_tokens:
                offer_coin = Coin(get_denom(bid), bid_size.whole)
                return [MsgExecuteContract(wallet.key.acc_address,
                                           self.contract,
                                           msg,
                                           Coins([offer_coin]))]
            # Message for CW20 tokens
            else:
                execute_msg = {
                    'send': {
                        'contract': self.contract,
                        'amount': bid_size.whole,
                        'msg': base64str_encode(msg)
                    }}
                return [MsgExecuteContract(wallet.key.acc_address,
                                           get_contract(bid),
                                           execute_msg)]

    @convert_params
    async def swap_msg(
            self,
            bid: str,
            bid_size: Numeric,
            minimum_receive=Dec(0)
    ) -> List[Msg]:
        """Single swap message
        """
        trade = await self.simulate(bid, bid_size)
        return await self.trade_to_msg(trade, minimum_receive)


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
    res = await multicall_query(msgs)
    if native_swap:
        await native_swap.query()
    i = 0
    for pool in pools:
        if pool.stable:
            pool.parse_multicall_res(res[i:i + 2])
            i += 2
        else:
            pool.parse_multicall_res(res[i:i + 1])
            i += 1
