from math import sqrt
from dataclasses import dataclass
from terra import *


def quadratic_root(a: float, b: float, c: float):
    s = sqrt(b ** 2 - 4 * a * c)
    return (-b + s) / (2 * a), (-b - s) / (2 * a)


@dataclass
class Trade:
    dex: str
    token_in: str
    amount_in: Dec
    token_out: str
    amount_out: Dec
    spread: Dec
    commission: Dec

    def float_amount_in(self):
        return from_Dec(self.amount_in, self.token_in)

    def float_amount_out(self):
        return from_Dec(self.amount_out, self.token_out)

    def float_commission(self):
        return from_Dec(self.commission, self.token_out)

    def __repr__(self):
        return f"From {self.float_amount_in()} {self.token_in} To {self.float_amount_out()}" \
               f" {self.token_out} on {self.dex}\n" \
               f"Rate {self.float_amount_out() / self.float_amount_in():.6f} {self.token_out} per {self.token_in}\n" \
               f"Spread {float(self.spread):.3%} Commission {self.float_commission()} {self.token_out}"


class Pool:
    def __init__(self, arg1: Union[str, Pair], arg2: str, dex=''):
        if isinstance(arg1, Pair):
            self.pair = arg1
            dex = arg2
        else:
            self.pair = Pair(arg1, arg2)
        self.token1, self.token2 = tuple(self.pair.pair)
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
        return f'{self.pair} on {self.dex}'

    def __eq__(self, other):
        return True if hash(self) == hash(other) else False

    def __hash__(self):
        return hash(str(self))

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
    def _token_amount(response: dict, token: str) -> Dec:
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
            pool_query = asyncio.create_task(terra.wasm.contract_query(self.contract, {'pool': {}}))
            if self.stable:
                config = await terra.wasm.contract_query(self.contract, {'config': {}})
                self.amp = Dec(json.loads(base64.b64decode(config['params'].encode('utf-8')))['amp'])
            response = await pool_query
            self.amount1 = self._token_amount(response, self.token1)
            self.amount2 = self._token_amount(response, self.token2)

    async def _xy(self, token_in: str) -> (Dec, Dec):
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

    async def _constant_product_swap(self, token_in: str, amount_in: Union[int, float, Dec]) -> Dec:
        """Calculate receive amount in constant product amm
        """
        if not isinstance(amount_in, Dec):
            amount_in = to_Dec(amount_in, token_in)
        xi, yi = await self._xy(token_in)
        return amount_in * yi / (xi + amount_in)

    async def _stable_swap(self, token_in: str, amount_in: Union[int, float, Dec]) -> Dec:
        """Calculate receive amount in a stable swap
        """
        if not isinstance(amount_in, Dec):
            amount_in = to_Dec(amount_in, token_in)
        xi, yi = await self._xy(token_in)
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
        xf = xi + amount_in
        b = xf + D * (1 / (2 * A) - 1)
        c = - D * D * D / (8 * A * xf)
        yf = max(quadratic_root(1, float(b), float(c)))
        return yi - yf

    async def price(self, token_in: str) -> Dec:
        """Marginal price of token_in in token_out
        """
        xi, yi = await self._xy(token_in)
        if self.dex == 'native_swap':
            return self.luna_ust if token_in == 'luna' else self.luna_ust.__rtruediv__(1)
        else:
            if self.stable:
                amount_in = xi / 10 ** 6
                return await self._stable_swap(token_in, amount_in) / amount_in
            else:
                return yi / xi

    async def simulate(self, token_in: str, amount_in: Union[int, float, Dec]) -> Trade:
        """Simulate the swap locally
        """
        token_in = token_in.lower()
        if not isinstance(amount_in, Dec):
            amount_in = to_Dec(amount_in, token_in)
        token_out = self.token2 if token_in == self.token1 else self.token1
        expected = await self.price(token_in) * amount_in
        # Market swap
        if self.dex == 'native_swap':
            amount_out = await self._constant_product_swap(token_in, amount_in)
            # The minimum spread charged on Terra<>Luna swaps to prevent leaking value from front-running attacks.
            spread = max((expected - amount_out) / expected, self.fee)
            commission = expected * spread
        else:
            # Stable swap
            if self.stable:
                amount_out = await self._stable_swap(token_in, amount_in)
            # Constant product swap
            else:
                amount_out = await self._constant_product_swap(token_in, amount_in)
            spread = (expected - amount_out) / expected + self.fee
            commission = amount_out * self.fee
        amount_out = expected * (1 - spread)
        return Trade(self.dex, token_in, amount_in, token_out, amount_out, spread, commission)

    async def trade_to_msg(self, trade: Trade, minimum_receive=Dec(0)) -> Union[Msg, list[Msg]]:
        """Wrap simulation result to a message
        """
        token_in, amount_in = trade.token_in, trade.amount_in

        if self.dex == 'native_swap':
            offer_coin = Coin(get_denom(token_in), amount_in.whole)
            ask_denom = get_denom(self.pair.other(token_in))
            if minimum_receive == Dec(0):
                minimum_receive = trade.amount_out * (1 - slippage)
            msg = {
                'assert_limit_order': {
                    'ask_denom': ask_denom,
                    'offer_coin': {
                        'denom': offer_coin.denom,
                        'amount': amount_in.whole
                    },
                    'minimum_receive': minimum_receive.whole
                }}
            assert_msg = MsgExecuteContract(wallet.key.acc_address, assert_limit_order, msg, Coins([offer_coin]))
            msg_swap = MsgSwap(wallet.key.acc_address, offer_coin, ask_denom)
            return [assert_msg, msg_swap]
        else:
            if minimum_receive == Dec(0):
                spread = str(slippage)
            else:
                spread = ((trade.amount_out - minimum_receive) / trade.amount_out).to_short_str()
            belief_price = trade.amount_in / trade.amount_out
            msg = {
                'swap': {
                    'offer_asset': {
                        'info': asset_info(token_in),
                        'amount': amount_in.whole
                    },
                    'belief_price': belief_price.to_short_str(),  # optional
                    'max_spread': spread,  # optional
                    # 'to': wallet.key.acc_address
                }}
            # Message for native tokens
            if token_in in native_tokens:
                offer_coin = Coin(get_denom(token_in), amount_in.whole)
                return MsgExecuteContract(wallet.key.acc_address, self.contract, msg, Coins([offer_coin]))
            # Message for CW20 tokens
            else:
                execute_msg = {
                    'send': {
                        'contract': self.contract,
                        'amount': amount_in.whole,
                        'msg': base64str_encode(msg)
                    }}
                return MsgExecuteContract(wallet.key.acc_address, get_contract(token_in), execute_msg)

    async def swap_msg(self, token_in: str, amount_in: Union[int, float, Dec],
                       minimum_receive=Dec(0)) -> Union[Msg, list[Msg]]:
        """Single swap message
        """
        token_in = token_in.lower()
        if not isinstance(amount_in, Dec):
            amount_in = to_Dec(amount_in, token_in)

        trade = await self.simulate(token_in, amount_in)
        return await self.trade_to_msg(trade, minimum_receive)
