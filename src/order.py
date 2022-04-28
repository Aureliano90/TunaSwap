from src.dex import *
from src.transaction import *
import attr

open_db = getDb('open.json')
filled_db = getDb('filled.json')


class LimitOrder(Swap):
    __slots__ = ('aggr', '_id', 'price', 'status', 'triggered', 'tx')

    def __init__(
            self,
            dex: str,
            bid: str,
            bid_size: Numeric,
            ask: str,
            ask_size=Dec(0),
            price=Dec(0),
            id=''
    ):
        self.id = id
        bid, ask = bid.lower(), ask.lower()
        bid_size = to_Dec(bid_size, bid)
        ask_size = to_Dec(ask_size, ask)
        if price == 0:
            assert ask_size != Dec(0)
            self.price = ask_size / bid_size
        else:
            self.price = Dec(price)
            ask_size = self.price * bid_size
        super(LimitOrder, self).__init__(dex, bid, bid_size, ask, ask_size)
        self.status = 'open'
        self.triggered = False
        self.tx: TxResult | TxInfo | None = None

    @property
    def id(self):
        return self._id

    @id.setter
    def id(self, value):
        self._id = str(value)

    def __repr__(self):
        s = f"limit order {self.id}: {self.float_bid()} {self.bid} -> {self.float_ask()} {self.ask} on {self.dex}\n" \
            f"Limit price {self.price.to_short_str()} {self.ask} per {self.bid}"
        return 'Open ' + s if self.status == 'open' else 'Filled ' + s

    def to_data(self) -> Dict:
        return {
            'dex': self.dex,
            'bid': self.bid,
            'bid_size': self.float_bid(),
            'ask': self.ask,
            'ask_size': self.float_ask(),
            'price': float(self.price),
            'order_id': self.id,
            'status': self.status,
            'triggered': self.triggered,
            'tx': self.tx.to_data() if self.tx else None
        }

    @classmethod
    def from_data(cls, data: Dict):
        ins = cls(
            data['dex'],
            data['bid'],
            to_Dec(data['bid_size'], data['bid']),
            data['ask'],
            to_Dec(data['ask_size'], data['ask']),
            Dec(data['price']),
            data['order_id']
        )
        ins.status, ins.triggered = data['status'], data['triggered']
        ins.tx = TxResult.from_data(data['tx']) if data['tx'] else None
        return ins

    async def match(self, pools: Dict[Pair | str, Pool]) -> Route | None:
        route = await Dex(self.dex).dijkstra_routing(self.bid, self.bid_size, self.ask, pools)
        if route.trade.ask_size > self.ask_size:
            self.triggered = True
            return route
        else:
            return None


class StopLoss(LimitOrder):
    __slots__ = ()

    def __repr__(self):
        s = f"stop order {self.id}: {self.float_bid()} {self.bid} -> {self.float_ask()} {self.ask} on {self.dex}\n" \
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


class ConditionOrder:
    __slots__ = ('condition', 'order')

    def __init__(
            self,
            condition: Dict[str, bool],
            order: LimitOrder):
        self.condition = condition
        self.order = order

    def __repr__(self):
        return f"{self.order}\nConditional on {' '.join(self.condition.keys())}"

    def __getattr__(self, item):
        return getattr(self.order, item)

    def __setattr__(self, key, value):
        if key in ('condition', 'order'):
            super().__setattr__(key, value)
        else:
            self.order.__setattr__(key, value)

    def notify(self, order_id: str):
        if order_id in self.condition:
            self.condition[order_id] = True

    async def match(self, pools: Dict[Pair | str, Pool]) -> Route | None:
        if all(self.condition.values()):
            self.order.triggered = True
            return await self.order.match(pools)


