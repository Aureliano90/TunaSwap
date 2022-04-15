from dex import *
from transaction import *
import attr


class LimitOrder(Swap):
    def __init__(self, dex: str, bid: str, bid_size: Numeric, ask: str, ask_size=0, price=0):
        bid, ask = bid.lower(), ask.lower()
        if not isinstance(bid_size, Dec):
            bid_size = to_Dec(bid_size, bid)
        if not isinstance(ask_size, Dec):
            ask_size = to_Dec(ask_size, ask)
        if price == 0:
            assert ask_size != Dec(0)
            self.price = ask_size / bid_size
        else:
            self.price = Dec(price)
            ask_size = self.price * bid_size
        super(LimitOrder, self).__init__(dex, bid, bid_size, ask, ask_size)
        self.status = 'open'
        self.result = None

    def __repr__(self):
        s = f"limit order: {self.float_bid()} {self.bid} -> {self.float_ask()} {self.ask} on {self.dex}\n" \
            f"Limit price {self.price.to_short_str()} {self.ask} per {self.bid}"
        return 'Open ' + s if self.status == 'open' else 'Filled ' + s

    async def match(self, pools: Dict[Pair | str, Pool]) -> Route | None:
        route = await Dex(self.dex).dijkstra_routing(self.bid, self.bid_size, self.ask, pools)
        if route.trade.ask_size > self.ask_size:
            return route
        else:
            return None


class StopLoss(LimitOrder):
    triggered = attr.ib(default=False)

    def __repr__(self):
        s = f"stop order: {self.float_bid()} {self.bid} -> {self.float_ask()} {self.ask} on {self.dex}\n" \
            f"Trigger price {self.price.to_short_str()} {self.ask} per {self.bid}"
        return 'Open ' + s if self.status == 'open' else 'Filled ' + s

    async def match(self, pools: Dict[Pair | str, Pool]) -> Route | None:
        dex = Dex(self.dex)
        for route in dex.dfs(self.bid, self.ask):
            price = Dec(1)
            for i in range(len(route) - 1):
                pair = Pair(route[i], route[i + 1])
                if pair == Pair('luna', 'ust'):
                    pool = pools['native_swap']
                else:
                    pool = pools[pair]
                price *= await pool.price(route[i])
            if price < self.price:
                self.triggered = True
        if self.triggered:
            route = await dex.dijkstra_routing(self.bid, self.bid_size, self.ask, pools)
            self.ask_size = route.trade.ask_size * (1 - slippage)
            return route
        return None


@attr.s
class OrderBook:
    dex: Dex | str = attr.ib(converter=Dex)
    open: List[LimitOrder] = attr.ib(factory=list)
    filled: List[LimitOrder] = attr.ib(factory=list)
    pools: Dict[Pair | str, Pool] = attr.ib(default={})
    flag = attr.ib(default=False)

    def submit(self, order: LimitOrder):
        self.open.append(order)
        order.dex = self.dex.dex
        print(order)
        self.pools.update(self.dex.pools_from_routes(self.dex.dfs(order.bid, order.ask)))

    async def fill(self, order: LimitOrder, route: Route):
        try:
            msgs = await self.dex.route_to_msg(route, order.ask_size)
            fee = await wallet.estimate_fee(msgs, memo='')
            if fee is None:
                self.open.append(order)
                return
            tx = await wallet.create_and_sign_tx(msgs, fee=fee, memo='')
            res = await wallet.broadcast(tx)
            if res is None:
                self.open.append(order)
            else:
                order.status = 'filled'
                order.result = res
                for coin in calculate_profit(res):
                    if order.ask == from_denom(coin.denom) or order.ask == coin.denom:
                        order.ask_size = coin.amount
                print(order)
                save_tx(res)
                self.filled.append(order)
                pools = {}
                for order in self.open:
                    pools.update(self.dex.pools_from_routes(self.dex.dfs(order.bid, order.ask)))
                keys = set(self.pools.keys())
                for key in keys:
                    if key not in pools:
                        self.pools.pop(key)
        except LCDResponseError as exc:
            print(f"Exception in {type(self).__name__}.fill\n{exc}")
            raise

    async def broker(self):
        while True:
            print('Accepting order. Example:\nlimit bid=luna bid_size=1 ask=ust price=1000')
            command = await asyncio.ensure_future(loop.run_in_executor(None, input))
            args = command.split()
            if not args:
                continue
            if args[0] == 'q':
                self.stop()
                break
            kwargs = dict(dex=self.dex.dex)
            for arg in args[1:]:
                key, value = arg.split('=')
                try:
                    value = float(value)
                except ValueError:
                    pass
                kwargs[key] = value
            try:
                if args[0].lower().find('limit') >= 0:
                    order = LimitOrder(**kwargs)
                elif args[0].lower().find('stop') >= 0:
                    order = StopLoss(**kwargs)
                else:
                    continue
                self.submit(order)
            except Exception as exc:
                print(exc)

    async def start(self, broker=False):
        if broker:
            asyncio.create_task(self.broker())
        async for _ in wallet.blockchain:
            if self.flag:
                break
            await multi_pools_query(self.pools.values())
            tasks = [asyncio.create_task(order.match(self.pools)) for order in self.open]
            await asyncio.gather(*tasks)
            routes: List[Route] = [task.result() for task in tasks]
            for order, route in zip(self.open, routes):
                if route:
                    self.open.remove(order)
                    asyncio.create_task(self.fill(order, route))

    def stop(self):
        self.open.clear()
        self.flag = True
