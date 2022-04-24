from src.pool import *
from collections import namedtuple
import attr

Hop = namedtuple('Hop', ['bid', 'ask', 'dex'])


@attr.s(slots=True)
class Vertex:
    ask_size: Dec = attr.ib(cmp=False, converter=Dec)
    spread: Dec = attr.ib(converter=Dec)
    route: Tuple[str] = attr.ib(cmp=False, init=False)
    hops: Tuple[Hop] = attr.ib(cmp=False, init=False)
    swaps: List[Swap] = attr.ib(cmp=False, factory=list)


@attr.s(repr=False, slots=True)
class Route:
    route: Tuple[str] = attr.ib()
    trade: Swap = attr.ib()
    swaps: List[Swap] = attr.ib()

    def __repr__(self):
        strings = [f"{self.trade.float_bid()} {self.trade.bid}"]
        strings += [f"{swap.float_ask()} {swap.ask}" for swap in self.swaps]
        return f"Route({' -> '.join(strings)} on {self.trade.dex})"


class Dex:
    __slots__ = ('dex', 'router')

    def __init__(self, dex: str):
        self.dex = find_dex(dex)
        if self.dex in router:
            self.router = AccAddress(router[self.dex])
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

    def pools_from_routes(self, routes: List[Tuple]) -> Dict[Pair | str, Pool]:
        pools = {}
        for route in routes:
            for i in range(len(route) - 1):
                pair = Pair(route[i], route[i + 1])
                if pair not in pools:
                    pools[pair] = Pool(pair, self.dex)
                if pair == Pair('luna', 'ust'):
                    if 'native_swap' not in pools:
                        pools['native_swap'] = Pool('luna', 'ust', 'native_swap')
        return pools

    @convert_params
    async def dijkstra_routing(
            self,
            bid: str,
            bid_size: Numeric,
            ask: str,
            pools=None
    ) -> Route | None:
        """Find the route with the least spread using Dijkstra's algorithm

        :return: Route(route, trade, swaps)
        """
        if pools is None:
            pools = {}
        bid, ask = self.assertion(bid, ask)

        routes = self.dfs(bid, ask)
        if not routes:
            return None

        graph = set()
        for route in routes:
            graph.update(route)
        # Connected edges in the graph
        if not pools:
            pools = self.pools_from_routes(routes)
            # Query liquidity in relevant pairs
            await multi_pools_query(pools.values())

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
                    swap = await pools[pair].simulate(next, min_vertex.ask_size)
                    if pair == Pair('luna', 'ust'):
                        native_swap = await pools['native_swap'].simulate(next, min_vertex.ask_size)
                        if native_swap.ask_size > swap.ask_size:
                            swap = native_swap
                    spread = spreads[next] + swap.spread - spreads[next] * swap.spread
                    if spread < spreads[neighbor]:
                        spreads[neighbor] = spread
                        vertex = Vertex(swap.ask_size, spread)
                        vertex.route = min_vertex.route + (neighbor,)
                        vertex.swaps = min_vertex.swaps + [swap]
                        heappush(heap, vertex)

        ask_size = min_vertex.swaps[-1].ask_size
        expected = bid_size
        for swap in min_vertex.swaps:
            expected *= await pools[Pair(swap.bid, swap.ask)].price(swap.bid)
        commission = expected - ask_size
        spread = commission / expected
        swap = Swap(self.dex,
                    bid,
                    bid_size,
                    ask,
                    ask_size,
                    spread,
                    commission)
        return Route(route=min_vertex.route,
                     trade=swap,
                     swaps=min_vertex.swaps)

    async def route_to_msg(
            self,
            routing: Route,
            minimum_receive=Dec(0)
    ) -> List[Msg]:
        """Wrap trading route to a message
        """
        if routing is None:
            print('Impossible swap.')
            raise ValueError
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
            for swap in swaps:
                if swap.dex == 'native_swap':
                    operation = ABI.native_swap(swap.bid, swap.ask)
                else:
                    operation = ABI.dex_swap(swap.dex, swap.bid, swap.ask)
                operations.append(operation)
            msg = ABI.execute_swap_operations(bid_size,
                                              minimum_receive,
                                              f'{max_spread}',
                                              operations)
            # Message for native tokens
            if bid in native_tokens:
                return [MsgExecuteContract(wallet.key.acc_address,
                                           self.router,
                                           msg,
                                           Coins({get_denom(bid): bid_size.whole}))]
            # Message for CW20 tokens
            else:
                return [MsgExecuteContract(wallet.key.acc_address,
                                           get_contract(bid),
                                           ABI.send(self.router, bid_size, msg))]
        # Loop doesn't have a router.
        else:
            msgs = []
            for swap in swaps:
                msgs.extend(await Pool(swap).swap_to_msg(swap, swap.ask_size))
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