@attr.s
class OrderBook:
    dex: Dex | str = attr.ib(converter=Dex)
    open: Dict[str, LimitOrder] = attr.ib(factory=dict)
    filled: Dict[str, LimitOrder] = attr.ib(factory=dict)
    pools: Dict[Pair | str, Pool] = attr.ib(factory=dict)
    flag = attr.ib(default=False)

    def submit(self, order: LimitOrder):
        order.dex = self.dex.dex
        if not order.id or order.id in self.open:
            for i in range(1, len(self.open) + 2):
                if str(i) not in self.open:
                    order.id = str(i)
                    break
        self.open[order.id] = order
        print(order)
        self.pools.update(self.dex.pools_from_routes(self.dex.dfs(order.bid, order.ask)))

    def cancel(self, order_id: str):
        if order_id in self.open:
            self.open.pop(order_id)
        pools = {}
        for order in self.open.values():
            pools.update(self.dex.pools_from_routes(self.dex.dfs(order.bid, order.ask)))
        keys = set(self.pools.keys())
        for key in keys:
            if key not in pools:
                self.pools.pop(key)

    async def fill(self, order: LimitOrder, route: Route):
        try:
            msgs = await self.dex.route_to_msg(route, order.ask_size)
            fee = await wallet.estimate_fee(msgs, memo='')
            if fee is None:
                self.open[order.id] = order
                return
            tx = await wallet.create_and_sign_tx(msgs, fee=fee, memo='')
            res = await wallet.broadcast(tx)
            if res is None:
                self.open[order.id] = order
            else:
                order.status = 'filled'
                order.tx = res
                for coin in calculate_profit(res):
                    if order.ask == (token := from_denom(coin.denom)):
                        order.ask_size = Dec(coin.amount * pow(10, tokens_info[token.lower()]['decimals']))
                print(order)
                save_tx(res)
                data = order.to_data()
                filled_db.add(data)
                self.filled[order.id] = order
                self.cancel(order.id)
                for _order in self.open.values():
                    if isinstance(_order, ConditionOrder):
                        _order.notify(order.id)
        except LCDResponseError as exc:
            print(f"Exception in {type(self).__name__}.fill\n{exc}")
            self.open[order.id] = order

    def parse_order(self, *args):
        kwargs: Dict[str, str | float] = dict(dex=self.dex.dex)
        for arg in args[1:]:
            try:
                key, value = arg.split('=')
                key = key.lower()
                kwargs[key] = value
                kwargs[key] = float(value)
            except ValueError:
                pass
        try:
            if 'condition' in kwargs:
                condition = {}
                for c in kwargs.pop('condition').split(','):
                    condition[c] = False
            else:
                condition = None
            if args[0].lower().find('limit') >= 0:
                order = LimitOrder(**kwargs)
            elif args[0].lower().find('stop') >= 0:
                order = StopLoss(**kwargs)
            else:
                return
            if condition:
                order = ConditionOrder(condition, order)
            return order
        except Exception as exc:
            print(f"Exception in {type(self).__name__}.parse_order\n{exc}")

    @staticmethod
    def parse_query(*args) -> Dict:
        kwargs = {}
        for arg in args:
            try:
                key, value = arg.split('=')
                key = key.lower()
                kwargs[key] = value
                kwargs[key] = float(value)
            except ValueError:
                pass
        return kwargs

    async def broker(self):
        print("""
1   Query price
2   Place order
3   Cancel order
4   Pending orders
q   Quit""")
        while True:
            command = await asyncio.ensure_future(loop.run_in_executor(None, input))
            command = command.split()
            match command:
                case ['1', *args]:
                    if len(args):
                        kwargs = self.parse_query(*args)
                    else:
                        print('Query price. Example: bid=luna bid_size=1 ask=ust')
                        command = await asyncio.ensure_future(loop.run_in_executor(None, input))
                        args = command.split()
                        kwargs = self.parse_query(*args)
                    try:
                        print(await self.dex.dijkstra_routing(**kwargs))
                    except TypeError:
                        pass
                case ['2', *args]:
                    if len(args):
                        order = self.parse_order(*args)
                    else:
                        print('Accepting order. Example: limit bid=luna bid_size=1 ask=ust price=1000')
                        command = await asyncio.ensure_future(loop.run_in_executor(None, input))
                        args = command.split()
                        order = self.parse_order(*args)
                    if order:
                        self.submit(order)
                case ['3']:
                    print(f"Open orders: {' '.join(self.open.keys())}")
                    if self.open:
                        order_id = await asyncio.ensure_future(loop.run_in_executor(None, input))
                        self.cancel(order_id)
                case ['3', order_id]:
                    self.cancel(order_id)
                case ['4']:
                    for order in self.open.values():
                        print(order)
                case ['q']:
                    self.stop()
                    break
                case _:
                    continue

    async def start(self, broker=False):
        for data in open_db.getAll():
            order = LimitOrder.from_data(data)
            self.submit(order)
        open_db.deleteAll()
        if broker:
            asyncio.create_task(self.broker())
        async for _ in wallet.blockchain:
            if self.flag:
                break
            await multi_pools_query(self.pools.values())
            tasks = [asyncio.create_task(order.match(self.pools)) for order in self.open.values()]
            await asyncio.gather(*tasks)
            routes: List[Route] = [task.result() for task in tasks]
            filling = []
            for order, route in zip(self.open.values(), routes):
                if route:
                    filling.append(order.id)
                    asyncio.create_task(self.fill(order, route))
            for order in filling:
                self.open.pop(order)

    def stop(self):
        data = [order.to_data() for order in self.open.values()]
        if data:
            open_db.addMany(data)
        self.open.clear()
        self.flag = True
