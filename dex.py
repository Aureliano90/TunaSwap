from pool import *
from collections import namedtuple
import attr

Hop = namedtuple('Hop', ['bid', 'ask', 'dex'])


@attr.s(cmp=False)
class Vertex:
    ask_size: Dec = attr.ib(converter=Dec)
    spread: Dec = attr.ib(converter=Dec)
    route: Tuple[str] = attr.ib(init=False)
    hops: Tuple[Hop] = attr.ib(init=False)

    def __eq__(self, other):
        return True if self.spread == other.spread else False

    def __gt__(self, other):
        return True if self.spread > other.spread else False

    def __lt__(self, other):
        return True if self.spread < other.spread else False


@attr.s(repr=False)
class Route:
    route: Tuple[str] = attr.ib()
    trade: Trade = attr.ib()
    swaps: List[Trade] = attr.ib()

    def __repr__(self):
        s = f"{self.trade.float_bid()} {self.trade.bid}"
        for i in range(len(self.swaps)):
            s += f" -> {self.swaps[i].float_ask()} {self.swaps[i].ask}"
        return f"Route({s} on {self.trade.dex})"


class Dex:
    def __init__(self, dex: str):
        self.dex = dex
        if dex in router:
            self.router = AccAddress(router[dex])
        else:
            self.router = AccAddress('')

    def adjacent(self, bid: str) -> List[str]:
        """Tokens forming a trading pair with token_in
        :return: adjacency list
        """
        return [pool.other(bid) for pool, info in pools_info.items() if bid in pool.pair and self.dex in info]

    def dfs(
            self,
            bid: str,
            ask: str
    ) -> List[Tuple]:
        """Depth first search for possible trading routes
        """
        bid, ask = bid.lower(), ask.lower()
        pairs = {bid: self.adjacent(bid)}
        route = (bid,)
        stack = [route]
        res = []
        while stack:
            route = stack.pop()
            node = route[-1]
            if node == ask:
                res.append(route)
            else:
                if node not in pairs:
                    pairs[node] = self.adjacent(node)
                for token in pairs[node]:
                    if token not in route:
                        stack.append(route + (token,))
        return res

    def assertion(self, bid: str, ask: str):
        bid, ask = bid.lower(), ask.lower()
        assert bid in tokens_info, f"No token info {bid}"
        assert self.dex in get_dex(bid), f"{bid} not trading on {self.dex}"
        assert ask in tokens_info, f"No token info {ask}"
        assert self.dex in get_dex(ask), f"{ask} not trading on {self.dex}"
        return bid, ask

    @convert_params
    async def dijkstra_routing(
            self,
            bid: str,
            bid_size: Numeric,
            ask: str
    ) -> Route | None:
        """Find the route with the least spread using Dijkstra's algorithm

        :return: Route(route, trade, swaps)
        """
        bid, ask = self.assertion(bid, ask)

        routes = self.dfs(bid, ask)
        if not routes:
            return None

        graph = set()
        for route in routes:
            graph.update(route)
        # Connected edges in the graph
        pools = dict()
        for route in routes:
            for i in range(len(route) - 1):
                pair = Pair(route[i], route[i + 1])
                if pair not in pools:
                    pools[pair] = Pool(pair, self.dex)
                if pair == Pair('luna', 'ust'):
                    pools['native_swap'] = Pool('luna', 'ust', 'native_swap')
        # Query liquidity in relevant pairs
        await multi_pools_query(pools.values())

        native = False
        min_vertex = Vertex(bid_size, Dec(0))
        min_vertex.route = (bid,)
        heap = [min_vertex]
        spreads = {token: Dec(1) for token in graph}
        spreads[bid] = Dec(0)
        visited = set()
        while heap:
            # Find the next token with the least spread
            min_vertex = heappop(heap)
            next = min_vertex.route[-1]
            visited.add(next)
            if next == ask:
                break
            # Update spread of neighbors
            for neighbor in self.adjacent(next):
                if neighbor not in visited and neighbor in graph:
                    pair = Pair(next, neighbor)
                    trade = await pools[pair].simulate(next, min_vertex.ask_size)
                    if pair == Pair('luna', 'ust'):
                        native_swap = await pools['native_swap'].simulate(next, min_vertex.ask_size)
                        if native_swap.ask_size > trade.ask_size:
                            trade = native_swap
                            native = True
                    spread = spreads[next] + trade.spread - spreads[next] * trade.spread
                    if spread < spreads[neighbor]:
                        spreads[neighbor] = spread
                        vertex = Vertex(trade.ask_size, spread)
                        vertex.route = min_vertex.route + (neighbor,)
                        heappush(heap, vertex)

        ask_size = expected = bid_size
        route: Tuple[str] = min_vertex.route
        swaps: List[Trade] = []
        for i in range(len(route) - 1):
            pair = Pair(route[i], route[i + 1])
            if native and pair == Pair('luna', 'ust'):
                trade = await pools['native_swap'].simulate(route[i], ask_size)
            else:
                trade = await pools[pair].simulate(route[i], ask_size)
            ask_size = trade.ask_size
            swaps.append(trade)
            expected *= await pools[pair].price(route[i])
        spread = (expected - ask_size) / expected
        commission = expected * spread
        trade = Trade(self.dex,
                      bid,
                      bid_size,
                      ask,
                      ask_size,
                      spread,
                      commission)
        return Route(route=route,
                     trade=trade,
                     swaps=swaps)

    async def route_to_msg(
            self,
            routing: Route,
            minimum_receive=Dec(0)
    ) -> List[Msg]:
        """Wrap trading route to a message
        """
        if routing is None:
            print('Impossible swap.')
            exit()
        trade, route, swaps = routing.trade, routing.route, routing.swaps
        bid, bid_size, ask, ask_size = trade.bid, trade.bid_size, trade.ask, trade.ask_size

        if self.router:
            if minimum_receive == Dec(0):
                if bid == ask:
                    minimum_receive = bid_size
                else:
                    if ask_size != Dec(0):
                        minimum_receive = ask_size * (1 - slippage)
                    else:
                        return await self.swap_msg(bid, bid_size, ask)
            operations = []
            for i in range(len(swaps)):
                if swaps[i].dex == 'native_swap':
                    operation = {'native_swap': {
                        'offer_denom': get_denom(swaps[i].bid),
                        'ask_denom': get_denom(swaps[i].ask)
                    }}
                else:
                    operation = {swaps[i].dex: {
                        'offer_asset_info': asset_info(swaps[i].bid),
                        'ask_asset_info': asset_info(swaps[i].ask)
                    }}
                operations.append(operation)
            msg = {
                'execute_swap_operations': {
                    'offer_amount': bid_size.whole,
                    'minimum_receive': minimum_receive.whole,
                    'max_spread': f'{max_spread}',
                    'operations': operations
                }}
            # Message for native tokens
            if bid in native_tokens:
                coins = Coins({get_denom(bid): bid_size.whole})
                return [MsgExecuteContract(wallet.key.acc_address,
                                           self.router,
                                           msg, coins)]
            # Message for CW20 tokens
            else:
                execute_msg = {
                    'send': {
                        'contract': self.router,
                        'amount': bid_size.whole,
                        'msg': base64str_encode(msg)
                    }
                }
                return [MsgExecuteContract(wallet.key.acc_address,
                                           get_contract(bid),
                                           execute_msg)]
        # Loop doesn't have a router.
        else:
            pools = [Pool(route[i], route[i + 1], swaps[i].dex) for i in range(len(swaps))]
            await multi_pools_query(pools)

            msgs = []
            for i in range(len(swaps)):
                trade = await pools[i].simulate(route[i], bid_size)
                minimum_receive = trade.ask_size - 1
                msgs += await pools[i].trade_to_msg(trade, minimum_receive)
                # There may be leftovers.
                # Next input = last minimum_receive
                bid_size = minimum_receive
            return msgs

    @convert_params
    async def swap_msg(
            self,
            bid: str,
            bid_size: Numeric,
            ask: str,
            minimum_receive=Dec(0)
    ) -> List[Msg]:
        """Multi hop swap message
        """
        bid, ask = self.assertion(bid, ask)
        routing = await self.dijkstra_routing(bid, bid_size, ask)
        return await self.route_to_msg(routing, minimum_receive)

    @convert_params
    async def limit_order(
            self,
            bid: str,
            bid_size: Numeric,
            bid_price: Numeric
    ):
        pass
